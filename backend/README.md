# Home IA — mesmo backend para Windows e Android

O Home Windows e o Home Android podem conversar com o **mesmo servidor HTTPS** e compartilhar um estilo de personalidade. Isso não implica sincronização de dispositivos: cada app é independente e configura o endpoint e seu token.

## Contrato
Requisição: `POST https://<seu-worker>.workers.dev/ai`
- Cabeçalho: `Authorization: Bearer <HOME_ACCESS_TOKEN>`
- JSON: `{"message":"Olá Home", "mood":0}`
Resposta: `{"reply":"Olá!", "mood":1}`

Os estados são 0 normal, 1 amigável, 2 sonolento e 3 bravo. O servidor devolve resposta curta em pt-BR. No celular, o botão de voz usa reconhecimento e fala do Android. No Windows, usa Vosk e as vozes disponíveis (SAPI5/Kokoro).

## Implantação opcional na Cloudflare
O arquivo `home-ai-worker.js` é código-fonte pronto para um Worker, mas **não está publicado automaticamente**. Crie um Worker HTTPS e cadastre DOIS segredos *no Worker*, não neste repositório:
- `GROQ_API_KEY`: uma **nova** chave da Groq (não reutilize qualquer chave anteriormente exposta)
- `HOME_ACCESS_TOKEN`: segredo longo, independente da chave da Groq, para autenticar Home Windows/Android

No aplicativo (página Assistente → configurar IA), informe a URL do Worker terminada em `/ai` e apenas o `HOME_ACCESS_TOKEN`. Não inclua `GROQ_API_KEY` no cliente.

O exemplo usa o modelo `openai/gpt-oss-20b`; verifique os limites e as tarifas em https://console.groq.com/docs/models. Configure controles de uso/rate limiting no Worker antes de ampliar o acesso. O Home não grava histórico remoto por conta própria.

## Aviso importante
Até configurar e publicar esse servidor, a IA conversacional **não está ativa**: as reações locais funcionam, mas respostas geradas por modelo não. Não substitua a chave de assinatura Android pelos segredos de IA.


## Home IA — implantação Cloudflare e voz Alex

O Worker `home-ai` foi criado na conta Cloudflare associada ao projeto, com URL
`https://home-ai.aqnoeu-home.workers.dev/ai`. Os aplicativos Windows e Android
pré-preenchem este endpoint. A publicação do código não configura automaticamente
os secrets do usuário.

No painel **Cloudflare → Workers & Pages → home-ai → Settings / Variables and Secrets**,
configure:
- `HOME_ACCESS_TOKEN`: token privado de acesso do Home, usado igualmente no app Windows e Android.
- `GROQ_API_KEY`: **chave Groq NOVA**, nunca a anteriormente exposta em conversa.

Sem estes dois segredos, o endpoint de IA não responde às conversas.
O token de acesso **não** deve ser incorporado no repositório nem no APK.

### Mesma voz de Windows e Android — Kokoro Alex

O Windows já sintetiza localmente em `pm_alex`. Para o Android usar **a mesma voz**, o Worker expõe `POST /tts` e repassa a um serviço privado `backend/home-voice-server.py`, com o mesmo Kokoro ONNX e pacote de vozes do Windows.

Esse servidor **exige hospedagem HTTPS permanente, modelo Kokoro instalado e os secrets**
`HOME_TTS_INTERNAL_TOKEN` (mesmo segredo em Worker e servidor, pelo menos 32 caracteres),
`KOKORO_TTS_ORIGIN` (somente Worker: URL HTTPS do servidor) e
`HOME_KOKORO_MODEL_DIR` (somente servidor: diretório dos dois arquivos do modelo).

Exemplo de execução, **após configurar os secrets no host**, sem expor a porta diretamente na Internet:
```bash
python -m pip install -r backend/requirements-voice.txt
uvicorn backend.home-voice-server:app --host 127.0.0.1 --port 8765
```
O nome do arquivo contém hífen; para usar Python `-m uvicorn`, execute:
```bash
cd backend
uvicorn home_voice_server:app --host 127.0.0.1 --port 8765
```
Se a implementação ficar em `home-voice-server.py`, renomeie para `home_voice_server.py` ou carregue via `importlib`.
Configure um proxy HTTPS com autenticação e não exponha a porta 8765 diretamente.

Enquanto o servidor Kokoro não estiver hospedado e acessível, o Android informa
a indisponibilidade e usa temporariamente sua voz TTS local; **não se deve anunciar
que a voz Alex está funcional no mobile antes de testar o endpoint**.

A Groq oferece chat/geração de texto, mas não disponibiliza a voz personalizada
Kokoro `pm_alex` como TTS. Assim, as duas integrações são separadas para preservar
a identidade vocal.
