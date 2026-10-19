# Evidências de verificação

## Comparação visual

A referência e a implementação foram medidas com o mesmo viewport. Os valores abaixo são dimensões CSS computadas no navegador.

| Cenário | Referência | Implementação |
| --- | --- | --- |
| Desktop 1440 × 900 — painel | 460 × 642,1 px | 460 × 642 px |
| Desktop — botão | 378,4 × 56 px | 378,4 × 56 px |
| Celular 390 × 844 — painel | 350,4 × 671,6 px | 350,4 × 671,1 px |
| Celular — botão | 300,8 × 56 px | 300,8 × 56 px |

Não foi detectado overflow horizontal nos dois viewports. Em 390 × 640, a página cria rolagem vertical e o rodapé fica totalmente alcançável.

Capturas finais:

- [Desktop 1440 × 900](./evidence/login-desktop-1440x900.png)
- [Celular 390 × 844](./evidence/login-mobile-390x844.png)

## Acessibilidade e comportamento

- A ordem de foco por teclado é login, senha, visibilidade da senha, recuperação e envio.
- Todos os cinco controles exibem contorno ciano com `:focus-visible`.
- A alternância da senha preserva o valor e muda o nome acessível entre “Mostrar senha” e “Ocultar senha”.
- Enter com campos vazios exibe “Informe login e senha para continuar.” na região `role="alert"`.
- O diálogo de recuperação abre sem enviar dados, valida e-mail em português e fecha com Escape.
- O CSS respeita `prefers-reduced-motion: reduce`.

## Validações técnicas

- Compilação: `.venv/Scripts/reflex.exe compile --dry`.
- Execução: `.venv/Scripts/reflex.exe run --env prod --single-port`.
- Testes: `.venv/Scripts/python.exe -m unittest discover -v`.
- OpenSpec: `openspec validate redesenhar-tela-login --strict`.
