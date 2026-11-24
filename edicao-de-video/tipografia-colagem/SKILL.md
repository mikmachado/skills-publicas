---
name: tipografia-colagem
description: Cria um Reels/TikTok 9:16 de TEXTO ANIMADO estilo colagem a partir de uma narração gravada - cada frase vira uma cena de tipografia presa à fala, com letras gigantes condensadas caindo uma a uma, palavras pipocando com contorno e sombra, fundo de zebra roxa/vermelha ondulando, cards pretos com fonte fina, rabiscos amarelos à mão (setas, círculos, cobra, estrelas, faíscas), muro de letras que desaba, palavra saindo do papel, câmera riscada com X, olho que pisca, balão de "comenta" e CTA final. Paleta roxo, amarelo, vermelho, preto e bege, com grão de filme e tremidinha de câmera nos cortes. Fotos da pessoa viram recortes em P&B com borda de figurinha e movimento de GIF (pulo, dança, tremor). Inclui tratamento da voz (corta pausas, 1.2x, tira ruído), trilha e efeitos sonoros sintetizados. Use quando pedirem "texto animado", "tipografia animada", "kinetic typography", "vídeo só de texto com a minha voz", "motion de texto estilo colagem", "letras caindo", "vídeo tipo esse com gráficos e texto", "narração com texto na tela estilo pôster", ou "edita igual ao vídeo da criatividade".
---

# Tipografia colagem

Narração → Reels 9:16 (1080x1920, 30 fps) de tipografia animada estilo colagem. Cada cena é um **modelo** configurado num `projeto.json` e presa a uma **palavra da fala**. Não precisa de filmagem: só o áudio e, se quiser, 3 a 5 fotos da pessoa.

Requisitos: Mac, `ffmpeg`, Python 3 com `numpy pillow faster-whisper`, e `swiftc` (Xcode CLT) para o recorte. As fontes (Anton e Quicksand, licença OFL) estão em `fontes/`.

Scripts em `~/.claude/skills/tipografia-colagem/scripts/` (chame de `SK`).

## Fluxo

1. **Roteiro** (se a pessoa ainda não gravou): curto, ~25–35 s lidos, frases curtas e diretas. Marque em CAIXA ALTA as palavras que viram cena (ex.: CRIATIVIDADE, VISTO, BORA). Termine com CTA "comenta X". Cada frase = 1 cena; 15 a 18 cenas para ~22 s depois de 1.2x.
2. **Áudio**: crie a pasta do projeto e rode
   `python3 SK/preparar_audio.py <audio> <pasta> --texto "<roteiro>"`
   Ele transcreve com tempo por palavra (faster-whisper), corta as pausas para 0.14 s, acelera 1.2x (`--velocidade`), tira ruído e normaliza. Gera `voz.wav`, `palavras.json`, `transcricao.txt`.
   - **Confira a transcrição.** Nomes próprios saem errados (ex.: "Claude" → "Cloud"). Ou corrija o `"w"` em `palavras.json`, ou use a palavra como ela saiu nas referências da cena.
3. **Fotos** (opcional): copie para `<pasta>/fotos/` como `.jpg` com nomes simples (`selfie.jpg`, `apontando.jpg`) e rode `python3 SK/recortar.py <pasta>/fotos`. Sai `<nome>_cut.png` (P&B contrastado, recortado pelo Vision da Apple). Clareia sozinho foto muito escura; force com `--clarear nome`.
   Bons encaixes: selfie → `olho_foto`; apontando → `video`; pulando/sorrindo → `palavra` com `"movimento":"pulo"`; agachada/tímida → `palavra` com `"tremor"`.
4. **projeto.json**: escreva as cenas (catálogo abaixo). Parta de `exemplos/criatividade.json`, que é o vídeo de referência inteiro.
5. **Prévia**: `python3 SK/motor.py <pasta>/projeto.json --ver 0.3,1.2,2.5,...` (um tempo no meio de cada cena) → `saida/previa.jpg`. Olhe e corrija: texto vazando, foto cobrindo rosto (suba as letras com `ys` ou traga a foto para frente com `"atras": false`), cena curta demais.
6. **Montagem**: `bash SK/montar.sh <pasta>/projeto.json` → `saida/<nome>.mp4` (alta, ~130 MB por causa do grão), `<nome>-leve.mp4` (prévia) e `<nome>-POSTAR.mp4` (10 Mbps, < 30 MB, para o Reels). ~2 min num M1/M2.

## projeto.json

```json
{"nome": "video", "voz": "voz.wav", "palavras": "palavras.json", "fotos": "fotos", "saida": "saida",
 "bpm": 124, "musica": true, "volume_musica": 1.0, "volume_efeitos": 1.0, "final_extra": 1.6,
 "cenas": [ {"tipo": "...", "inicio": "palavra", ...}, ... ]}
```

