---
name: desenhos-animados
description: Edita um vídeo (Reels/TikTok 9:16) de uma pessoa num lugar real com estética de desenho animado por cima do cenário - linhas coloridas tremidas (boil) com borda escura que se desenham contornando muro, prédios, árvores, pedras e a própria pessoa; parede de pedra/azulejo virando mosaico colorido estilo Gaudí que se espalha em onda; chão com pedras coloridas e rabiscos (estrelas, corações, espirais, zigue-zague); título de filme; palavras pipocando presas à parede; frase final grande. Pessoa sempre na frente. Funciona com câmera parada/na mão e com câmera acompanhando a pessoa andando. Use quando pedirem "desenhos animados", "linhas animadas", "contornar o muro/prédio/árvore", "parede em mosaico colorido", "pedras coloridas", "rabiscos no chão", "título de filme", "palavras pipocando na parede", "igual ao vídeo andando loucamente em Barcelona" ou "a arte de sair de casa", ou qualquer pedido de decorar o cenário real com desenhos coloridos animados.
---

# Desenhos animados

Desenhos coloridos animados por cima do cenário real, com a pessoa sempre na frente. Fica com cara de caderno de desenho que ganhou vida, mas tudo preso ao lugar: a tinta e as palavras andam junto com a parede quando a câmera mexe.

`<skill>` = a pasta desta skill. Requisitos: macOS (recorte da pessoa pelo Vision via `swift`, fonte Avenir Next Condensed do sistema), `ffmpeg`, `python3` com `numpy opencv-python pillow`. Para as etapas de IA (SAM, SegFormer) use um venv com `torch torchvision transformers scipy` — crie com `python3 -m venv .venv && .venv/bin/pip install torch torchvision transformers scipy opencv-python pillow` (um só, reaproveite entre vídeos).

## A estética (o que dá a identidade dos vídeos)

- **Paleta** (em `scripts/comum/desenho.py`): amarelo `#FFE26E`, rosa `#FF4FA3`, laranja `#FF7A2E`, ciano `#3ED3FF`, lima `#B8FF3C`, roxo `#9B6BFF`, branco. Toda linha e todo texto têm **borda escura** (`#141219`), sombra e um brilho leve — linha branca sozinha some no cenário, foi a primeira reclamação.
- **Linhas tremidas** (`tremer`): mudam a cada 3 quadros, como desenho animado feito à mão. Elas **se desenham** (`parcial`) e as de eco são **tracejadas andando** (`tracejar`).
- **Tinta com textura**: a cor entra multiplicada pela luz/textura do lugar (`compor_tinta_linhas`), então a pedra continua parecendo pedra pintada, não um adesivo chapado.
- **Título de filme**: 3 linhas — pequena / GRANDE / pequena — Avenir Next Condensed, branco com borda, letras se espaçando devagar, filetes amarelos que crescem dos lados da última linha. Aparece ~0,5s → 4,5s.
- **Palavras pipocando**: uma de cada vez, pop com rebote suave (sem exagero — rebote grande faz as palavras se encostarem), girinho de ±3–8°, cores alternadas. Em volta da pessoa, nunca em cima dela.
- **Frase final** grande, empilhada, entrando palavra por palavra (ex.: SAIA. / VIAJE. / CRIE.).
- **A pessoa sempre por cima** de tudo (compositing por último com a máscara do Vision).

## Primeiro: olhar o vídeo e escolher o caso

Extraia quadros e máscaras e faça uma folha de contato:

```bash
bash <skill>/scripts/comum/quadros_e_mascaras.sh <video> ~/dev/<projeto>
cd ~/dev/<projeto> && mkdir -p olhar && ffmpeg -v error -i base.mov -vf "fps=1,scale=360:-2,tile=6x3" -frames:v 1 olhar/folha.jpg
```

Se o vídeo não for 1080×1920, redimensione os quadros antes (os renders assumem 1080×1920 a 30 fps).

| O vídeo | Caso | Pasta |
|---|---|---|
| Câmera parada ou na mão, pessoa parada/encostada numa parede ou fachada | **parede** | `scripts/parede/` |
| Câmera acompanhando a pessoa andando, cenário passando de lado | **travelling** | `scripts/travelling/` |

