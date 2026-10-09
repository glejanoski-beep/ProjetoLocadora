import re
import unittest
from pathlib import Path


FUNCTION_PATH = (
    Path(__file__).parents[1]
    / "xano"
    / "xano"
    / "function"
    / "quick_start"
    / "enforce_role.xs"
)
LOG_EVENT_PATH = (
    Path(__file__).parents[1]
    / "xano"
    / "xano"
    / "function"
    / "quick_start"
    / "log_event.xs"
)
AUTH_ME_PATH = (
    Path(__file__).parents[1]
    / "xano"
    / "xano"
    / "api"
    / "authentication"
    / "auth"
    / "me_GET.xs"
)
MY_EVENTS_PATH = (
    Path(__file__).parents[1]
    / "xano"
    / "xano"
    / "api"
    / "event_logs"
    / "logs"
    / "user"
    / "my_events_GET.xs"
)
UPDATE_PASSWORD_PATH = (
    Path(__file__).parents[1]
    / "xano"
    / "xano"
    / "api"
    / "authentication"
    / "reset"
    / "update_password_POST.xs"
)
SIGNUP_PATH = (
    Path(__file__).parents[1]
    / "xano"
    / "xano"
    / "api"
    / "authentication"
    / "auth"
    / "signup_POST.xs"
)
WELCOME_EMAIL_PATH = (
    Path(__file__).parents[1]
    / "xano"
    / "xano"
    / "api"
    / "authentication"
    / "message"
    / "send_welcome_email_POST.xs"
)
FILM_CREATE_PATH = (
    Path(__file__).parents[1]
    / "xano"
    / "xano"
    / "api"
    / "catalogo_filmes"
    / "filmes_POST.xs"
)
FILM_UPDATE_PATH = (
    Path(__file__).parents[1]
    / "xano"
    / "xano"
    / "api"
    / "catalogo_filmes"
    / "filmes_id_PATCH.xs"
)


class TestEnforceRoleContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = FUNCTION_PATH.read_text(encoding="utf-8")
        cls.log_event_source = LOG_EVENT_PATH.read_text(encoding="utf-8")
        cls.auth_me_source = AUTH_ME_PATH.read_text(encoding="utf-8")
        cls.my_events_source = MY_EVENTS_PATH.read_text(encoding="utf-8")
        cls.update_password_source = UPDATE_PASSWORD_PATH.read_text(
            encoding="utf-8"
        )
        cls.signup_source = SIGNUP_PATH.read_text(encoding="utf-8")
        cls.welcome_email_source = WELCOME_EMAIL_PATH.read_text(
            encoding="utf-8"
        )

    def test_preserves_function_signature_and_guid(self):
        self.assertIsNotNone(
            re.search(
                r'function "Quick Start/enforce_role"\s*\{\s*input\s*\{'
                r".*?\bint user_id\b.*?\btext required_role\b",
                self.source,
                re.DOTALL,
            )
        )
        self.assertIn('guid = "7xVXPTnU16TJsslvt3O4zfBuAag"', self.source)

    def test_film_year_validation_uses_supported_timestamp_filters(self):
        expected_current_year = (
            '(now|format_timestamp:"Y":"UTC"|to_int)'
        )
        for endpoint_path in (FILM_CREATE_PATH, FILM_UPDATE_PATH):
            with self.subTest(endpoint=endpoint_path.name):
                endpoint_source = endpoint_path.read_text(encoding="utf-8")
                self.assertIn(expected_current_year, endpoint_source)
                self.assertNotIn("timestamp_year", endpoint_source)

    def test_reads_current_role_and_active_state(self):
        self.assertRegex(
            self.source,
            r'db\.get user\s*\{[^}]*output = \["role", "is_active"\][^}]*\}',
        )

    def test_checks_user_existence_before_account_state(self):
        self.assertLess(
            self.source.index("precondition ($user != null)"),
            self.source.index("if ($user.is_active == false)"),
        )

    def test_only_explicit_false_marks_account_inactive(self):
        self.assertIn("if ($user.is_active == false)", self.source)
        self.assertNotIn("if ($user.is_active == true)", self.source)
        inactive_check = self.source.split(
            "if ($user.is_active == false)", maxsplit=1
        )[1].split("\n      }\n    }", maxsplit=1)[0]
        self.assert_denial_is_audited_before_throw(
            inactive_check,
            "denied_inactive",
        )

    def test_accepts_only_recognized_roles_for_both_access_levels(self):
        self.assertIn("value = {admin: 2, member: 1}", self.source)
        role_lookup = self.source.index("value = $role_hierarchy|get:$user_role")
        recognized_role_guard = self.source.index(
            "if ($user_role_level == null || $user_role_level <= 0)"
        )
        required_role_lookup = self.source.index(
            "value = $role_hierarchy|get:$input.required_role"
        )
        self.assertLess(role_lookup, recognized_role_guard)
        self.assertLess(recognized_role_guard, required_role_lookup)

    def test_rejects_unrecognized_minimum_role(self):
        self.assertIn(
            "precondition ($required_role_level > 0)", self.source
        )

    def test_role_insufficiency_is_audited_then_denied(self):
        role_check = self.source.split(
            "if ($user_role_level < $required_role_level)", maxsplit=1
        )[1]
        self.assert_denial_is_audited_before_throw(
            role_check,
            "denied_role:",
            result_is_prefix=True,
        )

    def test_unrecognized_user_role_is_audited_then_denied(self):
        role_check = self.source.split(
            "if ($user_role_level == null || $user_role_level <= 0)",
            maxsplit=1,
        )[1]
        self.assert_denial_is_audited_before_throw(
            role_check,
            "denied_role_unrecognized",
        )

    def test_audit_helper_persists_only_declared_metadata(self):
        self.assertRegex(
            self.log_event_source,
            r"int user_id\?\s+text action\s+text result\?",
        )
        self.assertRegex(
            self.log_event_source,
            r"metadata\s*:\s*\{\s*result\s*:\s*\$input\.result"
            r"\s*resource_type\s*:\s*\$input\.resource_type"
            r"\s*resource_id\s*:\s*\$input\.resource_id",
        )
        self.assertNotRegex(
            self.log_event_source,
            r"\$input\.(password|token|email|user(?:\W|$))",
        )

    def test_auth_me_checks_role_before_reading_or_returning_user_data(self):
        role_check = self.auth_me_source.index(
            'function.run "Quick Start/enforce_role"'
        )
        user_read = self.auth_me_source.index("db.get user")
        success_audit = self.auth_me_source.index(
            'action  : "get_auth_user"'
        )

        self.assertIn('auth = "user"', self.auth_me_source)
        self.assertIn("user_id: $auth.id", self.auth_me_source)
        self.assertIn('required_role: "member"', self.auth_me_source)
        self.assertLess(role_check, user_read)
        self.assertLess(role_check, success_audit)

    def test_my_events_checks_role_before_query_and_keeps_user_filter(self):
        role_check = self.my_events_source.index(
            'function.run "Quick Start/enforce_role"'
        )
        event_query = self.my_events_source.index("db.query event_log")

        self.assertIn('auth = "user"', self.my_events_source)
        self.assertIn("user_id: $auth.id", self.my_events_source)
        self.assertIn('required_role: "member"', self.my_events_source)
        self.assertLess(role_check, event_query)
        self.assertIn(
            "where = $db.event_log.user_id == $auth.id",
            self.my_events_source,
        )

    def test_update_password_checks_role_before_password_operations(self):
        role_check = self.update_password_source.index(
            'function.run "Quick Start/enforce_role"'
        )
        password_validation = self.update_password_source.index(
            "precondition ($input.password == $input.confirm_password)"
        )
        user_read = self.update_password_source.index("db.get user")
        password_update = self.update_password_source.index("db.edit user")

        self.assertIn('auth = "user"', self.update_password_source)
        self.assertIn("user_id: $auth.id", self.update_password_source)
        self.assertIn('required_role: "member"', self.update_password_source)
        self.assertLess(role_check, password_validation)
        self.assertLess(role_check, user_read)
        self.assertLess(role_check, password_update)

    def test_public_signup_does_not_accept_user_controlled_role(self):
        input_block = self.signup_source.split("input {", maxsplit=1)[1].split(
            "\n  }", maxsplit=1
        )[0]

        self.assertNotRegex(input_block, r"\brole\b")

    def test_public_signup_assigns_member_explicitly(self):
        self.assertRegex(
            self.signup_source,
            r"db\.add user\s*\{\s*data\s*=\s*\{[^}]*role\s*:\s*"
            r'"member"',
        )

    def test_public_signup_creates_and_returns_auth_token(self):
        token_creation = self.signup_source.index("security.create_auth_token")
        token_assignment = self.signup_source.index("} as $authToken", token_creation)
        response = self.signup_source.index("response =")

        self.assertIn("table = \"user\"", self.signup_source[token_creation:])
        self.assertLess(token_creation, token_assignment)
        self.assertLess(token_assignment, response)
        self.assertRegex(
            self.signup_source[response:],
            r"response\s*=\s*\{\s*authToken\s*:\s*\$authToken",
        )

    def test_public_signup_does_not_change_existing_user_roles_or_states(self):
        self.assertEqual(
            len(re.findall(r"\bdb\.add user\b", self.signup_source)),
            1,
        )
        self.assertNotRegex(
            self.signup_source,
            r"\bdb\.(?:edit|delete)\s+user\b",
        )

    def test_welcome_email_requires_admin_before_lookup_and_send(self):
        role_check = self.welcome_email_source.index(
            'function.run "Quick Start/enforce_role"'
        )
        user_lookup = self.welcome_email_source.index("db.get user")
        email_send = self.welcome_email_source.index("util.send_email")

        self.assertIn('auth = "user"', self.welcome_email_source)
        self.assertIn("user_id: $auth.id", self.welcome_email_source)
        self.assertIn('required_role: "admin"', self.welcome_email_source)
        self.assertLess(role_check, user_lookup)
        self.assertLess(role_check, email_send)

    def assert_denial_is_audited_before_throw(
        self, source, expected_result, result_is_prefix=False
    ):
        audit = source.index('action : "authorization_denied"')
        denial = source.index("throw {")
        self.assertLess(audit, denial)
        audit_source = source[:denial]
        if result_is_prefix:
            self.assertRegex(
                audit_source,
                r'result\s*:\s*"denied_role:"\s*~\s*\$input\.required_role',
            )
        else:
            self.assertIn(f'result : "{expected_result}"', audit_source)
        self.assertIn("user_id: $user.id", audit_source)
        self.assertNotRegex(
            audit_source,
            r"password|token|email|user_record",
        )


if __name__ == "__main__":
    unittest.main()
