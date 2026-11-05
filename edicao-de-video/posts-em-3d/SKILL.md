---
name: posts-em-3d
description: Coloca posts de Instagram (fotos e vídeos tocando dentro da moldura) e telas de player de música flutuando em 3D atrás da pessoa, entrando com giro e rebote, com sombra, luzes coloridas e efeito sonoro. Pode manter o cenário original ou trocar por um estúdio branco infinito com reflexo no chão. Use quando pedirem "posts flutuando", "posts atrás de mim", "mural de posts", "portfólio em volta", "telas do Spotify/música no vídeo", efeito 3D Flip do Alight Motion com posts do Canva, ou o efeito de mostrar trabalhos em quadradinhos ao redor da pessoa num Reels.
---

# Posts em 3D flutuando atrás da pessoa

O tutorial original usa 3 apps: Canva (vídeo dentro da moldura de post, fundo verde) → Alight Motion (3D Flip para virar o post, chroma key, um export por post) → CapCut (fundo branco, remover plano de fundo, posts atrás da pessoa, keyframe de entrada, "balanço de rebote", vídeo desacelerado, reflexo duplicando e girando a pessoa, iluminação arco-íris, efeitos sonoros).

Aqui sai num comando só (`scripts/mural.py`): cada post é um plano 3D de verdade, projetado em perspectiva, então dá pra girar em qualquer eixo sem exportar nada. Camadas, de trás pra frente:

1. fundo: o vídeo original **ou** um estúdio branco infinito (parede, curva e chão), ou uma imagem;
2. sombras macias dos posts;
3. posts e players (giram ao entrar, assentam com mola e ficam balançando de leve);
4. luzes coloridas passeando (tingem sem escurecer);
5. a pessoa recortada (no estúdio: com reflexo no chão e sombra nos pés);
6. posts marcados `"frente": true`, que passam na frente dela.

Requisitos: macOS (recorte com o Vision via `swift`), `ffmpeg`, Python 3 com `pillow numpy`. Rode os scripts com `python3 -I`. Exemplo completo em `exemplos/projeto.json`.

## Antes de começar

Pergunte só o que faltar: o vídeo, o que vai dentro dos posts (fotos, vídeos, trechos de reels: arquivo + segundo inicial), se quer telas de música (música, artista, capa) e se o fundo fica o original ou vira estúdio branco. Padrões: fundo original, 6–9 cards, entradas quando a pessoa se mexe.

## Como filmar (se ainda não gravou)

- Tripé, câmera parada. Pessoa com espaço de parede livre em volta (ou corpo inteiro, se for para o estúdio branco).
- Entrar em cena e fazer um gesto (abrir os braços, apontar) onde os posts devem "sair". Pouco movimento depois: o recorte fica melhor.
- Para o estúdio com reflexo: pés visíveis no quadro.

## Passo a passo

Numa pasta do projeto:

### 1. Base (9:16, 30 fps, até a duração pedida)
```bash
ffmpeg -i bruto.MOV -t 20 -map 0:v:0 -map 0:a:0 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30" -c:v libx264 -crf 16 -pix_fmt yuv420p -c:a aac base.mp4
```

### 2. Recorte da pessoa
```bash
mkdir -p quadros mask && ffmpeg -i base.mp4 -q:v 2 quadros/%05d.jpg
swift scripts/seg.swift quadros mask
```
O Vision recorta pessoas, não objetos: cadeira, mesa ou violão ficariam **atrás** dos posts, e os posts passam entre a pessoa e o móvel (parece que ela sentou no card). Se a pessoa está sentada ou apoiada em algo, inclua o móvel na máscara:
```bash
swift scripts/seg_objetos.swift            # (usado pelo script abaixo)
python3 -I scripts/mascara_objetos.py quadros mask mask_tudo --zona x0,y0,x1,y1
```
Ele apaga a pessoa (pinta da cor do fundo), recorta o objeto em destaque com o Vision, fica só com o que encosta nela e junta com a máscara da pessoa. `--zona` limita o objeto à área do móvel: sem ela entram estante, prateleira e cabos que tocam a pessoa. Audite sobre magenta (1 quadro a cada ~1,5 s) e use `"mascara": "mask_tudo"` no projeto.