Para saber se a câmera mexe: `cv2.phaseCorrelate` entre o quadro 1 e outros (parte de cima, sem a pessoa). Dezenas de px de deriva = câmera na mão → caso parede funciona (a homografia segura). Centenas de px andando de lado = travelling.

## Caso parede (câmera parada/na mão) — o mais robusto

Exemplo completo: `exemplos/parede.json` (vídeo "A arte de sair de casa").

1. **Rastrear o cenário** (homografia do quadro 1 para cada quadro, ignorando a pessoa):
   `python3 -I <skill>/scripts/parede/rastrear_homografia.py` → `homog.npy`. Fundo de pedra/tijolo dá milhares de pontos; se o mínimo cair abaixo de ~150, desconfie.
2. **Recortar as peças da parede** (pedras, azulejos, tijolos, placas) com SAM. O recorte por bordas (Canny/limiar) fica serrilhado e cheio de buraco — o SAM acerta o formato das pedras.
   ```bash
   <venv>/bin/python <skill>/scripts/parede/sam_quadro.py 1      # ~2 min na CPU
   <venv>/bin/python <skill>/scripts/parede/sam_quadro.py <último>  # se a pessoa se mexe e revela parede
   python3 -I <skill>/scripts/parede/pedras.py <y_limite> 1 <último>
   ```
   `y_limite` descarta peças abaixo da linha da parede (ex.: a calçada). Rode SAM também num quadro em que a pessoa está em outro lugar, senão fica um "buraco" com o formato dela quando ela sai. Confira `olhar/pedras.jpg`. (SAM no MPS falha com float64 → os scripts usam CPU; precisa `torchvision`.)
3. **Linha do encontro parede/chão**: `python3 -I <skill>/scripts/parede/costura.py <y_min> <y_max>` → põe `a` e `b` em `"costura"` no JSON.
4. **Escrever o JSON** do vídeo copiando `exemplos/parede.json`: título, palavras (posições em px do **quadro 1**, longe do corpo da pessoa), hora de cada uma, final, rabiscos do chão (longe dos pés). Distribua as palavras em duas colunas (x≈200 e x≈880) e acima da cabeça; palavras longas (CRIATIVIDADE) só cabem acima da cabeça.
5. **Prévia** de alguns quadros antes do render inteiro (cada quadro é independente, rode em paralelo):
   ```bash
   for f in 30 120 240 330 420; do python3 -I <skill>/scripts/parede/render_parede.py video.json $f $((f+1)) prev & done; wait
   ```
   Monte uma folha com `olhar/prev_*.jpg` e olhe: cores certas? palavras se tocando? texto atrás da cabeça?
6. **Render** e som original de volta:
   ```bash
   python3 -I <skill>/scripts/parede/render_parede.py video.json
   ffmpeg -i linhas_mudo.mp4 -i base.mov -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest <nome>_v1.mp4
   ```

O que o render faz: ~2/3 das peças ganham tinta numa onda que sai da pessoa (com um flash branco no pop); as outras ganham contorno colorido se desenhando; linha amarela + eco ciano tracejado no rodapé; contorno rosa colado na pessoa + eco amarelo tracejado mais largo (acompanha quando ela anda); rabiscos no chão; textos.

## Caso travelling (câmera acompanhando a pessoa andando)

Dois renders de referência — copie o mais parecido para o projeto e adapte textos, tempos e regiões:
- `scripts/travelling/render_travelling_parque.py` — **comece por este**, é o mais genérico e já usa `comum/desenho.py`. Vídeo "A arte de explorar" (parque com céu, cidade ao fundo, cerca viva, cordinha e chão de terra; cena andando pra esquerda). Tem: sol desenhado em volta do sol de verdade (área estourada do céu), prédios em rosa na borda com o céu + janelas amarelas, topo da vegetação em lima + eco laranja tracejado, cordinha da cerca pintada com listras coloridas presas ao mundo, árvore/palmeira que entra (contorno + hachura roxa), rabiscos densos e palavras curtas deitadas no chão (presos ao mundo via `desloc_linha.npy`, longe dos pés), contorno da pessoa, título + frase final no céu. Render de 9 s ≈ 2–3 min.
- `scripts/travelling/render_travelling_v4.py` — vídeo "Andando loucamente em Barcelona" (muro baixo de mosaico + prédios + árvores + chão de pedra; cena andando pra direita): topo do muro em amarelo, pedras do chão coloridas, muro pintado com palavras e estrelas, hachura nas árvores.

