# Tarefas

- [ ] Mapear os endpoints e funções de autenticação, recuperação, autorização e auditoria que serão alterados.
- [ ] Definir o conjunto mínimo de campos permitidos nos metadados de eventos.
- [ ] Remover objetos completos de usuário, hashes, tokens e dados de recuperação dos logs.
- [ ] Proteger o endpoint de envio de boas-vindas com autenticação e autorização no backend.
- [ ] Integrar a verificação de papel aos endpoints administrativos da fundação.
- [ ] Adicionar estado de acesso do usuário com valor padrão ativo e preservar compatibilidade com usuários existentes.
- [ ] Rejeitar usuários desativados no login comum e no login por magic link.
- [ ] Tornar o pedido de recuperação de senha indistinguível para e-mails existentes e inexistentes.
- [ ] Corrigir o retorno interno do gerador de magic link sem expor token ou existência de usuário.
- [ ] Implementar consumo atômico ou condicional do magic link para impedir reutilização concorrente.
- [ ] Registrar eventos de sucesso e falha de autenticação/autorização sem dados sensíveis.
- [ ] Validar os recursos Xano modificados no ambiente Xano e executar os cenários críticos da especificação.
- [ ] Registrar limitações ou decisões que dependam da configuração do serviço Xano ou do frontend Reflex.
