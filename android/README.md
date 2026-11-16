# Home Android — notch e Alex offline (v0.1.5)

O Home Android é o aplicativo nativo que acompanha o Home Windows, com identidade visual dos olhinhos aprovada e personalização de largura, altura, posição e distância entre os olhos.

## Voz Alex totalmente local
- A aba **Voz** tem o botão **Instalar Alex**: o usuário autoriza um download único de aproximadamente 329 MB (modelo Kokoro v1.0 português), extraído na pasta privada do aplicativo. É necessário ter aproximadamente 850 MB livres temporariamente.
- Depois de instalada, a síntese de voz **pm_alex, speaker ID 43** acontece no próprio celular, sem servidor e sem limite mensal, via **sherpa-onnx Android v2.0.1** (biblioteca oficial, baixada pelo CI com SHA-256 fixado).
- A fonte do modelo é [cristianoaredes/kokoro-pt-br](https://huggingface.co/cristianoaredes/kokoro-pt-br). O Android valida estrutura e tamanhos na extração. **Ainda é necessário testar fisicamente a reprodução no Xiaomi 13 Pro**. Não afirmar execução validada só porque o APK compila.
- Quando a voz não está instalada, o Home informa a ausência; **não usa a voz Google como se fosse Alex**.
- Reconhecimento de voz ao apertar **Falar agora** ainda é fornecido pelo serviço de reconhecimento de fala instalado no Android. Isso é separado da síntese offline da Alex.
- No Windows, Alex usa Kokoro local também. Em **Voz**, o botão de instalação obtém o modelo e a opção SAPI5 é alternativa **apenas quando explicitamente escolhida**.
- Nem Android nem Windows exigem Cloudflare, URL, token ou chave de IA para usar a voz Alex.

## Compilação
Os workflows Android baixam a biblioteca oficial `sherpa-onnx-2.0.1.aar`, validando SHA-256. Ela não é commitada ao repositório. Para compilar manualmente na raiz do projeto, rode:

```bash
bash android/prepare-sherpa.sh
cd android
gradle --no-daemon :app:assembleDebug
```

A versão oficial é publicada em `android-vX.Y.Z` na seção Releases do GitHub, assinada pelo mesmo keystore privado; pode atualizar **por cima** da versão oficial anterior pelo botão Atualizações no aplicativo. A versão debug do GitHub Actions não é assinada com o certificado de release.

## Privacidade e limitações
O Home não acessa aplicativos de terceiros nem exige configurar servidores para funcionar. O download inicial do modelo e a verificação de atualizações exigem internet. Áudio de saída é produzido localmente. O reconhecimento da **entrada de voz** pode usar recursos online ou offline conforme o serviço de reconhecimento do dispositivo; ele não está implementado como mecanismo Vosk local no Android.

A sobreposição do notch depende da permissão do sistema e pode ser limitada em regiões de barra de status do HyperOS.
