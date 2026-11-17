# HOME Intersect — arquitetura e regras de evolução

> Documento de continuidade. Última revisão: 17/11/2026.
> Este arquivo descreve o estado da refatoração, não promete recursos ainda não instalados.

## Objetivo desta refatoração

Separar **interface**, **motor de voz**, **comandos locais**, **integrações**, **armazenamento** e **atualizações**.
Fazer mudanças pequenas, testáveis e reversíveis. Não alterar a identidade oficial
dos olhos, os dados do usuário, permissões nem o comportamento dos recursos existentes
sem necessidade.

## Windows — mapa de módulos

| Arquivo | Responsabilidade |
| --- | --- |
| `home.py` | Inicialização, lifecycle, notch, eventos globais e orquestração |
| `home_eyes.py` | Renderização e animações dos olhos; import legado `from home import EyesWidget` preservado |
| `home_edit_dialog.py` | Editor avançado de geometria e posição |
| `home_navigation.py` | Navegação e páginas do notch expandido |
| `home_ui.py` | Componentes do painel |
| `home_assistant.py` | Chat e fluxo de respostas |
| `home_voice.py` | Reconhecimento e sessão de voz |
| `home_faber.py` | Síntese de voz offline |
| `home_emotions.py` | Estado de emoção e contexto |
| `home_device.py` | Consultas locais de sistema, sem rede |
| `home_integrations.py` | Ações Windows autorizadas e ponte Chrome opt-in |
| `home_chat_store.py` | Histórico de conversas |
| `update_service.py` / `updater.py` | Atualização, assinatura e instalação |

### Próxima decomposição do Windows

Dividir `Home` em controladores de layout/arraste, configurações, atualização
e ciclo de vida, mantendo a interface pública. Refatorar somente após testes
de regressão suficientes para o comportamento do notch.

## Android — mapa de módulos

| Arquivo | Responsabilidade |
| --- | --- |
| `MainActivity.java` | Lifecycle, navegação, permissões, decisões do usuário e composição de telas |
| `HomeUiKit.java` | Botões, campos, cartões, notas e espaçamento reutilizáveis |
| `HomeLocalCommands.java` | Identificação de comandos locais e consultas read-only; **não executa efeitos de UI** |
| `WakeWordService.java` | Ciclo de microfone, frases de ativação, notificações e escuta de fundo |
| `HomeOfflineReplies.java` | Respostas offline no background sem depender da Activity ou do microfone |
| `WakeModelInstaller.java` | Instalação/validação do modelo offline |
| `HomeVoice.java` | Escuta da consulta completa |
| `FaberOffline.kt` | Voz de resposta offline |
| `EyesView.java` | Desenho dos olhos e estados visuais |
| `OverlayService.java` | Janela flutuante Android e ciclo de vida do notch |
| `HomeGroq.java` | Pedidos ao provedor de IA |
| `HomeChatStore.java` | Conversas locais |
| `UpdateHelper.java` | Download oficial e instalação com consentimento |
| `DeviceHub.java` | Consultas e atalhos do dispositivo |
| `HomeHubAccount.java` | Conta HOME e sincronização |
| `VoiceEnrollment.java` | Amostras e preferências de voz |

### Próxima decomposição do Android

1. Extrair as telas de configurações de `MainActivity` em controladores específicos,
   sem navegação circular nem referências fortes que sobrevivam à Activity.
2. Extrair UI do histórico/chat em componentes independentes preservando o teclado e scroll.
3. Isolar o reconhecimento da frase de ativação da captura de comandos e da resposta;
   adotar máquina de estados explícita, sem dois microfones simultâneos.
4. Usar testes de instrumento no Android físico (incluindo HyperOS) antes de afirmar
   que reconhecimento contínuo em segundo plano está funcionando.

## Contratos que não devem quebrar

- **Olhos:** verde-neon só após detecção da frase e enquanto o comando está sendo
  capturado. O microfone passivo não deixa os olhos verdes. Resposta da Faber usa branco.
  Download: base cinza + preenchimento branco real + piscada única a 100%.
- **Ativação:** 'Ei Home', 'Ok Home', 'Home'; permissões explícitas;
  no Android, restrições de abertura em segundo plano dependem do SO.
- **Dados:** preservar conversas, conta, configurações e versões anteriores.
- **Permissões:** execução de comandos sensíveis só com consentimento;
  nunca executar código arbitrário produzido por LLM.
- **Privacidade:** áudio offline por padrão quando aplicável; não salvar/enviar
  gravação sem solicitação explícita.
- **Marca:** `HOME_Manual_de_Marca_v1_2.pdf` é referência; não trocar a arte oficial.
- **Lançamento:** testar Android/Windows; versão nova precisa ter versionCode superior;
  verificar publicação de APK e ZIP antes de anunciar links.

## Estratégia de trabalho

1. Antes de editar: localizar o módulo dono da responsabilidade, ler testes e anotar
   comportamento atual.
2. Alterar uma responsabilidade por PR; adicionar teste de contrato.
3. Rodar testes unitários, compilação Android e verificação Windows.
4. Só integrar após testes verdes; acompanhar publicação de versão assinada.
5. Anotar decisões e pendências em `docs/HOME_EVOLUTION_ROADMAP.md`.
