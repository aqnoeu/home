# Home — Notch animado para Windows

Home é um widget de entalhe para a borda superior do Windows, inspirado no formato de uma Dynamic Island, com olhos animados expressivos e dimensões personalizáveis.

## Recursos da versão 0.7 (código-fonte)
- Entalhe acoplado à borda superior, com curvas laterais e abertura animada.
- Olhos vetoriais com piscadas, olhares aleatórios e expressões.
- Modo Edição: redimensionar arrastando as alças, tanto recolhido quanto expandido.
- Arrastar horizontalmente com o botão direito.
- Preferências preservadas em `~/.home_notch.json` (fora da pasta do aplicativo).
- Botão **Verificar atualizações** usando GitHub Releases.

## Executar pelo Python
Requer Python 3.10+ e Windows:

```powershell
py -m pip install -r requirements.txt
py home.py
```

Você também pode usar `INICIAR_HOME.bat`. No modo Python, o botão verifica as versões, mas **a instalação automática funciona somente no executável Home.exe**.

## Atualizações automáticas
Ao publicar uma Release com `Home-Windows.zip` e `SHA256SUMS.txt`, o Home instalado via .exe pode oferecer atualização manual com um clique. O pacote é conferido por SHA-256 e instalado por um atualizador externo. O checksum detecta corrupção ou alteração relativa ao arquivo da própria Release; não substitui uma assinatura de código independente.

Não existe atualização automática sem confirmação do usuário. As configurações são mantidas.

## Compilação e publicação
O workflow `.github/workflows/windows-release.yml` compila `Home.exe` e `HomeUpdater.exe` com PyInstaller em runner Windows.

**Release automática:** alterações em `home.py`, `update_service.py`, `updater.py` ou `requirements.txt` enviadas à branch `main` acionam o GitHub Actions. A versão patch aumenta automaticamente, os executáveis são compilados e uma nova Release é publicada se a compilação passar. Também é possível iniciar manualmente em Actions. **Publicar código na main agora significa autorizar sua publicação como Release**, sem etapa adicional de aprovação.

Ainda não há .exe validado em uma máquina Windows nesta etapa; trate a versão como candidata a testes até a aprovação.

