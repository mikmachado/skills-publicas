# Texto seguindo gestos — skill para o Claude Code

Você fala para a câmera e, a cada frase, **desenha uma forma no ar com as mãos**. A frase fica presa nessa forma, parada no lugar: aparece por onde a mão passa, a forma se fecha, fica um pouco em cena e sai. Depois entra a próxima.

- **arco**: as duas mãos sobem juntas pelo meio e abrem para os lados
- **quadrado**: uma mão sobe por um lado, cruza por cima e desce pelo outro (um pedaço da frase em cada lado)
- **círculo**: as duas mãos saem de baixo pelos lados e dão a volta
- **linha**: a mão varre na horizontal (o texto sempre lê da esquerda pra direita)
- **zigue-zague** e **ondas**: uma palavra por traço, ou a frase fazendo a onda
- **oval de fechamento**: arco por cima da cabeça + a mão descendo pelo lado

O Claude rastreia as duas mãos (Vision da Apple), detecta os gestos, sugere a forma e a frase de cada um, mostra uma prévia para você conferir e entrega o vídeo com texto branco grosso e sombra forte. Vídeo **HDR do iPhone continua HDR** (não fica apagado) e o arquivo final cabe no limite de envio do celular.

## Como instalar

1. Tenha o [Claude Code](https://claude.com/claude-code) num **Mac** com `ffmpeg` e Python 3:
   ```bash
   brew install ffmpeg
   pip3 install numpy opencv-python pillow faster-whisper
   ```
2. Baixe o repositório [skills-publicas](https://github.com/mikmachado/skills-publicas) e copie esta pasta para as skills do Claude:
   ```bash
   git clone https://github.com/mikmachado/skills-publicas.git
   mkdir -p ~/.claude/skills
   cp -R skills-publicas/edicao-de-video/texto-seguindo-gestos ~/.claude/skills/
   ```
   (ou **Code → Download ZIP**, descompacte e copie a pasta `edicao-de-video/texto-seguindo-gestos` para `~/.claude/skills/`)
3. Abra o Claude Code numa pasta de trabalho e peça, por exemplo:
   > "Usa a skill texto-seguindo-gestos neste vídeo. Eu faço um arco, depois um quadrado, depois um círculo e termino com uma linha."

   > "Esse vídeo não tem fala. Faz o texto seguindo meus gestos com estas frases: ..."

## Dicas de gravação

- Vertical (9:16), **câmera parada**, você inteiro ou da cintura pra cima, com espaço para os braços abrirem.
- **Uma forma por frase**, gestos grandes e claros, do tamanho do corpo.
- **Volte as mãos para baixo entre um gesto e outro** — é assim que a skill separa um do outro.
- Linha de preferência da esquerda para a direita de quem assiste (se fizer ao contrário, a skill espelha só aquele trecho).
- Não cubra o rosto com a mão no meio do gesto.
- Diga ao Claude a ordem das formas que você fez — ajuda a conferir o que ele detectou.

Feito com o Claude.
