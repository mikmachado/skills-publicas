---
name: colagem-surreal
description: Edita um vídeo falado (Reels/TikTok 9:16, gravado em fundo verde) como colagem editorial surreal frase a frase - a pessoa recortada em P&B contrastado sobre papel off-white com objetos coloridos realistas, brincando com escala - cabeça gigante com a tampa do crânio voando, cérebro e uma versão mini da pessoa sentada dentro dele; pessoa pequena ao lado de objetos gigantes com carimbo de X; cópias coloridas dela imitando; TV antiga em glitch com feixe vermelho chegando nela; mala que enche de verdade com as coisas que ela cita e passagem dirigindo um carro antigo; cabeça de perfil num círculo de papel rasgado com silhueta e pontilhado; celular em colagem com feed de rede social que enche e explode; tesoura recortando; figurinhas duotone; peixe e nuvem surreais; CTA com etiqueta vermelha. Cortes secos, câmera que aproxima e afasta, letra de marcador, efeitos sonoros. Use quando pedirem "colagem surreal", "edição estilo colagem editorial com escala", "cabeça gigante com cérebro", "eu mini sentada na minha cabeça", "colagem P&B com objetos coloridos", "TV com feixe vermelho", "mala enchendo", "celular explodindo de conteúdo", ou "edita igual ao vídeo da Mica surreal".
---

# Colagem surreal

Esta skill é uma **caixa de efeitos**, não um modelo fechado: o roteiro de cada vídeo nasce da fala da pessoa. `exemplos/roteiro-completo.json` é só um exemplo comentado (o vídeo de demonstração); nunca reaproveite as falas, tempos ou textos dele.

Cada frase da fala vira uma cena de colagem: a pessoa recortada (muitas vezes em P&B contrastado) sobre papel claro, objetos realistas coloridos em volta e um absurdo visual que torna literal o que ela diz ("acessar o repertório" → as coisas saem da cabeça e entram no celular até ele explodir). Tudo sai de um `roteiro.json` e três comandos em Python + ffmpeg.

Requisitos: macOS (recorte e rostos pelo Vision do Mac), `ffmpeg`, Python 3 com `pillow numpy faster-whisper`. Sempre `python3 -I`. Fonte: Marker Felt (já vem no Mac).

## Antes de tudo: o que gravar (fundo verde, mesma roupa em tudo)

A fala inteira é gravada **na ordem**, num arquivo só, trocando de enquadramento entre as frases. A pessoa fica parada para facilitar o recorte; o movimento vem da edição. Combine o take com o tipo de cena:

| take | enquadramento | vira a cena |
|---|---|---|
| em pé, corpo inteiro, de frente | câmera longe, pés no chão | `em_pe` |
| plano médio de frente | cabeça grande no quadro | `cerebro`, `mala`, `cta` |
| sentada de perfil numa cadeira (com algo na mão) | corpo inteiro com a cadeira | `tv` |
| perfil e 3/4, plano médio | cabeça e ombro | `celular` (perfil), `perfil` (3/4) |
| sentada de frente, mãos no joelho, **calada** | corpo inteiro | a mini dentro do cérebro enquanto a gigante fala |
| sentada de frente **falando** a frase seguinte | corpo inteiro | a mini fala de dentro do cérebro |
| de frente **calada**, ~2 s | plano médio | a gigante parada ouvindo a mini |
| extras curtos (lupa, capuz, careta) | qualquer | `canto`, `cabeca_canto`, figurinhas |

Fundo verde é o ideal. Sem verde (parede lisa, longe de móveis) a skill usa só o recorte de pessoa do Mac: funciona, mas o recorte **não é garantido** (cabelo, mãos, objetos na mão e cadeira podem falhar ou tremer). Avise a pessoa antes de gravar.

Regras: a mini **nunca** mexe a boca enquanto a gigante fala (grave um take calado). Cada take tem uma intenção: pergunte antes de reaproveitar um take para outra frase.

## Passo a passo

`S=~/.claude/skills/colagem-surreal/scripts`, numa pasta nova para o projeto, com o `roteiro.json` (comece copiando `exemplos/roteiro-completo.json`; troque `fala` e `takes` pelos arquivos da pessoa).

### 1. Preparar (uma vez; ~10 min para 1 min de vídeo)
```bash
python3 -I $S/preparar.py roteiro.json
```
Gera `quadros/<take>/`, `recorte/<take>/` (RGBA), `rostos/<take>.json`, `fala.wav` e `transcricao.json`. Takes extras no roteiro: `"takes": {"calada": {"arquivo": "x.mov", "de": 3.5, "ate": 8}}`.

Revise a transcrição (campo `"w"`; nomes e gírias saem errados) e o recorte:
```bash
python3 -I $S/motor.py roteiro.json --recorte     # ver/recorte_<take>.jpg sobre magenta, o vídeo todo
```

### 2. Montar o mapa de cenas com a pessoa (antes do roteiro)