### 3. Achar os lugares
Faça uma grade de alguns quadros e veja onde está a parede livre e onde fica a cabeça:
```bash
ffmpeg -i base.mp4 -vf "select='eq(n\,60)+eq(n\,300)+eq(n\,540)',scale=432:-1,drawgrid=w=43.2:h=76.8:c=red@0.5,tile=3x1" -frames:v 1 -fps_mode vfr grade.jpg
```
Cada célula = 108×192 px do base. Para sugerir tempos de entrada pelos gestos:
```bash
python3 -I scripts/mural.py projeto.json --gestos
```

### 4. `projeto.json`
```json
{
  "base": "base.mp4", "mascara": "mask", "saida": "posts-3d.mp4",
  "fundo": "original",
  "luzes": {"intensidade": 0.28},
  "posts": [
    {"midia": "reel.mp4", "de": 12.0, "entra": 2.6, "x": 230, "y": 330, "largura": 360, "rot": [4, 24, -5]},
    {"tipo": "player", "midia": "capa.jpg", "musica": "Nome", "artista": "Artista", "duracao": 231, "pos": 48,
     "entra": 3.4, "x": 845, "y": 330, "largura": 330, "rot": [4, -22, 4]}
  ]
}
```
- **Post**: `midia` (jpg/png/mp4/mov), `de` (segundo inicial do vídeo), `velocidade` (0.7 = mais lento, como no tutorial), `foco` [x, y] do recorte 4:5.
- **Player de música** (`"tipo": "player"`): tela "tocando agora" escura com capa, música, artista, barra que anda (`pos` = segundo inicial, `duracao` total) e controles. Visual genérico, **sem logo de marca**. A capa pode ser foto ou vídeo.
- **Posição**: `x, y` = centro em px do base; `largura` em px (post 220–400). Sem `x/y/largura`, usa a composição pronta do vídeo de referência (9 lugares em volta da pessoa).
- **Giro** `rot: [rx, ry, rz]` em graus. `ry` é o Flip horizontal: cards da **esquerda com ry positivo** (olham pro centro), da **direita negativo**, 20–30°. `rx` é o Flip vertical ("mais deitadinho"), 0–12°. `rz` inclinação de 2–6°, alternando o sinal. Variar tamanhos e ângulos é o que faz o efeito.
- **Tempo**: `entra` em segundos (sem ele, usa os gestos). `sai` opcional. `anim`: `flip` (padrão, o 3D Flip), `pop`, `cai`, `vem` (sai do fundo).
- **Comentário** (`"tipo": "comentario"`): balão com avatar, `usuario`, `texto`, `quando`, `curtidas` (`"escuro": true` para tema escuro). Sem `midia`. Largura 420–560.
- **Notificação** (`"tipo": "notificacao"`): banner de celular com `app`, `titulo`, `texto`, `cor_app` e `simbolo` (letra no ícone). Largura 540–700. Fica bem com `"anim": "cai"`.
- `"frente": true`: card na frente da pessoa (um pequeno, num canto, dá profundidade). Comentários e notificações na frente funcionam bem, longe do rosto.
- **Caos** (vários elementos se amontoando): `deriva` (px/s, ~25) faz cada card andar numa direção; `deriva_giro` (°/s, ~3) faz girar; `flutuar` 1.5+ deixa o balanço mais nervoso. Gere a lista com um script (tempos acelerando: `t = ini + (fim-ini)·(k/N)^0.6`, posições aleatórias fora do rosto). Exemplo em `exemplos/caos.py`.
- **Some tudo**: `some_tudo` (segundo) faz todos os cards incharem e serem sugados juntos em `some_duracao` (0.2 s), com som de sugada; depois disso, nenhum efeito sonoro e a trilha corta seco. `voz_antes`/`voz_depois` controlam o áudio original antes e depois (ex.: 0.25 → 1.0, o silêncio do ambiente volta).
- **Holograma**: `"holograma": true` (global ou por card): o conteúdo escuro do card acende em ciano, o branco vira vidro, com contorno aceso, linhas de varredura, aberração cromática, tremulação e glitch. Hologramas somam luz (sem sombra).
- `opacidade` (global ou por card, ex.: 0.85): transparência leve nos elementos; deixa o cenário aparecer sem perder a leitura. Mais claro que o holograma.
- Globais: `fundo` (`original` | `estudio` | caminho de imagem), `luzes` (`{"intensidade", "cores"}` ou `false`), `sombra` (0.16), `flutuar` (1 = balanço de rebote; 0 desliga), `duracao_entrada` (0.65 s), `focal` (1.3; menor = perspectiva mais forte), `cor: "rico"` (look rico e claro no final), `trilha` + `trilha_de` + `trilha_volume` (música que abaixa sob a voz).
- Estúdio: `pessoa: {"escala": 0.8, "x": 0, "y": 120}` encolhe/move a pessoa para os posts aparecerem mais (como no tutorial); `estudio: {"cor_parede", "cor_chao"}`; `reflexo` (liga sozinho se os pés aparecem); `chao` (y do chão em px, se o automático errar).

