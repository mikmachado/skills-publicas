---
name: textos-em-lugares
description: Edita um vídeo falado (Reels/TikTok 9:16) colocando a legenda DENTRO do cenário real, como se o texto estivesse pintado no lugar, com a pessoa recortada passando na frente - texto deitado no chão em perspectiva, palavras gigantes num painel atrás da pessoa, frases que nascem nos pés e a pessoa pisa nelas, texto pintado numa escada com a letra dobrando em cada degrau, frase andando em volta do corpo, anéis de texto girando no chão com câmera de cima, chão inteiro coberto de "TEXTO" para o fechamento/CTA e texto na parede. Rastreia câmera na mão, recorta pessoas (inclusive quem passa ao fundo) e faz a montagem final com cortes presos à fala, 1.2x, cor e áudio tratado. Use quando pedirem "texto no chão", "texto na escada", "texto em volta de mim", "texto circular", "texto pintado no cenário", "legenda que faz parte do lugar", "texto em vários lugares", "pisar no texto", "chão cheio de texto", ou "edita igual ao vídeo dos textos em lugares".
---

# Textos em lugares

O vídeo é uma sequência de cenas curtas, cada uma com um "lugar" diferente para o texto. Cada cena é um vídeo da pessoa falando; o texto entra palavra por palavra no tempo da fala, branco com sombra (amarelo claro `#FFE26E` só nas palavras-chave), letras grossas (Avenir Next Heavy / Condensed Heavy), e a pessoa fica na frente.

Requisitos: macOS (recorte pelo Vision da Apple via `swift`; fontes Avenir do sistema), `ffmpeg`, Python 3 com `numpy opencv-python pillow faster-whisper`. Rode os scripts com `python3 -I`. `<skill>` abaixo = a pasta desta skill.

## Os efeitos (scripts/efeitos/)

| Efeito | Script | Melhor cenário | Câmera |
|---|---|---|---|
| Chão + painel gigante atrás (gancho de abertura) | `chao_e_painel.py` | pessoa sentada/parada, chão à frente | tripé |
| Pisar no texto | `pisar.py` | pessoa andando em direção à câmera | tripé |
| Escada pintada (letra dobra no degrau) | `escada.py` | escada de frente, pessoa num degrau | na mão ok |
| Texto contornando o corpo | `contorno.py` | pessoa de corpo inteiro contra um muro | quase parada |
| Texto circular no chão | `circulo.py` | câmera do alto, pessoa em pé no chão | na mão ok |
| Chão cheio de TEXTO + chamada (CTA) | `chao_cheio.py` | caminho/corredor, pessoa vindo | na mão ok |
| Texto na parede | `scripts/parede/` | parede lateral lisa | tripé |

**O texto é automático e vem da fala de cada vídeo**: `scripts/comum/frases.py` lê a `transcricao.json`, divide em frases (pausas e pontuação), escolhe a palavra-chave de cada uma e cada efeito monta o layout sozinho (título, linhas, anéis, chamada…). Nada é fixo de um vídeo específico.

Por cena você só ajusta um `cena.json` (exemplo em `exemplos/cena.json`):
- `trocas` — corrige palavras da transcrição (ex.: `{"cloud": "Claude"}`);
- `destaques` — as palavras-chave (amarelas/gigantes); sem isso, escolhe a palavra de conteúdo mais longa de cada frase;
- `max_palavras` — tamanho máximo de uma frase;
- `geometria` — os números do LUGAR (trapézio do chão, curva dos degraus, ponto de fuga, ponto entre os pés…). O topo de cada script lista quais lê e o padrão.

Veja as frases antes: `python3 -I <skill>/scripts/comum/frases.py` (mostra cada frase com a palavra-chave em `*MAIÚSCULAS*`). Confira o efeito com `--ver t1 t2 ...` (gera `ver_*.jpg` só daqueles instantes) antes de renderizar tudo.

## Antes de começar

- Pergunte só o que faltar: os vídeos de cada cena e a ordem. O resto tem padrão.
- Mostre imagens a cada etapa (grade, `--ver`, folha de quadros). É olhando que se acerta.
- Uma pasta por cena (`cena1/`, `cena2/`...) dentro da pasta do projeto. Rode tudo de dentro da pasta da cena.

