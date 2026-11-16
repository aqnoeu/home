# Home para Android — protótipo nativo 0.1.0

Esta pasta contém uma **versão Android independente** do Home para Windows.

## O que já está implementado no código
- Notch grafite com dois olhos vetoriais brancos, piscada e movimentos suaves, inspirado nas proporções do `EyesWidget` do PC.
- Toque no Notch para abrir a Activity em tela cheia, sem painel flutuante expandido.
- Quatro expressões e controles explícitos para iniciar/parar a sobreposição.
- Verificação manual das Releases do GitHub para localizar o artefato `Home-Android.apk` e **abrir a URL de download**, nunca instalar silenciosamente.
- QR Code que aponta à página oficial `https://github.com/aqnoeu/home/releases`.
- Serviço em primeiro plano com notificação persistente enquanto o Notch estiver ativado.

## Limitações reais
- A sobreposição depende de **Permitir exibição sobre outros apps**; posição perto da câmera e visibilidade são determinadas pelo fabricante, pelas áreas de recorte e pela versão do Android. Não é garantido desenhar *dentro* da barra de status ou exatamente sobre a câmera.
- O serviço pode ser interrompido pelo sistema e pode ficar oculto em telas de segurança ou apps que bloqueiam overlays.
- Não há IA, sincronização com PC, captura de conteúdo nem gravação de microfone nesta versão.
- A versão Android não reutiliza diretamente o PySide6: replica o desenho dos olhos em Canvas nativo.
- APK do workflow é **debug/de teste**, não se destina a distribuição permanente. Builds debug de runs diferentes podem ter assinaturas incompatíveis.
- Para atualização futura mantendo os dados é obrigatório criar um **keystore de release estável e protegido** (não publicar no repositório), compilar um APK release assinado e publicar `Home-Android.apk` em uma Release compatível com as versões Windows. Nunca sobrescrever o APK com outro certificado.

## Compilar
Abra a pasta `android/` no Android Studio compatível com AGP 8.7.3 e JDK 17 ou execute:

```bash
gradle :app:assembleDebug
```

A ação **Home Android — APK de teste** no GitHub Actions também compila e anexa `Home-Android-candidato` como artefato. Extraia o ZIP do artefato e instale `app-debug.apk` no Android, autorizando instalação por fonte externa. Desinstale uma versão debug anterior se a assinatura não for compatível (isso apaga os dados locais do app).

## Distribuição de release planejada
1. Proteger o keystore de produção por secrets do GitHub Actions.
2. Compilar e assinar APK Android para cada publicação planejada.
3. Publicar o asset `Home-Android.apk` junto a uma Release oficial sem romper a verificação de versões Windows.
4. Testar manualmente em Android com câmera frontal e diferentes políticas de sobreposição.

## Privacidade
O Home só abre a interface quando tocado; não utiliza microfone, não tem conexão com a versão Windows e não lê outros aplicativos. A consulta de atualizações se conecta ao GitHub apenas após clique em **Verificar atualizações**.

## Atualização dentro do aplicativo (v0.1.2+)
A aba **Verificar atualizações** procura a última Release Android oficial com tag `android-vX.Y.Z` e arquivo `Home-Android.apk`. Havendo versão maior que a instalada, o Home solicita confirmação, baixa o APK no armazenamento privado, valida o SHA-256 fornecido pela API do GitHub, abre o instalador do Android e pede confirmação ao usuário. Não há instalação silenciosa.

**Distribuição:** o workflow `.github/workflows/android-release.yml` publica o APK na própria GitHub Releases, de forma independente da versão Windows, **somente quando as quatro credenciais de assinatura estiverem configuradas** no repositório em *Settings → Secrets and variables → Actions*:

- `HOME_ANDROID_KEYSTORE_BASE64`: conteúdo do arquivo keystore de produção codificado em base64, sem quebras de linha.
- `HOME_ANDROID_KEYSTORE_PASSWORD`: senha do keystore.
- `HOME_ANDROID_KEY_ALIAS`: alias da chave.
- `HOME_ANDROID_KEY_PASSWORD`: senha da chave.

Gere e guarde o keystore fora do repositório, com backup seguro. Use a **mesma chave em todas as versões Android futuras**, pois o Android rejeita a instalação por cima se o certificado mudar. Nunca faça commit do keystore ou das senhas, e nunca reutilize o keystore de debug do GitHub Actions em produção.

**Migração do APK debug 0.1.0/0.1.1 para a primeira versão assinada:** será necessário desinstalar o debug e instalar o `Home-Android.apk` uma única vez, pois as assinaturas são distintas. Depois, novas versões oficiais podem ser instaladas pelo botão interno preservando as configurações.

A compilação de debug continua no workflow `android-build.yml`, apenas para testes e sem promessas de atualização por cima da versão anterior.