1. Leia as referências que a pessoa mandar (prints, vídeos) e descreva o que vê em cada uma: tipografia, cor, escala, movimento. Pergunte o que ela **não** quer.
2. Leia a transcrição e divida em cenas de 5–15 s, uma por take gravado.
3. Para cada frase, proponha uma imagem literal e o efeito (tabela: frase · imagem · efeito · take). Exemplos: "avaliar" → mini com lupa no cérebro; "perder tempo" → TV; "juntar experiências" → mala; "virar conteúdo" → celular; "não é X" → X gigante com carimbo; "comenta" → etiqueta.
4. Liste os objetos que faltam e ajude a gerá-los (ver Ativos). Mostre o mapa e espere o ok antes de escrever o roteiro.

Guarde na memória o que a pessoa corrigir: vira o estilo dela nos próximos vídeos.

### 3. Escrever o roteiro
```bash
python3 -I $S/motor.py roteiro.json --palavras    # palavras com tempo
python3 -I $S/motor.py roteiro.json --plano       # cenas, cortes secos e duração final
```
Divida a fala em cenas (uma por take/ideia, 5–15 s) e case cada frase com um absurdo visual literal.

### 4. Conferir quadros (tempos do vídeo FINAL, veja `--plano`)
```bash
python3 -I $S/motor.py roteiro.json --ver 2.5 12 30 47
```
Olhe um quadro no meio de cada momento: texto não cortado e sem cobrir rosto, objeto no lugar, câmera não cortando a cabeça.

### 5. Renderizar (~10 min para 1 min)
```bash
python3 -I $S/motor.py roteiro.json
python3 -I $S/motor.py roteiro.json --trecho 20 28 && python3 -I $S/motor.py roteiro.json --monta   # refazer só um pedaço
```
Saem `final.mp4` (voz + efeitos, -14 LUFS), `final-celular.mp4` (720p leve), `final-camada-textos.mov` (ProRes 4444 transparente, para o CapCut), `final-sfx.wav` e `final.srt`.

## Tempos

Número = segundos **da gravação**. `"@palavra"` = a palavra, procurada a partir do início da cena (`"@o#2"` = 2ª ocorrência, `"@palavra+0.3"`, `"@palavra:fim"`). Acento conta; maiúscula não; palavras com mais de 3 letras acham por começo.

Cortes secos são automáticos: dentro de cada cena só ficam as falas (pausas > 0,18 s saem). Trechos calados que devem ficar: `"fixos": [[19.0, 20.3]]`. Desligar: `"cortes_secos": false`.

## Campos comuns a toda cena

`tipo`, `de`, `ate`, `textos`, `camera`, `pb`, `raios` (raios cinza atrás; padrão sim em cérebro/mala/celular/perfil/cta), `fixos`.

- **`pb`**: `true`/`false`, `{"ate": "@palavra"}` (P&B até ali, depois cor) ou `{"de": "@palavra"}`. Só a pessoa fica P&B; objetos continuam coloridos. Alterne cenas em P&B e em cor.
- **`camera`**: lista de `[tempo, zoom, [x, y] ou null, duração]`. Duração 0 = corte seco (punch-in); > 0 = movimento suave. `[x, y]` é o ponto da tela que fica no centro. Sem `camera`, cada tipo tem um movimento padrão. A câmera ainda respira e desliza sozinha (nunca fica parada).
- **`textos`**: blocos que entram linha a linha quando a 1ª palavra da linha é dita:
  ```json
  {"linhas": [["o problema não é", "cinza", 66], ["edição", "vermelho", 150]], "ate": "@o"}
  ```
  Linha = `[texto, cor, tamanho]` ou `{"texto", "cor", "tam", "em", "x", "y"}` (use `em` quando o texto difere da transcrição, ex. "copiar" falado como "copiado"). Bloco: `x` (70), `y` (150), `max_x` (1040; o tamanho encolhe sozinho para caber), `ate` (padrão: até o próximo bloco). Uma ou duas palavras-chave em vermelho grande; o resto cinza pequeno.

## Tipos de cena

