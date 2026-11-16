# HOME Intersect — melhorias planejadas

Atualizado em 16/11/2026. Este arquivo registra propostas, não funcionalidades já instaladas.

## Próxima etapa: conectar HOME Intersect ↔ HOME Writer
- Conectar a extensão Writer ao HOME Windows por protocolo local autenticado, reutilizando a ponte existente somente após autorização específica para o Writer.
- Oferecer comandos de correção, reescrita, aprofundamento de trecho e pesquisa/explicação sem abrir páginas extras.
- Seleção de texto e envio para o Writer apenas após ação explícita; o HOME não deve ler documentos ou abas automaticamente.
- O Writer mantém alterações com aceitar/rejeitar sem perder o original; HOME pode acompanhar o contexto somente durante a sessão autorizada.
- Validar segurança: token por sessão, origem da extensão permitida, tamanho limite, controle de acesso e revogação de permissão.
- Integração não implementada neste pacote.

## Interação com dispositivos — próximas melhorias
- Android: painel de saúde do aparelho (memória e armazenamento com permissões mínimas); abrir telas do sistema sob demanda.
- Android: automações opcionais, condicionadas a permissões explícitas e restrições do Android para execução em segundo plano.
- Windows: informações locais úteis (bateria de notebook, dispositivos conectados) e mais comandos predefinidos com confirmação.
- Sincronização PC–celular: projeto separado com pareamento explícito, criptografia e revogação; sem acesso remoto permanente por padrão.
- Extensão Writer e permissões corporativas: proibir leitura silenciosa de documentos e ações executáveis arbitrárias.

## Incluído neste pacote
- QR Code de download acessível em Configurações → Geral no Android.
- Hora, data e nível de bateria respondidos localmente no Android, sem Groq.
- Atalhos explícitos para configurações de Wi-Fi e Bluetooth do Android.
- Windows: abrir Gerenciador de Tarefas e Painel de Controle pelo catálogo permitido, respeitando a confirmação existente.

## Conectores locais implementados nesta atualização
- Android: diagnóstico sob demanda de bateria, rede (sem SSID ou localização), estado Bluetooth com permissão, saída e volume de áudio, RAM e espaço de armazenamento.
- Android: atalhos de agenda, inclusão de evento e alarmes no aplicativo do sistema; não lê agenda pessoal automaticamente.
- Android: consulta do texto copiado apenas depois de clique, sem envio à IA.
- Android: visualização opcional de notificações via serviço autorizado e resposta por RemoteInput somente com confirmação do usuário; nada salvo ou enviado à IA.
- Windows: recursos de diagnóstico e atalhos locais, sem automação silenciosa.
- Fora do escopo: pareamento celular-PC e integração HOME Writer.