Antes de adaptar, olhe a segmentação (`argmax` de `probs.npy` pintado sobre alguns quadros): o grupo "muro" também pega cerca/cordinha; vegetação baixa (cerca viva) cai em "árvore".

1. `python3 -I <skill>/scripts/travelling/fluxo.py` → `fluxo_u.npy` (fluxo óptico horizontal).
2. `<venv>/bin/python <skill>/scripts/travelling/segformer.py` → `probs.npy` (muro, prédio, céu, árvore, chão). SegFormer ADE20K é **muito** melhor que separar por cor/fluxo.
3. `python3 -I <skill>/scripts/travelling/preparar.py` → `probs_limpo.npy`, `vel.npy`, `topo.npy` (topo do muro estabilizado no tempo).
4. `python3 -I <skill>/scripts/travelling/desloc.py` → `desloc_linha.npy` (quanto cada linha da tela andou; prende tinta e palavras ao chão/muro).
5. Adapte e rode o render; junte o áudio como no caso parede.

Lições desse caso:
- **Frase longa não vai no muro que passa**: com a cena andando para um lado, a frase aparece de trás pra frente e o meio passa atrás da pessoa. No muro, só palavras curtas soltas (BARCELONA, UAU!, GAUDÍ) + estrelas/corações; a frase vai no **céu**, palavra por palavra.
- **Pés**: a máscara do Vision erra no tênis (borrão de movimento). Não pinte nada colorido a menos de ~110 px da pessoa no chão nem em pixel escuro perto dela — senão aparecem "falhas no sapato". GrabCut não resolve.
- Árvores: contorno inteiro (laranja) + hachura diagonal colorida cobrindo, revelada de cima pra baixo.
- Prédios: contorno só na borda com o céu (rosa) + janelas em amarelo.
- Chão liso (terra, asfalto) não tem pedras pra pintar: use rabiscos densos (duas faixas de altura, a cada ~150 px de mundo) + palavras curtas achatadas (fy≈0.6) como se estivessem deitadas.
- Para o tamanho do `zigue`, o parâmetro é o número de dentes (~7), não o raio — 50+ dentes vira uma faixa enorme.
- Elemento que entra no meio do vídeo (palmeira): detecte por "colunas com vegetação no topo do quadro", não por formato de blob — ele se funde com a cerca viva e o blob deixa de parecer alto.

## Entregar

- Qualidade cheia: `<nome>_v1.mp4` (crf 16).
- **Versão pra postar / celular** (o envio pro celular aceita até 30 MB) — 2 passadas mirando ~24 MB:
  ```bash
  ffmpeg -y -i <nome>_v1.mp4 -c:v libx264 -preset slow -b:v 13M -pass 1 -an -f mp4 /dev/null
  ffmpeg -y -i <nome>_v1.mp4 -c:v libx264 -preset slow -b:v 13M -maxrate 18M -bufsize 26M -pass 2 -profile:v high -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart <nome>_postar.mp4
  rm -f ffmpeg2pass*
  ```
  (Ajuste `-b:v` pela duração: ~13M para 15 s, ~16M para 12 s, ~19M para 9 s.)
- Ao responder, explique em português simples o que entrou (tinta, linhas, textos com os tempos) e ofereça ajustes concretos (trocar palavras, menos cor na parede, mudar tempos). Se o som original for quase mudo, sugira pôr música no próprio Instagram.

## Armadilhas que já custaram uma rodada

- **Cores trocadas no texto**: tudo é BGR. Sprite de texto composto direto no quadro usa a cor em BGR (`sprite()` já faz isso). Usar `rgb()` ali faz o amarelo virar ciano.
- O título é gerado em RGB pelo PIL → `por_texto(bg, tt, bgr=False)`.
- Na prévia, olhe se a cabeça da pessoa cobre a frase final quando ela anda pra frente — suba as palavras se cobrir demais.
- Parede inteira colorida já é bem "alto"; `fracao_pintada` 0.6–0.7 e `opacidade` ~0.82 deixam a textura respirar.