### Trilha de caos (opcional)
Para "ansiedade/excesso" até um corte seco:
```bash
python3 -I scripts/trilha_caos.py --dur 13.6 -o trilha-caos.wav     # dur = some_tudo
```
Pulso acelerando, tique-taque, baixo dissonante, escala de Shepard e gaguejo no fim. No `projeto.json`: `"trilha": "trilha-caos.wav", "trilha_volume": 0.9`. Ideia de roteiro que funciona: começar já no meio da ação, o caos cresce, tudo some num gesto da pessoa (deitar a cabeça, largar a caneta) e o resto é silêncio. Se cortar o vídeo bruto em dois trechos, esconda o corte no meio do caos.

### 5. Conferir antes de renderizar
```bash
python3 -I scripts/mural.py projeto.json --ver 3 6 9.5 15     # → posts-3d_*.jpg
```
Olhe também um quadro no meio de uma entrada (`entra` + 0.2) para ver o giro. Ajuste posições até nenhum card cobrir o rosto ou objetos que não foram recortados.

### 6. Renderizar
```bash
python3 -I scripts/mural.py projeto.json            # --rascunho = metade da resolução
```
Sai: `posts-3d.mp4` (voz + whoosh/pop em cada entrada), `posts-3d-camada-posts.mov` (só os posts, ProRes 4444 com transparência, para mexer no CapCut) e `posts-3d-sfx.wav`.

### 7. Revisar
```bash
ffmpeg -i posts-3d.mp4 -vf "fps=1,scale=216:-1,tile=10x2" -frames:v 1 folha.jpg
```
Confira o recorte sobre o vídeo todo (cabelo e mãos na frente dos cards, nada de card "furando" a pessoa), se a mídia certa aparece em cada card e se as entradas batem com os gestos.

## Erros comuns

| Sintoma | Causa | Correção |
|---|---|---|
| Card cobre cadeira/objeto mas some atrás da pessoa | o recorte só pega pessoas | `mascara_objetos.py` (passo 2), ou mover o card |
| Card "fura" a pessoa em alguns quadros | recorte falhou | revisar `mask/` sobre magenta, refazer só os quadros ruins |
| Post mostra o trecho errado | `de` errado | o vídeo do post começa em `de` no momento em que o card entra |
| Perspectiva exagerada ou chapada | `ry` ou `focal` | ry 20–30°, focal 1.1–1.6 |
| Luz escurecendo/manchando | intensidade alta | `luzes.intensidade` 0.2–0.35 em fundo escuro, até 0.5 no estúdio branco |
| Card parece sentado na cadeira | card sobre o assento (o recorte não pega a cadeira) | descer o card para o chão, com `"deriva": 0` para não subir |
| Reflexo flutuando | chão errado | definir `"chao"` em px |
