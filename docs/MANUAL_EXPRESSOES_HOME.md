# HOME INTERSECT — Manual de Expressões v1.1

**Atualização:** 17/11/2026  
**Fonte de verdade:** `home_eyes.py`, `home_emotions.py`, `home_groq_client.py`, `home.py`.  
**Alcance:** renderizadores Windows (PySide6) e Android (Canvas nativo). As duas implementações devem manter os mesmos identificadores. A compilação e a validação visual em aparelhos ainda precisam ser confirmadas.

## Identidade visual

O Home usa **apenas dois olhos**. Não desenhar boca, nariz, cabeça, bochechas conectadas ou terceiro olho. A marca estática aprovada não deve ser substituída pelas animações. Usar as dimensões, posições, raios e o preto de recorte definidos em `home_eyes.py`. Partículas e linhas auxiliares podem surgir ao lado dos olhos, somente quando houver espaço.

## Emoções e estados já existentes

| Expressão/estado | Identificador | Desenho / acionamento |
|---|---|---|
| Neutro | `neutro` | Dois olhos verticais arredondados, branco-azulado; piscadas e olhar natural |
| Feliz (manual) | `mood=1` | Recorte inferior em cada olho, mantendo o par oficial |
| Raiva / Bravo | `raiva` | Laranja, olhos reduzidos e tampas diagonais, leve tremor |
| Sonolento | `sonolento` | Azul dessaturado; olhos semicerrados com cerca de 40% da altura normal; sem Z flutuante |
| Tédio | `tedio` | Cinza, 75% da altura e 77% da largura |
| Carregando | `carregando` | Verde, pulsação discreta de opacidade |
| Bateria baixa | `bateria_baixa` | Âmbar, altura reduzida |
| Economia | `economia` | Azul discreto, altura reduzida |
| Ouvindo | `voice_state=listening` | Ajusta a abertura vertical a 1,08 |
| Pensando (voz) | `voice_state=thinking` | Ajusta a abertura vertical a 0,72 |
| Falando | `voice_state=speaking` | Ajusta abertura a 0,96, sem pulsações de fala |

O **sonolento** utiliza apenas os olhos semicerrados. As antigas marcas laterais azuis e o Z flutuante foram removidos por divergirem da expressão aprovada.

## Novas expressões implementadas

| Expressão | Identificador | Geometria / comportamento |
|---|---|---|
| Piscadela | `piscadela` | Olho esquerdo se estreita a 12% da altura; direito permanece aberto |
| Lovabow | `lovabow` | Dois olhos substituídos por corações vetoriais, branco evoluindo até rosa |
| Pensando (emoção) | `pensando` | Olhos discretamente reduzidos e olhar deslocado |
| Surpreso | `surpreso` | Olhos mais altos e largos, sem boca |
| Desconfiado | `desconfiado` | Assimetria; olho esquerdo parcialmente fechado |
| Tímido | `timido` | Olhos rosados discretos; dois pares de risquinhos inferiores laterais |
| Confuso | `confuso` | Assimetria de abertura entre os olhos |
| Travesso | `travesso` | Olho esquerdo mais estreito; gesto assimétrico |

**Interações:** o botão `⋯` do painel Windows percorre as oito expressões, mostrando cada uma por 12 segundos. O mecanismo de conversa pode selecioná-las pelo JSON de emoção retornado pela Groq, durante o período de retenção de 15 segundos. Depois, volta o contexto automático. Os estados de bateria e carregamento continuam calculados normalmente.

### Movimento e limitações

- Piscadas aleatórias e reação a clique permanecem em funcionamento.
- Olhar acompanha o mouse somente quando autorizado.
- Os elementos auxiliares são omitidos em alturas muito pequenas.
- Preservar contraste e legibilidade no notch recolhido de 22 px.
- Não confundir **`pensando` como emoção** com o estado operacional de voz `thinking`.
- Não copiar automaticamente desenhos integrais do DeskBuddy ou de outras bibliotecas que tenham boca.
- A revisão 1.1 corresponde ao **desenho derivado do código**, e não a capturas reais da interface em execução.
- O aplicativo Android ainda precisa de uma adaptação equivalente e testes no aparelho.

## Referências

