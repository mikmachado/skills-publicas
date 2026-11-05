# Posts em 3D

Skill do Claude Code que coloca posts de Instagram (com fotos e vídeos tocando dentro) e telas de player de música flutuando em 3D atrás de você no vídeo. Cada card entra girando, assenta com rebote, balança de leve, faz sombra e recebe luzes coloridas, com som de whoosh e pop.

Substitui o caminho Canva → Alight Motion (3D Flip) → CapCut por um comando só.

## Como usar

Peça ao Claude algo como:

> Coloca posts flutuando atrás de mim nesse vídeo, com trechos dos meus reels e uma tela de música tocando.

Ele recorta você, monta a composição, mostra quadros para você aprovar e renderiza. Você recebe:

- `posts-3d.mp4`: o vídeo pronto;
- `posts-3d-camada-posts.mov`: só os posts, com fundo transparente, para ajustar no CapCut;
- `posts-3d-sfx.wav`: os efeitos sonoros separados.

## Requisitos

macOS, `ffmpeg` e Python 3 com `pillow` e `numpy`.

## Dicas de gravação

Tripé, parede livre em volta de você e um gesto (abrir os braços, apontar) na hora em que os posts devem aparecer. Para o fundo de estúdio branco com reflexo no chão, grave em pé, de corpo inteiro.
