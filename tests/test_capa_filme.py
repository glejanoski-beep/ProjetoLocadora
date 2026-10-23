"""Capa do filme: validação, URL pública, transporte, estado e contrato XanoScript.

HTTP e sessão substituídos por doubles locais; não envia arquivos ao Xano.
"""

import io
import re
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import reflex as rx

from ProjetoLocadora import xano_client as client
from ProjetoLocadora.ProjetoLocadora import State
from ProjetoLocadora.catalogo_filmes import CAPA_MAX_BYTES, validar_capa
from ProjetoLocadora.xano_client import XanoCatalogError, film_cover_url

BASE = "https://x8ki-local.n7.xano.io/api:catalogo"
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"0" * 64
PDF = b"%PDF-1.7\n" + b"0" * 64
COVER = {
    "access": "public", "path": "/vault/AbC123/xyz/capa-4.webp", "name": "capa-4.webp",
    "type": "image", "size": 500, "mime": "image/webp", "meta": {},
}
FILM = {
    "id": 4, "titulo": "Filme local", "genero": "Drama", "ano_lancamento": 1950,
    "classificacao": "Livre", "valor_locacao_centavos": 500, "status": "active",
}
XANO_API = Path(__file__).resolve().parents[1] / "xano" / "xano" / "api" / "catalogo_filmes"


def response(status, payload, method="POST"):
    return httpx.Response(status, json=payload, request=httpx.Request(method, BASE))


class TestCoverValidation(unittest.TestCase):
    def test_detects_type_by_content(self):
        self.assertEqual(validar_capa(JPEG), ("image/jpeg", "jpg"))
        self.assertEqual(validar_capa(PNG), ("image/png", "png"))
        self.assertEqual(validar_capa(WEBP), ("image/webp", "webp"))

    def test_rejects_disguised_empty_and_oversized_files(self):
        for content in (PDF, b"GIF89a" + b"0" * 10, b"", JPEG[:2]):
            with self.subTest(content=content[:8]), self.assertRaises(ValueError):
                validar_capa(content)
        with self.assertRaisesRegex(ValueError, "2 MB"):
            validar_capa(JPEG + b"0" * CAPA_MAX_BYTES)
        self.assertEqual(validar_capa(JPEG.ljust(CAPA_MAX_BYTES, b"0"))[0], "image/jpeg")


class TestCoverUrl(unittest.TestCase):
    def setUp(self):
        url = patch.object(client, "get_xano_catalog_api_url", return_value=BASE)
        url.start()
        self.addCleanup(url.stop)

    def test_public_path_uses_instance_origin(self):
        self.assertEqual(film_cover_url(COVER), "https://x8ki-local.n7.xano.io/vault/AbC123/xyz/capa-4.webp")

    def test_unexpected_values_mean_no_cover(self):
        for cover in (
            None, "texto", {}, {**COVER, "access": "private"},
            {**COVER, "path": "/vault/../segredo"}, {**COVER, "path": "https://outro.site/x.jpg"},
            {**COVER, "path": "/vault/a b.jpg"}, {**COVER, "path": '/vault/a".jpg'}, {**COVER, "path": 7},
        ):
            with self.subTest(cover=cover):
                self.assertEqual(film_cover_url(cover), "")


class TestCoverClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        url = patch.object(client, "get_xano_catalog_api_url", return_value=BASE)
        url.start()
        self.addCleanup(url.stop)
        self.request = patch.object(client, "_catalog_request", new=AsyncMock()).start()
        self.addCleanup(patch.stopall)

    async def test_listing_exposes_cover_url_and_hides_storage_object(self):
        self.request.return_value = response(200, [{**FILM, "capa": COVER}, {**FILM, "id": 5, "capa": None}, {**FILM, "id": 6}], "GET")
        films = await client.list_films_xano("token-local")
        self.assertEqual([f["capa_url"] for f in films], [film_cover_url(COVER), "", ""])
        self.assertTrue(all("capa" not in film for film in films))

    async def test_link_is_used_when_there_is_no_stored_file(self):
        link = "https://4.bp.blogspot.com/a/s1600/Creed_poster.jpeg"
        self.request.return_value = response(200, [
            {**FILM, "capa": None, "capa_link": link},
            {**FILM, "id": 5, "capa": COVER, "capa_link": link},
            {**FILM, "id": 6, "capa_link": "javascript:alert(1)"},
            {**FILM, "id": 7, "capa_link": "http://sem-https.com/a.jpg"},
        ], "GET")
        films = await client.list_films_xano("token-local")
        self.assertEqual([f["capa_url"] for f in films], [link, film_cover_url(COVER), "", ""])
        self.assertEqual([f["capa_link"] for f in films], [link, link, "", ""])

    async def test_set_link_sends_json_put(self):
        link = "https://4.bp.blogspot.com/a/s1600/Creed_poster.jpeg"
        self.request.return_value = response(200, {"film": {**FILM, "capa_link": link}, "audit_succeeded": True}, "PUT")
        film = await client.set_film_cover_link_xano("token-local", 4, link)
        self.assertEqual(film["capa_url"], link)
        args, kwargs = self.request.await_args
        self.assertEqual(args[:2], ("PUT", "/4/capa-link"))
        self.assertEqual(kwargs["json_body"], {"capa_link": link})
        self.request.return_value = response(400, {"message": "x"}, "PUT")
        with self.assertRaisesRegex(XanoCatalogError, "link https válido"):
            await client.set_film_cover_link_xano("token-local", 4, "https://x")

    async def test_upload_sends_generated_name_and_validated_content(self):
        self.request.return_value = response(200, {"film": {**FILM, "capa": COVER}, "audit_succeeded": True})
        film = await client.upload_film_cover_xano("token-local", 4, WEBP, "image/webp", "webp")
        self.assertEqual(film["capa_url"], film_cover_url(COVER))
        args, kwargs = self.request.await_args
        self.assertEqual(args[:2], ("POST", "/4/capa"))
        self.assertEqual(kwargs["upload"], client.UploadPart("capa", "capa-4.webp", WEBP, "image/webp"))

    async def test_upload_errors_have_specific_messages(self):
        cases = {
            400: "não foi aceita", 413: "não foi aceita", 429: "limite de requisições",
            403: "permissão", 404: "Filme não encontrado", 500: "erro interno",
        }
        for status, text in cases.items():
            with self.subTest(status=status):
                self.request.return_value = response(status, {"message": "x"})
                with self.assertRaisesRegex(XanoCatalogError, text):
                    await client.upload_film_cover_xano("token-local", 4, JPEG, "image/jpeg", "jpg")

    async def test_plan_without_file_storage_is_not_reported_as_permission(self):
        self.request.return_value = response(
            403, {"code": "ERROR_CODE_ACCESS_DENIED", "message": "Not supported. Please upgrade your Xano instance."}
        )
        with self.assertRaisesRegex(XanoCatalogError, "plano atual do Xano não permite armazenar arquivos"):
            await client.upload_film_cover_xano("token-local", 4, JPEG, "image/jpeg", "jpg")

    async def test_failed_audit_is_reported_without_retry(self):
        self.request.return_value = response(200, {"film": {**FILM, "capa": None}, "audit_succeeded": False}, "DELETE")
        with self.assertRaises(client.XanoAuditError):
            await client.remove_film_cover_xano("token-local", 4)
        self.request.assert_awaited_once()


