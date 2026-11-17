# HOME INTERSECT — Manual de Expressões v1.1

**Atualização:** 17/11/2026  
**Fonte de verdade:** `home_eyes.py`, `home_emotions.py`, `home_groq_client.py`, `home.py`.  
**Alcance:** renderizador Windows em PySide6. Android exige implementação/teste próprio.

## Identidade visual

O Home usa **apenas dois olhos**. Não desenhar boca, nariz, cabeça, bochechas conectadas ou terceiro olho. A marca estática aprovada não deve ser substituída pelas animações. Usar as dimensões, posições, raios e o preto de recorte definidos em `home_eyes.py`. Partículas e linhas auxiliares podem surgir ao lado dos olhos, somente quando houver espaço.

## Emoções e estados já existentes

| Expressão/estado | Identificador | Desenho / acionamento |
|---|---|---|
| Neutro | `neutro` | Dois olhos verticais arredondados, branco-azulado; piscadas e olhar natural |
| Feliz (manual) | `mood=1` | Recorte inferior em cada olho, mantendo o par oficial |
| Raiva / Bravo | `raiva` | Laranja, olhos reduzidos e tampas diagonais, leve tremor |
| Sonolento | `sonolento` | Azul dessaturado; 40% da altura normal; pequeno `z` onde couber |
| Tédio | `tedio` | Cinza, 75% da altura e 77% da largura |
| Carregando | `carregando` | Verde, pulsação discreta de opacidade |
| Bateria baixa | `bateria_baixa` | Âmbar, altura reduzida |
| Economia | `economia` | Azul discreto, altura reduzida |
| Ouvindo | `voice_state=listening` | Ajusta a abertura vertical a 1,08 |
| Pensando (voz) | `voice_state=thinking` | Ajusta a abertura vertical a 0,72 |
| Falando | `voice_state=speaking` | Ajusta abertura a 0,96, sem pulsações de fala |

O **sonolento foi aprimorado** com risquinhos laterais discretos abaixo dos olhos em alturas de interface suficientes (a partir de 28 px). Não desenhar linhas unidas nem elementos na posição de uma boca.

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
