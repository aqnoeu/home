# Home Android — voz Faber (Piper pt_BR-faber-medium)

A voz do Home é **Faber**, modelo Piper em português brasileiro, executado localmente por sherpa-onnx. O mesmo arquivo de modelo é utilizado em Windows e Android.

## Funcionalidades de voz

- **Instalar Faber**: download opcional, único, do pacote oficial de aproximadamente 67 MB, com checksum SHA-256 fixado.
- **Testar Faber**: síntese e reprodução diretamente no Android, sem nuvem, servidor ou chave de API.
- **Diagnóstico**: botão para copiar qual etapa falhou, caso o modelo não carregue ou reproduza.
- **Falar agora**: reconhecimento pelo serviço de entrada de fala do Android (separado do motor de síntese Faber; esse reconhecimento pode usar a rede conforme as configurações do aparelho).
- Na atualização, o Home remove apenas os arquivos do antigo modelo Alex de sua pasta privada; preserva o Notch, os olhinhos e todas as demais preferências.

Fonte: https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-pt_BR-faber-medium.tar.bz2

Modelo SHA-256: `7add3f923ad6bc25ca8a192805fd1a64d1b3893e4611c4a9719545a825039a83`

## Compilar

Na raiz do repositório, instale a biblioteca JNI oficial antes do Gradle:

```bash
bash android/prepare-sherpa.sh
cd android
gradle --no-daemon :app:assembleDebug
```

Os workflows oficiais fazem a mesma etapa e assinam a release com o keystore estável. Instale sempre **Home-Android.apk** da Release oficial (não o debug) para atualizar por cima, preservando dados.

A reprodução de áudio precisa ser verificada em aparelho físico: passar na compilação não comprova qualidade ou fluidez. O Home nunca substituirá Faber silenciosamente por uma voz do Google.