class TestWindowsMultipartTransport(unittest.IsolatedAsyncioTestCase):
    async def test_curl_receives_form_part_and_temporary_file_is_removed(self):
        seen = {}

        def fake_run(command, input, **kwargs):
            config = input.decode("utf-8")
            seen["config"] = config
            path = re.search(r'capa=@(.+?);type=', config).group(1).replace("\\\\", "\\")
            seen["path"] = path
            seen["content"] = Path(path).read_bytes()
            seen["timeout"] = kwargs["timeout"]
            body = b'{"ok": true}\n__XANO_META__200__XANO_REQUEST_ID____XANO_CORRELATION_ID____XANO_CF_RAY__'
            return type("Done", (), {"returncode": 0, "stdout": body, "stderr": b""})()

        upload = client.UploadPart("capa", "capa-4.png", PNG, "image/png")
        with patch.object(client, "_WINDOWS", True), patch.object(client.shutil, "which", return_value="curl.exe"), \
                patch.object(client.subprocess, "run", side_effect=fake_run):
            result = await client._authenticated_request("POST", BASE + "/catalogo-filmes/filmes/4/capa", "token-local", upload=upload)

        self.assertEqual(result.status_code, 200)
        self.assertIn(";type=image/png;filename=capa-4.png", seen["config"])
        self.assertNotIn("Content-Type: application/json", seen["config"])
        self.assertEqual(seen["content"], PNG)
        self.assertEqual(seen["timeout"], 31)
        self.assertFalse(Path(seen["path"]).exists())


