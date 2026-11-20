# Textos em lugares — skill para o Claude Code

Coloca a legenda do seu vídeo **dentro do cenário**, como se o texto estivesse pintado no lugar, com você passando na frente:

- texto deitado no **chão** e palavras gigantes num **painel atrás de você**
- frases que nascem nos seus pés e você **pisa** nelas
- texto **pintado na escada**, com a letra dobrando em cada degrau
- frase andando **em volta do seu corpo**
- **anéis de texto** girando no chão (câmera de cima)
- **chão inteiro coberto de TEXTO** com a chamada final
- texto na **parede**

E faz a montagem final: cortes presos à fala, 1.2x, cor e áudio tratado (sem estourar).

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
   cp -R skills-publicas/edicao-de-video/textos-em-lugares ~/.claude/skills/
   ```
   (ou **Code → Download ZIP**, descompacte e copie a pasta `edicao-de-video/textos-em-lugares` para `~/.claude/skills/`)
3. Abra o Claude Code numa pasta com seus vídeos e peça, por exemplo:
   > "Coloca o texto da minha fala pintado no chão, com eu pisando nas letras"

   > "Faz o texto circular em volta de mim nesse vídeo gravado de cima"

## Dicas de gravação

- Vertical (9:16), fale com pausas naturais.
- **Chão / pisar / parede:** celular no tripé.
- **Escada / círculo / chão cheio:** pode ser na mão, a skill rastreia a câmera.
- Deixe a superfície onde vai o texto bem à vista (chão, degraus, parede).
- Câmera de cima para o texto circular.

Feito com o Claude.