## Passo a passo de cada cena

### 1. Base, quadros e transcrição
```bash
ffmpeg -i bruto.MOV -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" -r 30 -c:v libx264 -crf 16 -c:a aac base.mp4
mkdir -p quadros mask && ffmpeg -i base.mp4 -q:v 2 quadros/%05d.jpg
python3 -I <skill>/scripts/comum/transcrever.py base.mp4          # -> transcricao.json (tempo por palavra)
```
Mostre as frases (`frases.py`) e corrija nomes próprios com `trocas` no `cena.json` (ex.: "Cloud" → "Claude"). Ajuste `destaques` se a palavra-chave escolhida não for a melhor.

### 2. Recorte da pessoa
```bash
swift <skill>/scripts/comum/seg.swift quadros mask
```
Audite sobre magenta, 1 quadro a cada ~1–2 s. Problemas comuns e correções:
- **Pessoa pequena/longe ou borda ruim (aba falsa no boné, cabelo borrado):** recorte ampliado em retângulos e junte:
  ```bash
  swift <skill>/scripts/comum/seg_crop.swift quadros mcA 200 560 520 600     # x y w h
  swift <skill>/scripts/comum/seg_crop.swift quadros mcB 0 250 1080 800
  python3 -I <skill>/scripts/comum/juntar_mascaras.py mask_fina mask mcA:200,560,520,600 mcB:0,250,1080,800
  ```
  Os efeitos usam `mask_fina/` automaticamente se existir.
- **Gente passando ao fundo (só pernas, o Vision não pega):** depois do rastreio (passo 3), `python3 -I <skill>/scripts/comum/pessoas_passando.py x0 y0 x1 y1` (área onde passam) → `mask_gente/`. Se quiser reforçar, rode antes `seg_crop.swift quadros mask_topo ...` nessa área. Nunca preencha o espaço entre as pernas (o texto tem que aparecer ali).
- Mão/bolsa semitransparentes vazando texto: os scripts já fecham buracos da pessoa principal.

### 3. Câmera na mão: rastreio
O texto tem que grudar na superfície. Use **só a superfície onde vai o texto**, sem pessoas e sem paredes perto da câmera (paralaxe = texto tremendo):
```bash
python3 -I <skill>/scripts/comum/rastrear_plano.py 420 300 1060 1880    # x0 y0 x1 y1 -> homografias.json (SIFT + ECC)
python3 -I <skill>/scripts/comum/rastrear_lk.py                         # alternativa p/ piso liso (fluxo óptico)
```
Confira o tremor: projete 4 pontos da superfície por todas as homografias e meça o salto quadro a quadro — tem que ficar < ~1 px. Se aparecer salto grande num trecho (gente cobrindo a superfície, câmera mexendo rápido), troque para `rastrear_lk.py` ou restrinja a área.

### 4. Geometria do lugar (cena.json → geometria)
```bash
python3 -I <skill>/scripts/comum/grade.py base.mp4 --t 0.5 -o grade.jpg
```
- **Chão (chao_e_painel, pisar):** `quad_chao` = trapézio do chão na tela (bordas laterais apontando pro ponto de fuga do caminho). No painel, `pico` = palavra que lota a tela quando é falada (ex.: "texto"). No pisar, a posição vem dos pés no recorte; `frente` empurra a frase mais pra frente.
- **Chão cheio / círculo:** câmera virtual. Ache o ponto de fuga cruzando duas linhas paralelas do chão (bordas do caminho): `fuga` = [x, y], `focal` ~1550 (iPhone 1x, vídeo vertical); `chao_poligono` = onde é chão. No círculo, `inclinacao` é o ângulo do eixo (câmera do alto ~45°) e `pes` o ponto entre os pés; ajuste até os anéis parecerem deitados no chão.
- **Escada:** na grade, anote o y da borda de 3–4 degraus e ajuste `degraus` = [EA, EB, EC] em `y = EA + EB/(EC - k)`; `patamar_k` = onde começa o patamar plano; `espelho` = fração do degrau que é espelho (parte vertical) na tela; `borda_x`, `lado_x` (coluna livre ao lado da pessoa). A letra é desenhada "desdobrada" e quebra em cada quina — é isso que dá a sensação de pintada.
- **Contorno:** `chao_y` (y dos pés, onde o caminho é cortado) e `janelas_fundo` (áreas de fundo parado para compensar a tremidinha).