| tipo | o que faz | campos |
|---|---|---|
| `em_pe` | corpo inteiro pequeno sobre círculo amarelo, cenário de colagem (estante vinho cortada na borda + planta), objetos gigantes que levam carimbo de X; cópias dela em verde/azul/amarelo/rosa surgindo rápido atrás, imitando com atraso (o texto vai para trás delas) | `take`, `altura` (1150), `x` (640), `cenario` (["estante","planta"]), `objetos` [{`ativo`,`em`,`ate`,`x`,`y`,`alt`,`carimbo`}], `copias` {`de`,`ate`,`carimbo`} |
| `cerebro` | cabeça gigante; a tampa do crânio voa, o cérebro sobe e a mini cai sentada atrás dele (pernas escondidas); objetos em volta | `abre_em`, `mini` {`take` (take calado, ou `"fala"` se ela fala), `de` (onde começa a fala da mini), `cai_em`, `velocidade` 0.82}, `gigante` {`de`,`ate`} (trecho calado da gigante, vai e volta lento), `objetos` [{`ativo`,`em`,`onde`: mini/esquerda/topo/direita}], `canto` {`take`,`em`} (outro take subindo pelo canto), `cabeca_canto` {`take`,`em`,`cor`}, `figurinhas` |
| `tv` | aberta: sentada de perfil na cadeira (P&B), TV antiga cinza com tela em glitch colorido, feixe vermelho de bordas duras da tela até ela, círculo amarelo sob a TV, pipoca ao lado da cadeira | `take`, `altura` (640), `pipoca`, `objeto_sai` {`ativo`,`em`} (sai da tela em direção a ela) |
| `mala` | plano médio + mala aberta; cada coisa citada pula, cai dentro (com cópias) e a mala enche; passagem opcional dela dirigindo um carro antigo azul sobre a faixa amarela | `mala_em`, `itens` [{`ativo`,`em`,`copias` 2}], `enche` {`em`,`n`}, `pula_em`, `carro` {`de`,`ate`,`rosto` (tempo de um take de perfil)} |
| `celular` | só a cabeça de perfil num disco de papel (corte diagonal, silhueta, pontilhado); as coisas saem da cabeça e entram num celular em colagem com feed; ele treme, solta curtidas e corações e explode | `olha` (direita/esquerda), `disco_cor`, `celular_em`, `enche_em`, `explode_em`, `itens`, `feed_quadros` (tempos para as fotos do feed), `resultado` ("zine") |
| `perfil` | cabeça 3/4 ou de perfil num disco de papel; tesoura recortando o disco; figurinhas duotone; nuvem, peixe atravessando, coração | `olha`, `disco_cor`, `tesoura` {`de`,`ate`}, `objetos` [{`ativo`,`em`,`ate`,`x`,`y`,`larg`}], `figurinhas` [{`em`,`ate`,`quadro`,`cor`,`x`,`y`}], `nuvem_em`, `peixe_em`, `coracao_em` |
| `cta` | cabeça num círculo pontilhado, etiqueta vermelha com a palavra para comentar, objeto (o guia) | `etiqueta` {`texto`,`em`}, `objeto` {`ativo`,`em`,`x`,`y`} |

`figurinhas`: cabeça da própria pessoa num instante (`quadro` = segundos da gravação) em duotone `verde`, `amarelo`, `azul` ou `magenta`, com borda branca de adesivo.

Ativos que vêm com a skill (`ativo`): `cerebro lupa estrela mascara x rolo brilho livro carro aviao xicara1 celular tesoura peixe nuvem pipoca tv mala zine planta estante_vinho carro_lado_full`. Objeto novo: gere no Gemini *"hyper-realistic … on a perfectly flat solid pure green background (#00FF00), no shadows, no text"* e recorte com `python3 -I $S/ativo.py gerado.png nome` (`--divide` para vários lado a lado).

Efeitos sonoros saem sozinhos de cada cena (pop, carimbo, whoosh da tampa, queda da mini, papel, explosão). Sem trilha por padrão; opcional `"trilha": "musica.mp3"` + `"trilha_volume"` (abaixa sob a voz).

## Regras que deixam bom (aprendidas no vídeo de demonstração)

- **Corte seco** e **câmera viva**: abrir perto e afastar no momento da revelação; alternar perto/longe a cada frase. Pessoa parada + câmera parada = robô.
- **Escala é o principal**: pessoa pequena com objeto gigante; cabeça gigante com a mini dentro; objetos que entram em outros (cabeça → celular, coisas → mala) entram **de verdade** (camada da frente por cima, várias cópias).
- **P&B de vez em quando**, com os objetos em cor. Perfil = só a cabeça com corte diagonal sobre disco de papel.
- Texto na frente, menos quando fica por cima das pessoas (ex.: as cópias): aí vai para trás. Nunca deixar a câmera empurrar o rosto para cima de uma palavra-chave; nunca texto cortado.
- Pés e objetos apoiados no chão (sombra de contato); a TV/luz sempre virada para ela.
- Não escurecer o vídeo; papel claro.

## Erros comuns

| Sintoma | Causa | Correção |
|---|---|---|
| "palavra não encontrada" | grafia da transcrição ou `#n` contando do começo | `--palavras`; a busca começa no início da cena (e, nos textos, na linha anterior) |
| sobra de carpete/sujeira ou buraco no recorte | chão ou pano com dobra | `--recorte`; regrave com o chão mais limpo ou corrija o take e rode `preparar.py --refaz-recorte` |
| mini mexendo a boca | usou o take da fala no lugar do calado | `mini.take` = take calado enquanto a gigante fala |
| cabeça cortada na borda num zoom | foco da `camera` fora do rosto | mude o `[x, y]` ou diminua o zoom |
| palavra escondida atrás da cabeça | zoom empurrou o rosto para o texto | zoom menor naquele trecho ou texto em outra altura (`y`) |
