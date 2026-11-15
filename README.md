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