- `inicio`: palavra da fala em que a cena começa (corta 0.06 s antes; mude com `"antes"`). A 1ª cena começa no 0.
- Referência de palavra: `"criar"` = 1ª vez que aparece; `"criar#2"` = 2ª vez. Ignora maiúsculas e pontuação, **não** ignora acento.
- Campos `*_em` / `em` = palavra em que aquele elemento entra.
- Cores: `roxo, roxo_escuro, amarelo, vermelho, preto, bege, creme, laranja` (ou `[r,g,b]`). Fundos: `preto, bege, amarelo, roxo, zebra_roxa, zebra_vermelha, zebra_amarela`.
- `foto`: `{"nome": "selfie", "altura": 800, "x": 540, "y": 1500, "giro": -4, "movimento": "pulo|danca|tremor|respira", "atras": true}`.

## Catálogo de cenas (`tipo`)

| tipo | o que faz | campos |
|---|---|---|
| `queda` | 1 ou 2 palavras gigantes caindo letra a letra, quicando | `linhas` (1–2), `em`, `fundo`, `cores`, `enfeite`: `faiscas` \| `cobra` (cobra amarela + estrelas) |
| `zebra_card` | card de zebra roxa inclinado subindo, palavra em 2 linhas pipocando com contorno, tira de papel lateral, seta amarela | `linhas`, `tira` (lista curta), `seta` |
| `card_fino` | fundo amarelo com palavra repetida rolando, card preto com fonte fina, linhas entrando na fala, círculo roxo | `padrao`, `linhas`: [{`texto`, `em`, `grossa`, `cor`}], `circulo`, `circulo_linha` |
| `palavra` | etiqueta + palavra grande em 1–2 linhas pipocando; coringa com extras | `etiqueta`, `etiqueta_y`, `etiqueta_cor` [fundo, texto], `em`, `linhas`, `ys`, `tamanho`, `cores`, `contorno`, `sombra`, `balanco`, `pincelada`, `letra_cai` (última letra cai), `seta`, `faiscas`, `estrelas`, `foto` |
| `cadeado` | etiqueta, palavra num card vermelho, legenda num card preto, cadeado amarelo rabiscado | `etiqueta`, `palavra`, `em`, `legenda`, `legenda_em`, `cadeado_em` |
| `linhas` | título que encolhe e sobe, linhas de uma palavra repetida enchendo a tela, card preto final | `titulo`, `repetir`, `de`, `ate`, `card_pequeno`, `card_grande` |
| `camera` | câmera desenhada, card roxo com 2 linhas, X vermelho | `etiqueta`, `camera_em`, `linhas` [{`texto`,`em`}] x2, `x_em` |
| `olho_foto` | foto num card de zebra amarela respirando, olho que pisca, etiqueta, palavra circulada | `foto` (só `nome`/`movimento`), `etiqueta`, `palavra`, `em` |
| `muro` | palavra em tijolos coloridos (castelo) que desaba | `etiqueta`, `palavra` (9 letras = 3x3), `colunas`, `cai_em` |
| `papel` | palavra numa folha pautada que descola do papel + lâmpada | `etiqueta`, `palavra`, `em`, `sai_em`, `lampada_em` |
| `fina_onda` | palavra fina enorme com cobra passando + palavra grossa em onda | `etiqueta`, `fina`, `fina_em`, `meio`, `onda`, `onda_em` |
| `video` | título + card de vídeo com play e barrinha; foto apontando ao lado | `titulo`, `padrao`, `card_texto`, `em`, `foto` |
| `dupla` | card A + rabisco "+" + card B (ex.: VOCÊ + CLAUDE) | `etiqueta`, `a`, `b`, `b_em`, `a_cor`, `b_cor` |
| `pergunta` | card preto: fina em cima, grossa no meio, fina circulada embaixo | `topo`, `grande`, `grande_em`, `baixo`, `baixo_em` |
| `cta` | balão "comenta" + palavra gigante caindo, faíscas e zigue-zague | `balao`, `palavra`, `em` |

## Regras que fazem funcionar

- **Uma cena por frase curta**, 0.5 a 2.5 s. Cena longa (>2 s) precisa de vários `*_em` para ter coisas entrando ao longo da fala.
- Palavra grande: até ~6 letras por linha. Palavra longa → quebre em 2 (`CRIATI`/`VIDADE`, `EMPOL`/`GANTE`). O motor reduz sozinho o que passar de 960 px.
- Alterne fundos de uma cena para a outra (preto → bege → amarelo → zebra). Não repita o mesmo fundo em sequência.
- Foto nunca pode ter o rosto coberto: confira na prévia. Rosto atrás de letra → suba as `ys` ou use `"atras": false`.
- O movimento de GIF é "travado" a 8 quadros/s de propósito (stop-motion).
- Voz: preferência por **1.2x** e pausas curtas. A pessoa pode pedir 1.0 ou 1.1.
- O CTA final tem ~1.5 s depois da última palavra (`final_extra`).
- Som: whoosh em cada corte, pop nas letras, estrondo no muro, ding na lâmpada, risco no X/cadeado, batida de 124 bpm que abaixa sob a voz. Tudo sintetizado em `audio.py`, livre para usar.
- Ajustes depois: mude só o `projeto.json` e rode `montar.sh` de novo. Cena nova = função `m_<tipo>` + `s_<tipo>` em `motor.py` e uma linha em `MODELOS`.
