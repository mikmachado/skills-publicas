---
name: texto-seguindo-gestos
description: Edita um vídeo falado (Reels/TikTok 9:16) em que a pessoa desenha formas no ar com as mãos e a frase falada fica presa na forma desenhada - arco quando as duas mãos sobem e abrem, quadrado/retângulo quando uma mão sobe, cruza por cima e desce, círculo quando as mãos dão a volta, linha quando a mão varre na horizontal, oval que fecha no final. O texto aparece por onde a mão passa, a forma se fecha, fica um pouco em cena e sai; entra a próxima. Trechos sem gesto viram bloco de texto entrando com a fala. Rastreia as duas mãos (Vision da Apple), detecta os gestos e sugere as formas sozinho, mantém a cor original (valoriza só se pedirem) e usa texto branco grosso com sombra forte. Use quando pedirem "texto seguindo gestos", "texto seguindo as mãos", "texto seguindo os dedos", "o texto forma o que eu desenho com a mão", "texto em arco/quadrado/círculo com as mãos", "frase presa na forma", ou "edita igual ao vídeo do jardim".
---

# Texto seguindo gestos

A pessoa fala e, a cada frase, desenha uma forma no ar. A frase fica **presa na forma, parada no lugar** (não escorrega atrás da mão): aparece onde a mão passa, a forma se fecha, fica ~0,5 s e sai subindo e sumindo; entra a próxima.

Requisitos: macOS (Vision da Apple via `swiftc`; fonte Avenir Next Condensed do sistema), `ffmpeg`, Python 3 com `numpy opencv-python pillow faster-whisper`. Rode os scripts com `python3 -I`. `<skill>` = a pasta desta skill. Exemplo completo: `exemplos/jardim.json`.

## O que aprendemos nos testes (não repetir os erros)

- **NÃO** fazer fita de texto correndo atrás da mão (letra escorregando pelo rastro): fica embolado e ela não gostou. O certo é forma geométrica limpa, parada, uma por frase.
- Formas **geométricas e limpas** ajustadas ao tamanho/posição do gesto — não o traço tremido da mão.
- Texto **branco**, Avenir Next Condensed Heavy, com **sombra forte** (halo largo + sombra projetada + contorno escuro). Em fundo colorido/ar livre nada de amarelo; destaque = letra maior.
- **Vídeo do iPhone é HDR** (HLG/Dolby Vision, 10 bits). Tratar como vídeo comum deixa tudo APAGADO e com qualidade pior (aconteceu nos testes). O `preparar.sh` detecta (`hdr.txt`), mantém `base.mp4` em HDR, gera `quadros/` em SDR só para rastrear e conferir; `formas.py` compõe direto no sinal HLG e `montar.sh` entrega HEVC 10 bits HDR. Nunca converta a saída para SDR/H.264.
- **Cor: por padrão a ORIGINAL do arquivo** (o ajuste de cor mudava demais o que foi gravado). Só valorize se pedirem: `COR=1 bash preparar.sh ...` (usa `scripts/cor.txt`: vibrance, contraste, quente, vinheta) e `"quadros": "quadros_cor"` no projeto.
- O texto tem que **ler da esquerda pra direita para quem assiste**. Se a mão varre da direita pra esquerda, espelhe aquele trecho (`espelhar`) — a imagem vira, o texto não.
- Retângulo: um pedaço da frase em cada lado (esquerda, cima, direita), **nunca letra no canto**.
- Sem gesto grande na frase → **bloco** acima da cabeça entrando palavra por palavra.
- Áudio original, 1x, sem cortes e sem música (ela põe a música ao postar), -16 LUFS.

## Antes de começar

Pergunte só o que faltar (o vídeo). Mostre imagem a cada etapa (`gestos.jpg`, `ver.jpg`) — é olhando que se acerta. Uma pasta por vídeo; rode tudo de dentro dela.

## Passo a passo

### 1. Preparar (quadros, cor, mãos, transcrição)
```bash
mkdir -p ~/dev/meu-video && cd ~/dev/meu-video
bash <skill>/scripts/preparar.sh /caminho/do/bruto.MOV
```
Gera `base.mp4`, `quadros/`, `maos.json`, `corpo.json`, `maos2.npy`, `transcricao.json`. Cor valorizada só se pedirem: `COR=1 bash preparar.sh ...` (ou `COR="filtro ffmpeg"`) cria `quadros_cor/`; aí use `"quadros": "quadros_cor"` no projeto.

Se a pose da MÃO do Vision travar (acontece: o modelo não carrega), o `preparar.sh` desiste dela em ~(quadros/2 + 60) s e segue só com a pose do corpo — funciona bem para as formas. Rastreio: pulso pela **pose do corpo** (estável com braço aberto) + ponta do indicador pela pose da mão quando ela está perto do pulso. Mão 0 = a que aparece à **esquerda da tela**, mão 1 = à direita.

