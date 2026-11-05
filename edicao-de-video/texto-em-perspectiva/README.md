# Texto na parede em perspectiva

Você grava um vídeo falando na frente de uma parede, e a legenda aparece **pintada na parede, em perspectiva**, com você passando na frente das letras. Na mesma parede entram imagens, prints de apps e até um feed de posts rolando, com vídeos tocando.

O efeito costuma levar três apps (CapCut, Alight Motion e Canva) e uma inserção por vez. Com esta skill, o Claude faz tudo a partir do seu vídeo: transcreve, mede a parede, desenha a legenda inteira com fontes misturadas, cola em perspectiva, corta as pausas, alterna zooms, ajusta a cor e coloca música e efeitos.

Mostrei o resultado no Instagram [@mik_machado](https://www.instagram.com/mik_machado/). **Guia completo com imagens, prompts prontos e erros comuns: [guia/](guia/README.md).**

## O que você precisa

- **macOS** (o recorte da pessoa usa o Vision da Apple)
- [Claude Code](https://claude.com/claude-code)
- **ffmpeg**: `brew install ffmpeg`
- **Python 3** com as bibliotecas: `pip3 install pillow numpy faster-whisper`

Se faltar algo, peça ao Claude: "instala o que a skill texto-em-perspectiva precisa".

## Como gravar

- Celular **no tripé, sem mexer**.
- Uma **parede clara e lisa, de lado** (em perspectiva), ocupando boa parte do quadro.
- Fique **longe da parede**; o texto vai no lado perto da câmera.
- Comece com **1 a 2 segundos de parede vazia**.
- Deixe aparecer o **rodapé, o teto ou uma quina**: eles mostram para onde a parede "foge".
- Vertical (9:16) e com pausas naturais na fala.

## Como pedir

Depois de instalar a skill (veja o [README principal](../../README.md)), abra o Claude Code na pasta do seu vídeo e peça, por exemplo:

> Use a skill texto-em-perspectiva no vídeo `meu-video.MOV`. Coloque toda a legenda do que eu falo na parede da esquerda, em perspectiva, palavra por palavra, misturando fontes e tamanhos. Eu tenho que passar na frente do texto. Quando eu falar de imagens e vídeos, mostre meus posts da pasta `posts/` subindo na parede como um feed. Deixe o vídeo dinâmico com cortes nas pausas. Me mostre uma imagem de cada etapa antes de seguir.

O Claude vai te mostrar a transcrição (corrija nomes próprios), a parede marcada sobre o vídeo, algumas telas da legenda e, no fim, uma folha de quadros do vídeo pronto.

## O que você recebe

| Arquivo | O que é |
| --- | --- |
| `final.mp4` | O vídeo pronto, com cortes, cor e som |
| `final-camada-cortada.mov` | Só a parede, com transparência e os mesmos cortes, para ajustar no CapCut |
| `trilha-camada.wav` e `sfx-camada.wav` | Música e efeitos separados |

## O que tem nesta pasta

| Arquivo | Para quê |
| --- | --- |
| `SKILL.md` | As instruções que o Claude segue |
| `scripts/transcrever.py` | Transcreve a fala com o tempo de cada palavra |
| `scripts/grade.py` | Desenha uma grade sobre o vídeo para achar os cantos da parede |
| `scripts/parede.py` | Desenha a parede animada (legenda, feed, prints) a partir do `projeto.json` |
| `scripts/seg.swift` | Recorta a pessoa quadro a quadro |
| `scripts/perspectiva.py` | Cola a parede em perspectiva com a pessoa na frente |
| `scripts/cortes.py` | Cortes, zooms, cor, música e efeitos |
| `scripts/cartao.py` | Gera um cartão de texto avulso (estilo do tutorial clássico) |
| `exemplos/projeto.json` | Exemplo de configuração da parede e das telas |
| `guia/` | Guia passo a passo com imagens do processo |
