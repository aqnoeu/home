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