### 5. Texto: estilo e ritmo (já é o padrão dos efeitos)
- Como cada efeito usa as frases: chão+painel = palavra-chave gigante atrás, resto no chão; pisar = cada frase nasce à frente dos pés; escada = 1ª frase vira título fixo, as outras sobem ao lado da pessoa e a palavra-chave vai gigante no patamar; contorno = 1ª frase anda em volta do corpo, as outras aparecem grandes no alto; círculo = um anel por frase (frente, depois atrás); chão cheio = palavra-chave da 1ª frase gigante + cobre o chão, o resto da fala em linhas ao fundo.
- Palavra por palavra no tempo da fala; nada de itálico fino, letra de mão ou cores médias que somem no fundo.
- Varie tamanhos: palavra-chave gigante, conectivos menores. Gancho forte já no 1º quadro da abertura.
- Muito texto funciona: pico de "TEXTO TEXTO TEXTO" no painel, anéis que se acumulam sem sair de cena, chão inteiro coberto no fim.
- Não corte letras na borda do muro/tela: reduza a largura máxima da linha.
- Texto "pintado" (escada, chão cheio) multiplica pela luz do lugar: a sombra da pessoa escurece as letras.

### 6. Render da cena
```bash
python3 -I <skill>/scripts/efeitos/<efeito>.py --ver 1.0 3.5 6.0     # confira
python3 -I <skill>/scripts/efeitos/<efeito>.py                       # -> comp.mp4
ffmpeg -i comp.mp4 -vf "fps=1,scale=216:-1,tile=8x2" -frames:v 1 folha.jpg
```
Mande uma prévia leve (`scale=540:-2`) para a pessoa aprovar cena por cena.

## Montagem final
Na pasta do projeto, crie `montagem.json` (exemplo em `exemplos/montagem.json`) e rode:
```bash
python3 -I <skill>/scripts/comum/montar.py montagem.json
```
- Cortes presos à fala: tira pausas > 0,35 s de cada cena; `segura_fim: true` mantém o final da última cena (tempo pra ler o CTA).
- 1.2x (`velocidade`), cor quente/ensolarada (`scripts/comum/cor.txt`, filtros do ffmpeg — edite à vontade).
- Áudio: iguala o volume das cenas (gravações em lugares diferentes chegam a 9 dB de diferença), limpa a voz (grave, "s", compressão), whoosh nas trocas de cena e pop nas palavras de `pop`, volume final −16 LUFS com pico ≤ −4 dB (sem estouro). `musica`: caminho de uma trilha (abaixa sozinha sob a voz) ou `null` para a pessoa pôr a música no app ao postar.
- Para mandar pro celular: reencode em 1080×1920 ~5 Mbps (`-b:v 4800k`), fica com ~25 MB.

## Texto na parede (scripts/parede/)
Fluxo do efeito clássico de parede lateral em perspectiva (tripé): `parede.py` desenha a parede plana a partir de `projeto.json` (ver `exemplos/parede_projeto.json`: `"parede"` com `lado`, `vp`, `focal`, `z`, `y`; `"telas"` com as frases), `perspectiva.py` cola na parede com a pessoa na frente (`--mistura multiplicar --mascara mask`) e `cortes.py` faz cortes/zoom/cor/som dessa cena. `cartao.py` gera um cartão avulso.

## Erros comuns
| Sintoma | Causa | Correção |
|---|---|---|
| Texto tremendo/escorregando | rastreio pegou parede perto da câmera ou gente | rastrear só a superfície do texto; `rastrear_lk.py` |
| Letra torta na escada | estreitamento horizontal | use só a dobra vertical (CONV = 0) |
| Buraco no texto em volta da pessoa | recorte "inchado" (aba no boné, cabelo) | `seg_crop.swift` + `juntar_mascaras.py` |
| Texto some entre as pernas de quem passa | máscara preenchendo buracos | `pessoas_passando.py` (não preenche) |
| Palavra cortada na borda | linha larga demais | reduzir largura máxima / tamanho |
| Áudio estourando | volumes diferentes entre cenas + normalização dinâmica | `montar.py` (ganho por cena + 2 passadas + limitador) |