## Crédito
Os olhos são um desenho independente em PySide6 inspirado na ideia visual do [FluxGarage/RoboEyes](https://github.com/FluxGarage/RoboEyes); não há cópia da biblioteca para Arduino.


## Interações locais (versão em desenvolvimento)
No painel expandido, clique em **Interações**. Os recursos começam desligados.

- **Olhos:** ative “acompanhar o mouse” e “reagir a cliques” separadamente.
- **Windows:** ative a permissão e clique explicitamente na ação desejada: Bloco de Notas, Calculadora, Explorador, volume ou controles de mídia. O Home não aceita comandos arbitrários.
- **Chrome:** ative “Receber páginas autorizadas do Chrome” no Home, clique em “Copiar código de conexão” e configure a extensão abaixo. Cada aba só é lida após clicar em “Compartilhar esta aba com Home”.

### Instalação da extensão Chrome (uma vez)
1. Baixe `Home-Chrome-Extension.zip` na [última Release](https://github.com/aqnoeu/home/releases/latest) e extraia para uma pasta fixa, por exemplo `Documentos/Home-Chrome-Extension`.
2. Abra `chrome://extensions` no Chrome, habilite **Modo do desenvolvedor** e clique em **Carregar sem compactação**.
3. Selecione a pasta extraída que contém `manifest.json`.
4. No Home, acesse **Interações**, marque **Receber páginas autorizadas do Chrome** e clique em **Copiar código de conexão**.
5. Abra a extensão, cole o código e clique em **Salvar código neste navegador**.
6. Abra uma página comum e clique em **Compartilhar esta aba com Home**. A página aparece no painel de Interações do Home.
7. O botão **Listar abas abertas** solicita uma permissão opcional do Chrome e exibe títulos apenas dentro da extensão. Para compartilhar uma aba selecionada, abra a extensão nela e autorize explicitamente.

**Privacidade:** a extensão não lê todas as páginas em segundo plano. Ao compartilhar, ela transmite ao processo Home local (127.0.0.1) o título, a URL e até 5.000 caracteres visíveis da aba. Não envie páginas com senhas, informações bancárias ou outros dados sensíveis. O código de conexão é salvo no armazenamento local do Chrome; a ponte Home não é exposta na rede. É possível desativar as permissões no Home a qualquer momento. Não há envio para serviços de IA.

As preferências das integrações ficam em `~/.home_integrations.json` e são preservadas nas atualizações. Se quiser revogar o código da extensão, remova esse arquivo com o Home fechado e inicie novamente (isso redefine as permissões). A extensão é um pacote separado do autoatualizador do Home; quando houver mudança nela, é necessário substituir os arquivos da extensão e recarregá-la em `chrome://extensions`.

### Status
Compilação e verificação de sintaxe são realizadas por GitHub Actions em Windows. Reações do mouse, execução dos aplicativos e leitura do Chrome dependem de teste manual no computador do usuário. Não execute arquivos de fontes não confiáveis.


## Voz e microfone (Home Voice)

O Home inclui um cartão **Voz e microfone** com dois modos: **Falar agora** (botão) e ativação por **"Ei, Home"** (opcional). Ambos usam reconhecimento offline em português pelo Vosk e respostas pelas vozes locais do Windows (pyttsx3/SAPI5).

### Primeira configuração

1. Atualize o Home pelo botão **Atualizações** após a publicação da Release que inclui o módulo de voz.
2. Abra **Voz e microfone** no Home expandido.
3. Clique em **Baixar modelo de português (aprox. 31 MB)** e confirme. O download é feito do [site oficial do Vosk](https://alphacephei.com/vosk/models), para a pasta `%LOCALAPPDATA%\Home\models\vosk-model-small-pt-0.3`.
4. Ative **Permitir que o Home use o microfone**. O padrão é **desativado**.
5. Para falar pelo botão, clique em **Falar agora / parar**. Para invocar sem clicar, ative **Escuta contínua de "Ei, Home"**. Esse segundo modo mantém o microfone aberto localmente enquanto ligado.
6. Ative **Permitir respostas faladas** se quiser ouvir a resposta no alto-falante.
7. Para executar controles do Windows por voz, ative **Permitir controles do Windows** em **Interações**; cada comando reconhecido ainda solicita confirmação antes de agir.

### Comandos iniciais
- "Ei, Home, abra a calculadora"
- "Ei, Home, abra o Bloco de Notas"
- "Ei, Home, abra o Explorador de Arquivos"
- "Ei, Home, aumente o volume"
- "Ei, Home, pause a música"

Também pode dizer os mesmos comandos diretamente pelo botão, sem "Ei, Home". Ainda não há um modelo conversacional de IA: respostas são mensagens associadas a comandos seguros predeterminados.

### Privacidade e limitações
- Microfone, escuta da palavra de ativação e voz sintetizada têm controles independentes, todos **desativados por padrão**.
- A transcrição roda no computador: **nenhuma gravação ou texto é enviado a servidor de IA**; o Home não salva áudio.
- O Home mostra um indicador discreto quando o microfone está ativo.
- O modo "Ei, Home" usa reconhecimento contínuo local de frases, não um detector de palavra-chave dedicado: pode reconhecer incorretamente ou ignorar frases, especialmente em ambientes ruidosos.
- O sistema de fala utiliza vozes **instaladas** no Windows. Se não houver uma voz portuguesa, a qualidade ou o idioma da fala poderá variar.
- O modelo Vosk não é incluído no executável e é baixado somente com autorização.
- Microfones bloqueados nas configurações de privacidade do Windows precisam ser autorizados no próprio sistema.
- É possível desativar o microfone a qualquer momento no menu **Voz e microfone**.

O projeto continua com a aparência grafite, o Modo Edição, a extensão opcional para Chrome, olhos interativos e atualizador por GitHub Releases.


### Correção do erro "Modelo de voz incompleto"

As primeiras versões do Home procuravam apenas `am/final.mdl`, mas o modelo oficial de português `vosk-model-small-pt-0.3` usa a estrutura antiga do Vosk com `final.mdl`, `mfcc.conf`, `Gr.fst` e `HCLr.fst` na raiz. O Home agora aceita ambas as estruturas e verifica o SHA-256 do ZIP oficial antes da extração.

Se o download falhar, atualize o Home para a Release com a correção e clique novamente em **Baixar modelo de português**. O Home limpa automaticamente a pasta temporária de um download interrompido; não é necessário apagar manualmente arquivos nem alterar as permissões do microfone.


## Interface navegável no próprio entalhe

Os cartões do Hub não abrem mais janelas de configuração separadas. Ao escolher **Voz**, **Interações**, **Modo edição**, **Atualizações** ou **Encerrar**, o próprio Home aumenta temporariamente para um tamanho de leitura confortável (até 690 × 610 px, respeitando a resolução da tela). Uma barra de navegação permite alternar entre as funcionalidades e retornar ao Hub; ao voltar, as dimensões salvas do Hub são restauradas. Os olhinhos continuam visíveis acima do conteúdo.

A página **Voz** inclui suas permissões, botão de fala, estado do microfone, modelo instalado e confirmação **Sim/Não** de ações reconhecidas, sem popups adicionais. A página **Atualizações** permite procurar versões e confirmar a instalação internamente. O **Modo edição** dispõe dos controles de largura, altura e distância da esquerda, preservando as configurações anteriores.

Essa organização oferece uma estrutura expansível para uma futura página de assistente de IA, **sem** habilitar IA ou conceder novas permissões no momento.

Caso você esteja usando o Home anterior, use **Atualizações** para receber a nova interface depois da publicação da Release no GitHub.


## Escolher a voz do Home

No painel expandido, abra **Voz e microfone**. O seletor lista apenas as vozes **SAPI5 realmente disponíveis no Windows** (não inclui necessariamente as vozes naturais do Narrador). Escolha a voz, ajuste **Velocidade** (90–280) e **Volume** (0–100%) e clique em **Testar voz selecionada** para ouvir uma prévia mesmo sem microfone. As preferências são salvas em `.home_integrations.json` e aplicadas às respostas faladas do **Assistente** e dos comandos de voz. A opção **Automática** prioriza uma voz em português. Caso nenhuma voz SAPI5 esteja disponível, a interface apresenta o diagnóstico sem inventar opções.


## Kokoro Alex — fala neural local (pt-BR)

Em **Voz e microfone → Mecanismo de fala**, selecione **Alex — Kokoro**. Clique em **Instalar Alex** para baixar, uma única vez, os arquivos do modelo (~340 MB), armazenados em `%LOCALAPPDATA%\\Home\\models\\kokoro-v1.0`. Os arquivos são baixados por HTTPS da [release oficial do kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1), com SHA-256 verificado antes da ativação. **O microfone não é necessário.** Depois da instalação, a geração é offline e o áudio é reproduzido no dispositivo pelo SoundDevice. O botão **Testar voz selecionada** permite ouvir Alex, e o Assistente digitado usa a mesma preferência.

Se o modelo não estiver instalado, a síntese continua com a voz Windows SAPI5, sem impedir o uso do Home. Pode-se reverter para SAPI5 a qualquer momento, sem perder o modelo baixado. **Kokoro-82M**: Apache-2.0; biblioteca **kokoro-onnx**: MIT. Dependências do mecanismo de fonetização podem possuir outras licenças e devem ser consideradas em qualquer redistribuição. A integração foi organizada em `home_kokoro.py` para que uma futura versão Android possa reutilizar o contrato de síntese de áudio, ainda que necessite de um empacotamento e interface específicos.
