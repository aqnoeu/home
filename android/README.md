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
