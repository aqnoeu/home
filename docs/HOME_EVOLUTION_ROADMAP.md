# HOME Intersect — roteiro do rebranding e evolução

> Registrado em 17/11/2026 para retomar em outros chats/sessões.
> **ESTADO:** ideias e referências. Nada aqui representa funcionalidade automaticamente publicada.
> Não confundir HOME Intersect (`aqnoeu/home`), HOME Writer e HOME Hub.

## Decisão de produto

**HOME 2.0 — Uma experiência, dois dispositivos.**
Manter o nome HOME, o conceito de notch e **os olhos oficiais do Manual de Marca v1.2**.
Não substituir a logo por olhos que lembram sinal de pausa. Aprimorar a experiência
usando componentes e padrões implementados de forma independente.

Prioridade máxima: qualidade do caminho básico **chamar → ouvir → interpretar →
responder → retornar à escuta**, em vez de acrescentar telas e funcionalidades soltas.

## Referências técnicas pesquisadas

- [OpenDex](https://github.com/wassgha/opendex) — MIT; assistente voice-first,
  permissões explícitas, interrupção e orquestração de ações.
- [PILLAR Dynamic Island](https://github.com/warpirate/pillar-dynamic-island-for-windows) —
  MIT; notch Windows, mídia, brilho, notificações, temporizador, métricas.
- [EchoIsland](https://github.com/FunplayAI/EchoIsland) — MIT; cartões de sessão,
  eventos, tarefas e feedback em tempo real.
- [Xiaozhi ESP32](https://github.com/78/xiaozhi-esp32) — MIT; ideias de assistente
  por voz e integração, base aberta associada ao robô Troko.
- [Xiaozhi Android Client](https://github.com/TOM88812/xiaozhi-android-client) —
  Apache-2.0; fluxo de voz e chat Android/iOS.
- [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx) — Apache-2.0; STT, TTS,
  VAD, motores offline; selecionar **modelo realmente compatível com português**.
- [Whispr](https://github.com/Krshs90/Whispr) — MIT; interação IA em ilha desktop.
- [desktop-ai-buddy](https://github.com/gtradigo/desktop-ai-buddy) — MIT;
  olhos animados, Whisper/Piper/Ollama para desktop Linux.
- [BitMon](https://github.com/beped/BitMon) — licença não confirmada;
  referências de estados e expressões, **não copiar código sem licença**.
- [OpenCompanion](https://github.com/vynride/opencompanion) — AGPL-3.0;
  microfone e assistente Android; avaliar obrigações de copyleft antes de integrar.
- [NOVA](https://github.com/Aniketsingh2104/NOVA) — licença não confirmada;
  assistente offline Android e personalização de comandos; só estudo.
- [Sentry](https://github.com/alekslime/Sentry) — licença não confirmada;
  assistente contextual Windows; só estudo.
- Troko-Desk: referência de UX, mas disponibilidade gratuita, licença e
  acesso ao código devem ser verificados em fonte oficial antes de reutilização.

**Regra de licença:** inspiração visual e padrões de produto não autorizam
cópia de código, assets ou marcas; reutilização exige licença compatível,
créditos/avisos apropriados e avaliação das obrigações de distribuição.

## Fase 1 — estabilidade [ALTA / PRIMEIRO]

- [ ] Teste real do wake word no aparelho do usuário; medir falsas ativações,
  tempo de reconhecimento, wake após 10 minutos, tela desligada, notificações
  e retomada do microfone; diagnóstico visível.
- [ ] Separar detector de wake word do transcritor de comandos. Comparar
  AndroidWakeWord/ONNX, Sherpa-ONNX e modelos pt-BR com Vosk.
- [ ] Testar vozes gravadas com autorização, incluindo 'Ei Home',
  'Ok Home' e 'Home' isolado; usar áudio para avaliação/treinamento
  apenas conforme consentimento e possibilidade técnica.
- [ ] Evitar microfones concorrentes, sessões travadas e avisos de
  'HOME ouviu' sem mensagens ou respostas; melhorar background Faber.
- [ ] Garantir instalador Android, versionCode crescente, atualização
  assinada, recuperação após falha e indicador real de download.
- [ ] Remover travamentos de telas, melhorar feedback de erro e
  confiabilidade do histórico de chat.
- [ ] Medir desempenho CPU/RAM e bateria; evitar modelos pesados em loop.

## Fase 2 — rebranding de experiência [ALTA / DEPOIS DA BASE]

- [ ] Manter arte oficial dos olhos: grafite #0B111A, branco, ação
  #2F6BFF, laranja pontual #FF6A00, verde apenas semântica #00C46A.
- [ ] Android: layout mobile-first com chat rolável, entrada fixa, opção
  de múltiplas conversas, tipografia legível, margens e quebras de texto.
- [ ] Windows: notch compacto por padrão; expandir para cartões contextuais
  em vez de painel grande com muitos botões.
- [ ] Criar sistema de componentes: cards, estados, ícones, configurações,
  banners de atualização, vazios, carregamento e confirmação.
- [ ] Reduzir densidade de navegação, distinguir status reais da decoração;
  fazer on-boarding e instalação orientada das dependências opcionais.
- [ ] Harmonizar animações de escuta, fala, processamento, erro, bateria,
  atualização e modo Lovabow; não substituir a logo oficial.
- [ ] Revisar navegação por acessibilidade, contraste, alvos de toque e
  dimensões de telas pequenas.

## Fase 3 — assistente mais útil [DEPOIS]

- [ ] Interromper Faber e retomada de conversa sem repetir wake word
  durante janela curta e controlada.
- [ ] Comandos offline para hora/data/bateria/rede/armazenamento e estado local.
- [ ] Timer, pomodoro, modo foco, lembretes e rotinas com permissões adequadas.
- [ ] Controles Windows (apps, som, mídia, notificações) e Android
  (atalhos de sistema) sob consentimento.
- [ ] Conversa por streaming, cancelamento, modelos locais para consultas
  simples e Groq para perguntas complexas.
- [ ] Sincronização autorizada de histórico, preferências e perfis via
  HOME Hub, com privacidade e opção de desvincular.
- [ ] Contexto de tela ou documentos somente com consentimento explícito;
  automações com confirmação e auditoria.
- [ ] Futuramente, integrar HOME Writer por ponte autenticada,
  separadamente, conforme `HOME_BACKLOG.md`.

## Critérios de aceite antes de publicar como 'pronto'

- Wake word reconhece em condições de teste reais; não ativar com outras vozes
  ou palavras sem avaliar o risco, tampouco desaparecer após uma chamada.
- Pedido de voz + resposta aparece no histórico em segundo plano quando permitido.
- As ações têm estado visual verdadeiro; sem verde contínuo por microfone aberto.
- APK assinado instala e atualiza; Windows ZIP inicia, recolhe e expande.
- Testes de regressão e builds em CI verdes; problemas não reproduzidos
  em hardware devem ser reportados como 'não validados no dispositivo'.
- Nenhum recurso anunciado como implementado só porque consta neste roteiro.

## Como retomar em outro chat

Indique: **'Continue o roteiro HOME Intersect em
`aqnoeu/home/docs/HOME_EVOLUTION_ROADMAP.md`, respeitando
`docs/HOME_ARCHITECTURE.md`. Comece pela Fase 1.'**

Consultar o repositório `main` antes de decidir o que já foi entregue.
