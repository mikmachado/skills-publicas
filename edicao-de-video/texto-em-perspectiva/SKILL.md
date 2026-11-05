---
name: texto-em-perspectiva
description: Cola textos, imagens e vídeos em perspectiva numa parede real do vídeo, com a pessoa recortada passando na frente — a legenda inteira palavra por palavra com fontes misturadas, feed de posts rolando, prints de apps — e depois faz cortes, zooms, cor e som. Use quando pedirem texto "na parede", "em perspectiva", "colado no cenário", "atrás de mim", efeito Flip Layer do Alight Motion, Transform Image do Canva, ou legenda que parece parte do ambiente num Reels.
---

# Texto na parede em perspectiva

O efeito, feito tradicionalmente em 3 apps (CapCut → Alight Motion "Flip Layer" → CapCut com chroma key, modo Escurecer e recorte da pessoa), aqui sai inteiro pelo terminal. A ideia são 4 camadas:

1. o vídeo original, câmera parada;
2. a **parede plana**: um quadro branco com legenda, posts e prints animados no tempo da fala;
3. a **perspectiva**: esse quadro entortado até os 4 cantos da parede, no modo *multiplicar* (o branco some, a tinta pega a luz e a sombra da parede);
4. a **pessoa recortada** por cima.

Requisitos: macOS (o recorte usa o Vision da Apple via `swift`), `ffmpeg`, Python 3 com `pillow numpy faster-whisper`. Scripts em `scripts/`; rode com `python3 -I`. Exemplo de configuração em `exemplos/projeto.json`.

## Antes de começar

- **Pergunte só o que faltar**: o vídeo, qual parede, e o que entra além da legenda (posts? prints?). O resto tem padrão.
- Mostre uma imagem à pessoa a cada etapa (grade com os cantos, telas da parede plana, folha de quadros). É olhando que se acerta.

## Como filmar (se o vídeo ainda não existe)

- Celular **no tripé, sem mexer** (os cantos são fixos; câmera andando = texto escorregando).
- Parede **clara e lisa, de lado** (em perspectiva), ocupando boa parte do quadro.
- Pessoa **longe da parede**, de preferência na frente da parte distante; o texto fica no lado perto da câmera.
- **1–2 s de parede vazia** no começo; **quina, rodapé ou teto visíveis** (dão o ponto de fuga).
- 9:16, pausas naturais na fala (viram os cortes).

## Passo a passo

Trabalhe numa pasta do projeto. Todas as coordenadas são do `base.mp4` (1080×1920).

### 1. Base
```bash
ffmpeg -i bruto.MOV -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" -r 30 -c:v libx264 -crf 16 -c:a aac base.mp4
```

### 2. Transcrição com tempo por palavra
```bash
python3 -I scripts/transcrever.py base.mp4        # → transcricao.json
```
Mostre a transcrição e **corrija nomes próprios** no campo `"w"` de cada palavra, sem mudar a quantidade de palavras (ex.: "cloud" → "Claude", "a Light Motion" → "o Alight Motion"). Palavra estranha: recorte aquele trecho com ffmpeg e transcreva de novo.

### 3. Geometria da parede
```bash
python3 -I scripts/grade.py base.mp4 --t 0.5 -o grade.jpg
```
Abra a grade e ache o **ponto de fuga** (`vp`) da parede: cruze duas linhas paralelas dela (rodapé e teto, ou rodapé e o topo de um móvel encostado). Com a câmera nivelada, um ponto da parede lateral em (Z profundidade, Y altura) vai para `x = vpx ∓ focal/Z`, `y = vpy + focal·Y/Z`. Focal de um iPhone na lente 1x, vídeo vertical 1920: ~1550.

No `projeto.json`, em `"parede"`: `lado` (esquerda/direita), `vp`, `focal`, e o retângulo útil `z: [perto, longe]`, `y: [alto, baixo]`. Escolha a faixa **perto da câmera e fora de onde a pessoa fica** (o lado longe fica pequeno e atrás dela). Confira:
```bash
python3 -I scripts/grade.py base.mp4 --t 0.5 --cantos "$(python3 -I scripts/parede.py projeto.json --cantos)" -o conferir.jpg
```
O quadrilátero tem que "deitar" na parede: bordas verticais retas, de cima e de baixo apontando para o mesmo ponto de fuga do rodapé. Itere até ficar certo — é o que mais pesa no resultado.