### 2. Detectar os gestos
```bash
python3 -I <skill>/scripts/gestos.py          # --altura 160 = quanto a mão sobe acima do descanso p/ contar
```
Escreve `gestos.jpg` (um quadro por gesto com o traço das mãos e os tempos) e `projeto_sugerido.json`, e lista no terminal: tempo, forma, mãos e frase de cada gesto. **Olhe o `gestos.jpg`** e confira com a pessoa se lembrar ("primeiro foi um arco, depois um quadrado, depois um círculo…") — ela costuma lembrar a ordem das formas. Regras do detector:
- gesto = trecho em que alguma mão está bem acima da posição de descanso (colo/lados);
- 2 mãos que saem juntas do meio e abrem → `arco`; 2 mãos que saem dos lados e dão a volta → `elipse` (círculo);
- 1 mão que sobe e desce várias vezes indo para o lado (zigue-zague) às vezes some (traços estreitos viram "pequeno") ou sai como `retangulo`: use `caminho` com os picos e vales;
- 1 mão que passa perto dos dois cantos de cima → `retangulo`; trecho longo na horizontal → `linha` (avisa se for da direita pra esquerda); senão arco por cima (`elipse` 180→360);
- oval de fechamento (arco por cima + mão descendo pelo lado) costuma sair como `retangulo`: troque pelas duas metades de elipse (abaixo);
- frase vai para o gesto com que mais se sobrepõe (a fala vem um pouco antes do gesto); frase sem gesto → `blocos`.

### 3. Revisar o projeto
`cp projeto_sugerido.json projeto.json` e ajuste olhando o `gestos.jpg`:
- tipo e números da forma (a caixa do traço é o ponto de partida; arredonde, centralize em x≈540 quando for simétrico);
- `linhas` (quebre a frase: retângulo = 3 pedaços; linha = 2; círculo curto = repita a frase com `•`);
- `g0`/`g1` (gesto), `fecha` (quando o que faltou se completa), `sai` (quando some; antes do próximo gesto). `sai: 99` = fica até o fim;
- blocos que coincidem com uma forma: apague ou mude o tempo;
- `trocas` para nomes (CLAUDIO → CLAUDE).

Formato (ver `exemplos/jardim.json`):

| campo | o quê |
|---|---|
| `tipo: arco` | `cx`, `base` (y dos pés do arco), `rx` (meia largura), `alt` (altura) |
| `tipo: retangulo` | `x0 y0 x1 y1`, `r` (canto). Texto: `linhas` = [esquerda, cima, direita] |
| `tipo: elipse` | `cx cy rx ry`, `a0 a1` em graus (0 direita, 90 baixo, 180 esquerda, 270 cima). Círculo inteiro 180→540; metade de cima 180→360; **metade de baixo 180→0 com `"letras": "dentro"`** (lê da esquerda pra direita) |
| `tipo: linha` | `x0 y0 x1 y1`; com 2 `linhas`, a 1ª fica em cima do traço e a 2ª embaixo |
| `tipo: caminho` | `pontos` = [[x,y]…] na ordem da leitura; curva suave passando por eles — zigue-zague "sobe e desce", onda, qualquer traço. Use com `varredura` (o texto entra da esquerda pra direita no tempo do gesto) e desvie os pontos do rosto. **Zigue-zague (sobe e desce):** `"suave": false` (traços retos) + `"por_traco": true` + `linhas` = UMA PALAVRA POR TRAÇO ("" pula o traço) — foi o que ficou legível. Não use frase corrida na curva (embola nas pontas) nem `em_pe` (letras em pé espalham e não dá pra ler). **Onda:** pontos de uma senoide suave (amplitude ~34, comprimento ~460 px), `"traco": false`, `"desl": [0]`, `"ancora": 0.5` (letra centrada na onda, senão gruda nos vales e abre nas cristas), dois espaços entre palavras; várias ondas podem ir se empilhando com o mesmo `sai` |
| `maos` | [0], [1] ou [0, 1] — quais mãos "pintam" a forma |
| `tam` | tamanho da letra (encolhe sozinho se não couber) |
| `esquerda_pra_direita` | nunca aparece à direita antes da esquerda |
| `varredura` | ignora a mão e varre do começo ao fim durante o gesto |
| `desl`, `faixas`, `faixa` | afastamento de cada linha do traço (px, + = acima) e trecho do caminho (0–1) |
| `espelhar` | lista de [t0, t1] em que a imagem e as mãos são espelhadas |
| `blocos` | `linhas` = [[texto, tamanho]…], `y0`, `t0`, `sai` — palavras entram no tempo da fala |

Oval que fecha no final = duas elipses com o mesmo centro: metade de cima (180→360) e metade de baixo (180→0, `letras: dentro`), ambas com `sai: 99`.

### 4. Conferir e renderizar
```bash
python3 -I <skill>/scripts/formas.py --ver 1.5 3 5 7.5 12 16    # ver.jpg com esses instantes
python3 -I <skill>/scripts/formas.py                             # video_mudo.mp4
bash <skill>/scripts/montar.sh nome-do-video                     # final <30 MB (chega no celular) + versão -sem-audio; vídeo sem fala: --sem-tratar-audio
```
Na conferência, procure: letras faltando (a mão passou longe: aumente `alcance`, padrão 175 px), texto aparecendo de trás pra frente (use `esquerda_pra_direita` ou `espelhar`), forma cobrindo o rosto (mude a geometria), duas coisas ao mesmo tempo (ajuste `sai`).

Mande o arquivo final (já cabe no limite de 30 MB do celular). Confira a cor comparando um quadro do original com o final (mesma conversão para os dois).
