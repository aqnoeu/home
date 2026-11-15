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

**Somente execução manual:** Actions → Publicar Home para Windows → Run workflow, informando a versão que consta em `update_service.py` e as notas aprovadas. Um commit normal não dispara Release.

Ainda não há .exe validado em uma máquina Windows nesta etapa; trate a versão como candidata a testes até a aprovação.

## Crédito
Os olhos são um desenho independente em PySide6 inspirado na ideia visual do [FluxGarage/RoboEyes](https://github.com/FluxGarage/RoboEyes); não há cópia da biblioteca para Arduino.