- Código-base: https://github.com/aqnoeu/home
- Conceito inicial de olhos: https://github.com/FluxGarage/RoboEyes
- Pesquisa comparativa: https://github.com/Purujith-Kadekar/DeskBuddy
- Manual visual de referência elaborado anteriormente: `Manual_de_Expressoes_Home_Intersect_v1.pdf` (artefato de projeto externo ao repositório, sem confundir com capturas reais).

## Verificação para próximas alterações

Executar `python -m unittest discover -s tests` e validar a interface Windows com zoom de 100% e 125%, notch recolhido e expandido, os oito estados do seletor, prioridade bateria/conversa, voz, piscadas, transições e ausência de boca.


## Seletor de expressões no Android — atualização de 17/11/2026

- A tela inicial (**Hub**) e **Configurações → Aparência** reutilizam o mesmo seletor em `MainActivity.addExpressionPicker()`.
- A prévia utiliza o `EyesView` real do aplicativo (não um desenho externo). O modo `setExpressionPreview(true)` força a expressão selecionada apenas nessa prévia, mesmo com bateria carregando, escuta ativa ou indicador de download.
- Grade fixa de **duas linhas por três colunas**, seis botões por página, **duas páginas** e navegação por setas; sem lista horizontal.
- As 12 opções disponíveis são: Normal, Feliz, Sonolento, Bravo, Piscadela, Lovabow, Pensando, Surpreso, Desconfiado, Tímido, Confuso e Travesso.
- O índice salvo `home/mood` preserva os quatro primeiros valores anteriores (0–3) e adiciona as oito expressões seguintes (4–11). A seleção é encaminhada ao notch pelo fluxo existente.
- `HomeEmotion.normalize()` reconhece as emoções novas e `HomeGroq` pode retorná-las em seu JSON.
- A seleção no painel é uma escolha manual, mas estados operacionais prioritários (bateria/carregamento, voz e atualizações) ainda podem substituir temporariamente a aparência no notch real.
- O visual continua estritamente **sem boca**, com detalhes gráficos opcionais laterais/abaixo dos olhos.
- Verificar em aparelho físico: navegação de páginas, seleção persistente, retorno à tela, notch real, atualizações e voz, além de fontes e telas estreitas.


## Galeria de teste do Windows — atualização de 17/11/2026

- `home_expression_gallery.py` implementa a página **Expressões**, acessível pelo botão **⋯** do Hub ou pela navegação interna.
- A galeria mostra uma prévia renderizada pelo `EyesWidget` original, seguida de botões em **duas linhas e três colunas**, com navegação **1/2** e **2/2**.
- Os 12 nomes são os mesmos do Android, incluindo o Sonolento aprimorado e Lovabow.
- Ao clicar, atualiza a prévia e apresenta a expressão no notch por 12 segundos, sem desabilitar o motor contextual de energia/voz.
- A página utiliza os recursos vetoriais existentes e não altera o símbolo oficial da marca.
- Validação automatizada de navegação Windows incluída no workflow de release conjunta; a verificação visual e a compilação precisam ser observadas no GitHub Actions e no dispositivo.

## Correção do gerenciador — 19/11/2026 (branch de homologação)

- **Android:** a seleção na grade fixa a expressão no notch real, inclusive após a reconstrução do overlay e reinício; existe ação explícita de retorno ao modo automático. O toque prolongado na grade e o botão X nas configurações ocultam expressões nativas de forma reversível. Os interruptores restauram as expressões ocultas, com pelo menos uma opção mantida ativa.
- **Windows:** a galeria seleciona a expressão persistente no notch real, permite ocultar/restaurar opções e reativar o modo automático. Configurações persistidas em `~/.home_notch.json`.
- **Sono:** ambos os renderizadores preservam olhos reduzidos e não desenham Z flutuante nem tracinhos azuis.
- **Nota sobre prioridades:** seleção fixa prevalece sobre sugestões contextuais. O modo automático preserva o comportamento contextual, incluindo reações de bateria e conversa. Estados imediatos de microfone e atualização continuam podendo sinalizar sua operação no Android.
- **Publicação:** mudanças isoladas em branch e PR em rascunho; compilar e validar antes de obter autorização para lançar uma nova versão.
