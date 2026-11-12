# Cenário desenhado

Coloca você, sentada, dentro de um cenário de animação desenhado à mão que vai se transformando enquanto você fala: a cadeira vira sofá, o sofá vira banquinho, o banquinho vira o topo de um prédio (e a câmera se afasta para mostrar a altura), a parede tem quadros que se mexem, o céu tem nuvens andando, a cidade tem janelas piscando. As palavras entram animadas, letra por letra, no topo da tela. O vídeo pode começar e terminar no seu cenário real, com o desenho "invadindo" no meio.

Paleta verde, laranja, bege e rosinha. Tudo feito por código (Python + ffmpeg), sem app de edição e sem gerar imagem com IA.

## Como gravar

- Sentada (cadeira, banco, pernas cruzadas), no centro, câmera parada no tripé.
- Corpo inteiro do assento para cima, cabeça na metade de cima da tela (o topo fica para os textos).
- Fundo liso ajuda o recorte.

## Como usar com o Claude

Instale a skill na pasta de skills do Claude Code e peça, por exemplo:

> Edita esse vídeo com cenário desenhado: começa no cenário real, quando eu falo "transformar" a poltrona vira um sofá, no "alto do prédio" eu apareço sentada num prédio. [anexe o vídeo]

O Claude prepara o vídeo, escreve o roteiro de cenas presas às suas palavras, confere quadros e renderiza.

## Requisitos

macOS, `ffmpeg` e Python 3 com `pillow`, `numpy` e `faster-whisper`:

```bash
brew install ffmpeg
pip3 install pillow numpy faster-whisper
```

## Saídas

- `final.mp4` — vídeo pronto com voz e efeitos sonoros
- `final-camada-textos.mov` — só os textos, com fundo transparente, para ajustar no CapCut
- `final-sfx.wav` — só os efeitos sonoros
