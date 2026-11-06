// Parâmetros vigentes da política, para a estimativa exibida na devolução.
// O valor que vale é sempre o calculado na gravação da devolução.
query "multas/politica" verb=GET {
  api_group = "Locações"
  auth = "user"
  input {
  }
  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "member"}
    } as $role_check
    function.run "Locacoes/fine_policy" {
      input = {}
    } as $policy
  }
  response = $policy
  tags = []
  guid = "q6rT5Aj9cgbPNDG0YOHUd8h7LKk"
}