class TestCoverState(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = rx.State(_reflex_internal_init=True)
        self.state = await self.root.get_state(State)
        self.state._xano_auth_token = "token-local"
        self.state._user_id = "1"
        self.state._user_role = "admin"
        self.state.editing_film = True
        self.state.editing_film_id = 4
        self.upload = patch("ProjetoLocadora.ProjetoLocadora.upload_film_cover_xano", new=AsyncMock()).start()
        self.remove = patch("ProjetoLocadora.ProjetoLocadora.remove_film_cover_xano", new=AsyncMock()).start()
        self.addCleanup(patch.stopall)

    async def send(self, content):
        return [u async for u in self.state.upload_film_cover([rx.UploadFile(file=io.BytesIO(content))])]

    async def test_admin_upload_updates_preview(self):
        self.upload.return_value = {**FILM, "capa_url": "https://x8ki-local.n7.xano.io/vault/a/capa-4.jpg"}
        await self.send(JPEG)
        self.upload.assert_awaited_once_with("token-local", 4, JPEG, "image/jpeg", "jpg")
        self.assertEqual(self.state.form_cover_url, "https://x8ki-local.n7.xano.io/vault/a/capa-4.jpg")
        self.assertEqual((self.state.cover_success, self.state.cover_error, self.state.cover_loading), ("Capa atualizada.", "", False))

    async def test_invalid_file_never_reaches_xano(self):
        await self.send(PDF)
        self.upload.assert_not_awaited()
        self.assertIn("JPEG, PNG ou WebP", self.state.cover_error)

    async def test_member_is_redirected_without_upload(self):
        self.state._user_role = "member"
        updates = await self.send(JPEG)
        self.upload.assert_not_awaited()
        self.assertTrue(any("/filmes" in str(u) for u in updates))

    async def test_xano_error_is_shown_and_preview_kept(self):
        self.state.form_cover_url = "https://x8ki-local.n7.xano.io/vault/a/antiga.jpg"
        self.upload.side_effect = XanoCatalogError("A capa não foi aceita: use uma imagem JPEG, PNG ou WebP com até 2 MB.")
        await self.send(JPEG)
        self.assertEqual(self.state.form_cover_url, "https://x8ki-local.n7.xano.io/vault/a/antiga.jpg")
        self.assertIn("não foi aceita", self.state.cover_error)

    async def test_remove_clears_preview(self):
        self.state.form_cover_url = "https://x8ki-local.n7.xano.io/vault/a/antiga.jpg"
        self.remove.return_value = {**FILM, "capa_url": "", "capa_link": ""}
        [u async for u in self.state.remove_film_cover()]
        self.remove.assert_awaited_once_with("token-local", 4)
        self.assertEqual((self.state.form_cover_url, self.state.cover_success), ("", "Capa removida."))

    async def test_save_link_validates_before_calling_xano(self):
        link = "https://4.bp.blogspot.com/a/s1600/Creed_poster.jpeg"
        self.state.form_cover_link = "http://inseguro.com/a.jpg"
        [u async for u in self.state.save_film_cover_link()]
        self.assertIn("link https", self.state.cover_error)
        with patch("ProjetoLocadora.ProjetoLocadora.set_film_cover_link_xano", new=AsyncMock(
            return_value={**FILM, "capa_url": link, "capa_link": link},
        )) as save:
            self.state.form_cover_link = "  " + link + " "
            [u async for u in self.state.save_film_cover_link()]
        save.assert_awaited_once_with("token-local", 4, link)
        self.assertEqual((self.state.form_cover_url, self.state.cover_success), (link, "Link da capa salvo."))

    async def test_new_film_has_no_cover_operations(self):
        self.state.editing_film = False
        self.state.editing_film_id = 0
        await self.send(JPEG)
        self.upload.assert_not_awaited()
        self.assertIn("Carregue o filme", self.state.cover_error)


class TestCoverXanoContract(unittest.TestCase):
    def test_upload_endpoint_is_admin_only_public_and_checks_real_type_and_size(self):
        source = (XANO_API / "filmes_id_capa_POST.xs").read_text(encoding="utf-8")
        self.assertIn('query "catalogo-filmes/filmes/{id}/capa" verb=POST', source)
        self.assertRegex(source, r"\n\s+file\? capa\n")
        self.assertNotRegex(source, r"\n\s+image\? capa")
        self.assertIn('required_role: "admin"', source)
        self.assertIn('access = "public"', source)
        self.assertIn('["image/jpeg", "image/png", "image/webp"]|in:$stored_cover.mime', source)
        self.assertIn("$stored_cover.size <= 2097152", source)
        self.assertIn('action: "update_film_cover"', source)
        # A capa anterior só é apagada depois que o filme aponta para a nova.
        self.assertLess(source.index("db.edit film"), source.index("$existing_film.capa.path"))

    def test_remove_endpoint_is_admin_only_and_audited(self):
        source = (XANO_API / "filmes_id_capa_DELETE.xs").read_text(encoding="utf-8")
        self.assertIn('verb=DELETE', source)
        self.assertIn('required_role: "admin"', source)
        self.assertIn("capa: null", source)
        self.assertIn('action: "remove_film_cover"', source)

    def test_film_endpoints_return_cover(self):
        for name in ("filmes_GET.xs", "filmes_id_GET.xs", "filmes_POST.xs", "filmes_id_PATCH.xs"):
            with self.subTest(name=name):
                self.assertIn('"status", "capa", "capa_link"]', (XANO_API / name).read_text(encoding="utf-8"))

    def test_link_endpoint_is_admin_only_https_and_audited(self):
        source = (XANO_API / "filmes_id_capa_link_PUT.xs").read_text(encoding="utf-8")
        self.assertIn('query "catalogo-filmes/filmes/{id}/capa-link" verb=PUT', source)
        self.assertIn('required_role: "admin"', source)
        # Sem "/" escapada no padrão: o XanoScript não preserva "\/" (validação falhava sempre).
        self.assertIn('$link|replace:"/":""', source)
        self.assertIn('$link|starts_with:"https://"', source)
        self.assertIn('"/^https:[A-Za-z0-9._~:?#@!&()*+,;=%-]+$/"|regex_matches:$link_chars', source)
        self.assertNotIn("\/", source)
        self.assertIn("($link|strlen) <= 500", source)
        self.assertIn('action: "update_film_cover_link"', source)
        # Remover a capa limpa também o link.
        self.assertIn("capa_link: null", (XANO_API / "filmes_id_capa_DELETE.xs").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
