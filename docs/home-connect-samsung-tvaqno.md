# Home Connect — Samsung TVAQNO

## Escopo autorizado
Somente TV Samsung `TVAQNO`, cômodo `Quarto Aqno`, cadastrada no SmartThings. Não cadastrar ou controlar outros dispositivos. O usuário confirmou celular e TV na mesma rede Wi-Fi.

## Fluxo de conexão (pendente de implementação)
1. Home Connect > Casa Inteligente > Samsung SmartThings > Conectar.
2. Iniciar OAuth 2.0 por página oficial Samsung; nunca coletar senha Samsung no Home.
3. Backend HTTPS recebe callback e troca código por tokens; armazenar tokens de forma segura, sem gravá-los no repositório ou logs. Implementar renovação e revogação.
4. Consultar `/v1/devices`, localizar TVAQNO, solicitar seleção/confirmar deviceId. Limitar ações ao deviceId selecionado.
5. Consultar descrição/capabilities e status antes de oferecer controles; não presumir que atalhos visíveis no app SmartThings existem na API pública.
6. Enviar comandos somente para capacidades suportadas via `POST /v1/devices/{deviceId}/commands` e apresentar resultado/erros reais.
7. Validar power on/off, volume, mute, canais, apps Netflix/YouTube/Prime Video e navegação. Se API não expuser app launch, estudar canal local Samsung com pareamento e consentimento.

## Dependências
- Registrar API Access App no SmartThings Developer Center (pode exigir plano Developer/Business pago).
- Configurar redirect HTTPS e client credentials no backend (não no APK).
- Autorizar acesso à conta Samsung pelo próprio titular.
- Testar TV ligada e em standby, em Wi-Fi e opcionalmente em rede móvel.

## Segurança
Permissões mínimas `r:devices:*` e `x:devices:*`, restritas na autorização ao dispositivo escolhido quando suportado. Confirmar ações de risco. Nunca embutir token pessoal, senha ou segredo no código-fonte.

## Estado
Especificação registrada; **integração OAuth, interface e controle ainda não implementados nem testados**. Não publicar como funcionalidade pronta.

Referências: https://developer.smartthings.com/docs/service-integrations/architecture-and-auth-flow e https://developer.smartthings.com/docs/service-integrations/control-devices