### 4. Recorte da pessoa
```bash
mkdir -p quadros mask && ffmpeg -i base.mp4 -q:v 2 quadros/%05d.jpg
swift scripts/seg.swift quadros mask
```
Audite sobre magenta com 1 quadro a cada ~2 s do vídeo todo (nunca um quadro só). Só importa o recorte **dentro do quadrilátero** — erros em estante ou fundo não aparecem.

### 5. A parede plana (`projeto.json` → `"telas"`)
Cada tela consome palavras da transcrição, **na ordem**; a soma tem que bater com o total (o script avisa).
- **Legenda**: `{"linhas": [[["texto exibido", "estilo", nº de palavras do áudio], …], …]}` — uma frase por tela, alinhada à esquerda, palavra a palavra com pop.
- Estilos: `l`/`L` texto corrido · `h`/`H` palavra-chave condensada pesada (caixa alta) · `s`/`S` itálico serifado (palavra emotiva) · `m`/`M` letra de mão (fechos). Cor após dois-pontos: `H:t` terracota, `:p` petróleo, `:m` mostarda (troque em `"cores"`).
- **Feed** (quando a pessoa fala de imagens/vídeos): `{"feed": {"palavras": N, "posts": [jpg/mp4…], "perfil", "avatar", "rotulos": [...]}}` — posts sobem como no celular, vídeos tocando.
- **Prints** (quando cita apps/sites): `{"prints": {"palavras": N, "titulo": [...], "itens": [{"nome", "imagem", "palavra": índice dentro do bloco}]}}`.
- `{"pular": N}` pula palavras sem mostrar nada.

Mostre 4 telas antes de renderizar:
```bash
python3 -I scripts/parede.py projeto.json --ver 9.7 15.9 21.5 45.5    # → parede_*.jpg
python3 -I scripts/parede.py projeto.json                            # → parede.mp4 + cantos
```

### 6. Colar em perspectiva
```bash
python3 -I scripts/perspectiva.py --base base.mp4 --camada parede.mp4 \
  --cantos "$(python3 -I scripts/parede.py projeto.json --cantos)" \
  --mistura multiplicar --mascara mask --saida comp.mp4 --camada-saida camada.mov
```

### 7. Cortes, cor e som
```bash
python3 -I scripts/cortes.py projeto.json comp.mp4 final.mp4 --camada camada.mov \
  [--musica trilha.mp3 --musica-ini 30] [--sem-cor]
```
Um corte por frase sem as pausas, frases longas cortadas no meio, planos alternados (aberto / aproximado / close no `"rosto"` nas frases curtas, com a borda da parede presa para o texto não sair do quadro). Cor: pretos firmes, saturação 1,4, branco neutro. Som: música abaixando sob a voz, "pop" nas palavras `H`/`M`, whoosh e rolagem no feed, papel nos prints. **Sempre corte depois de colar a parede.**

### 8. Revisar e entregar
```bash
ffmpeg -i final.mp4 -vf "fps=1/1.6,scale=216:-1,tile=9x3" -frames:v 1 folha.jpg
```
Confira: o texto segue as linhas da parede? A pessoa fica inteira na frente? Alguma palavra cortada nos closes? Entregue `final.mp4`, `final-camada-cortada.mov` (parede com alpha, mesmos cortes), `trilha-camada.wav` e `sfx-camada.wav` para ajustes no CapCut.

## Peças avulsas

Para um cartão só (sem legenda inteira): `cartao.py` gera o texto estilo tutorial (amarelo com contorno) e `perspectiva.py` cola com animações `porta` (Flip Layer), `desdobra`, `surge` ou `nenhuma`, a partir de `--cantos` lidos na grade. Funciona também no chão ou numa mesa: só os cantos mudam.

## Erros comuns

| Sintoma | Causa | Correção |
|---|---|---|
| Texto escorrega | câmera mexeu, ou zoom antes de colar | tripé; colar antes de cortar |
| Texto flutua | cantos/ponto de fuga errados | refazer a conferência com a grade |
| Letras esticadas | retângulo fora da proporção real | usar a geometria por ponto de fuga (parede.py) |
| Texto sobre a mão | recorte falhou | auditar sobre magenta; corrigir com a parede vazia do começo |
| Palavra cortada | close cortou o lado perto | ajustar `"rosto"` ou usar letra menor |
| Nome errado | transcrição | corrigir `transcricao.json` antes do passo 5 |
