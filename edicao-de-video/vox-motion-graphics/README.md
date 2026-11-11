# Vox Motion Graphics

Skill do Claude Code que produz um vídeo explicativo narrado do começo ao fim, no estilo motion graphics de canais como a Vox, usando o MCP do [Higgsfield](https://higgsfield.ai). Ela pesquisa o tema (ou acha um assunto em alta sozinha), checa os fatos, escreve o roteiro, gera os clipes animados, grava a narração e entrega um MP4 montado, com legenda.

Tem dois estilos:

- **Colagem Mixed Media** (padrão): recortes de fotos antigas com borda de papel sobre fundos de cor chapada, meio-tom, círculos e setas desenhados à mão, gráficos que crescem. Bom para histórias com dados, "por que X" e vídeos curtos.
- **Diorama de papel documental**: mundos em papel de jornal sépia, figuras recortadas com tarja preta nos olhos, um único laranja queimado de destaque, letras tipográficas nos objetos e câmera FPV contínua. Bom para geopolítica, dinheiro e poder, ou quando você quer algo mais cinematográfico.

## Como usar

Peça ao Claude algo como:

> Faz um vídeo estilo Vox sobre por que o café ficou tão caro.

Ou, sem tema:

> Roda o pipeline vox com algum assunto em alta.

Antes da primeira geração paga, o Claude manda um plano curto (tema, ângulo, número de blocos, voz e créditos estimados) e segue sem esperar, a não ser que você peça para aprovar antes. No fim você recebe o vídeo, o roteiro completo e a lista de fontes.

Padrões: vertical 9:16, 1 minuto (6 blocos de 10 s), narração em inglês com voz de documentário e legenda burned-in. Dá para pedir 16:9, outra duração (1 a 10 min), outro idioma ou escolher a voz.

## Requisitos

- Conta no Higgsfield com créditos e o MCP do Higgsfield conectado ao Claude Code. Cada minuto gasta algumas centenas de créditos (o plano mostra a estimativa antes).
- Busca na web habilitada no Claude Code, para a pesquisa e a checagem dos fatos.

O estilo diorama traz IDs de imagens de referência (style key e objetos) gerados na minha conta. Se não abrirem na sua, o Claude gera novos com o prompt que está em `references/diorama-doc.md`.
