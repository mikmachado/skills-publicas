---
name: colagem-derretendo
description: Edita um vídeo falado (Reels/TikTok 9:16) no estilo colagem editorial com a pessoa derretendo - recorte da pessoa sobre papel bege claro, tinta preta brilhante escorrendo do busto, grade pontilhada azul, palavras gigantes condensadas atrás, rosto em meio-tom ou duotone, frases girando em volta da cabeça, cenas e letreiros dentro das lentes dos óculos escuros, parede de quadros em movimento (a câmera abre e depois aproxima), card de foto com fita, adesivos, lista em papel pautado, carimbo, comentário, curtidas e efeitos sonoros. Funciona com fundo verde ou qualquer fundo (recorte automático do Mac). Use quando pedirem "colagem derretendo", "tinta derretendo", "pessoa derretendo", "efeito de tinta escorrendo", "estilo AutoAE", "colagem editorial com grade azul", "texto nos óculos", "frase em volta da cabeça", "palavras gigantes atrás de mim", ou "edita igual ao vídeo da Mica derretendo".
---

# Colagem derretendo

A pessoa vira um busto recortado sobre papel bege, com tinta preta brilhante escorrendo por baixo dele: os pingos ficam atrás da pessoa, começam escondidos dentro do busto e só aparecem saindo pela borda de baixo (escorridos com bulbo, brilho e pingos caindo). Por cima, uma colagem editorial presa às palavras da fala. Tudo sai de um `roteiro.json` e dois comandos, em Python + ffmpeg, sem app de edição.

Requisitos: macOS (o recorte e os olhos usam o Vision do Mac), `ffmpeg`, Python 3 com `pillow numpy faster-whisper`. Rode sempre com `python3 -I`.

## Passo a passo

`S=~/.claude/skills/colagem-derretendo/scripts`, numa pasta nova para o projeto:

### 1. Preparar (uma vez por vídeo, ~2 min para 1 min de vídeo)
```bash
python3 -I $S/preparar.py /caminho/do/bruto.MOV          # --lingua en para inglês
```
Gera `base.mp4` (1080×1920, 30 fps), `quadros/`, `mask/` (recorte), `olhos.json` (rosto e olhos), `transcricao.json` e `info.json`. Quadros com fundo verde chapado são recortados pela cor; o resto, pelo recorte de pessoa do Mac, suavizado no tempo.

Revise a transcrição: nomes próprios e gírias saem errados ("cloud" → "Claude"). Corrija o campo `"w"` das palavras sem mudar a quantidade de palavras.

### 2. Ler as palavras
```bash
python3 -I $S/motor.py roteiro.json --palavras     # precisa de um roteiro.json, mesmo vazio: {"efeitos": []}
```

### 3. Escrever o `roteiro.json`
Leia a transcrição frase a frase e case cada frase com um efeito (tabela abaixo). Ritmo: algo novo a cada 2–4 s, sem empilhar mais de 3 coisas ao mesmo tempo. Modelos prontos: `exemplos/roteiro-curto.json` (15 s, fundo comum) e `exemplos/roteiro-completo.json` (50 s, fundo verde, óculos escuros, todos os efeitos).

```json
{
  "saida": "final.mp4",
  "efeitos": [
    {"tipo": "tratamento", "modo": "meio", "de": 0, "ate": "@totalmente"},
    {"tipo": "rotulo", "de": 0, "ate": "@totalmente"},
    {"tipo": "gigante", "texto": "PROVAR", "em": "@provar", "ate": "@totalmente"}
  ]
}
```

### 4. Conferir quadros
```bash
python3 -I $S/motor.py roteiro.json --ver 3.2 8.4 14.0     # → ver/q_03.20.jpg …
```
Olhe um quadro no meio de cada efeito: texto legível, nada cobrindo a boca, palavras gigantes não escondidas atrás do rosto, recorte limpo. Para revisar o recorte, veja também quadros espalhados pelo vídeo inteiro (o recorte automático oscila; um quadro bom não prova nada).

### 5. Renderizar
```bash
python3 -I $S/motor.py roteiro.json --rascunho   # meia resolução, mais rápido
python3 -I $S/motor.py roteiro.json              # final (processos em paralelo; ~2 min para 15 s)
```
Saem `final.mp4` (voz + efeitos sonoros, volume de Reels), `final-camada-textos.mov` (todos os textos com fundo transparente, ProRes 4444, para ajustar no CapCut) e `final-sfx.wav` (só os efeitos sonoros).

## Tempos (presos às palavras)

Número em segundos ou palavra da transcrição: `"@palavra"` (1ª vez no vídeo), `"@palavra#2"` (2ª vez), `"@palavra+0.2"`, `"@palavra:fim"`. Acento conta ("é" ≠ "e"); maiúscula não. Palavras com mais de 3 letras também acham por começo ("@caprich" acha "caprichosa").

**Atenção:** em `ate`, a palavra é procurada **a partir do `de`/`em`**. Então `"de": "@ele#2", "ate": "@mas"` pega o primeiro "mas" depois do segundo "ele". Não use `#n` no `ate` contando desde o começo do vídeo (dá "palavra não encontrada"). E `ate` igual à própria palavra do `de` dura zero: use a palavra seguinte.

Comuns: `de`/`em` (início), `ate` ou `dur` (fim). `x`, `y` são frações da tela (0–1).

## Efeitos

| tipo | o que faz | campos | use quando |
|---|---|---|---|
| `tratamento` | a pessoa em meio-tom P&B (`meio`) ou duotone (`azul`, `laranja`, `verde`, `rosa`, `pb`); flash branco na troca | `modo`, `de`, `ate` | abertura em meio-tom; uma frase dramática em azul |
| `rotulo` | legenda pequena em fonte mono, azul, digitando palavra a palavra no topo | `de`, `ate` (palavras da fala) ou `texto`; `x`, `y`, `cor`, `fundo` | quase o vídeo todo, frase a frase |
| `italico` | frase em serifa itálica no topo | `texto`, `em`, `ate`, `y` (0.156), `tam` (64) | frase leve, apelido, "muito obrigada" |
| `gigante` | palavra enorme condensada atrás da pessoa, entra com mola | `texto`, `em`, `ate`, `y` (0.80), `tam` (330), `contorno`, `treme`, `frente` | a palavra de impacto da frase |
| `fileiras` | a palavra repetida em fileiras que correm e enchem a tela atrás | `texto`, `em`, `ate` | o tema do vídeo, o "uau" |
| `contorno` | frase girando em volta da cabeça, acompanhando o cabelo | `texto`, `de`, `ate`, `tam` (54), `velocidade` | frase de 3–6 palavras |
| `lentes` | conteúdo dentro das lentes dos óculos escuros | `modo`: `letreiro` (`texto`), `palavras` (`esquerda`, `direita`), `filme` (`cenas_de`, `cenas_ate`), `coracoes`, `emoji`; `fundo`, `cor` | só com óculos escuros (a skill detecta; sem óculos ela ignora e avisa) |
| `parede` | a câmera abre e revela uma parede de quadros da própria pessoa (meio-tom, duotone, alguns tocando), depois volta | `de`, `ate` (≥ 2,5 s), `zoom` (0.52), `tratamentos` | "imagina", "todo mundo", empolgação, virada |
| `soco` | aproximação seca e tremida curta | `em`, `dur` (1.0), `zoom` (1.06) | volta de assunto, "mas", "ah" |
| `foto` | o quadro original (com o fundo real) vira foto com borda branca e fita | `de`, `ate`, `legenda` | bastidores, "olha onde eu estou" |
| `adesivos` | chuva de ícones e adesivos em volta, que voam para fora no fim | `de`, `ate`, `itens` (kit), `intervalo` | lista de coisas, "ideias", "tudo isso" |
| `adesivo` | um adesivo de papel (emoji ou imagem) com borda branca | `emoji` ou `imagem`, `em`, `ate`, `x`, `y`, `tam` | um objeto citado na fala |
| `prompt` | caixinha de prompt digitando | `texto`, `em`, `ate` | "pedi pra IA…" |
| `carimbo` | carimbo de borracha laranja | `texto`, `em`, `ate`, `x`, `y` | "deu certo", "aprovado" |
| `lista` | papel pautado com fita, itens digitando | `titulo`, `itens`, `em`, `ate`, `marcas` (uma palavra por item) | "separei uma lista" |
| `comentario` | comentário de rede social + "AQUI EMBAIXO ↓" | `usuario`, `texto`, `em`, `ate` | chamada para comentar |
| `curtidas` | selo de curtidas | `n`, `em`, `ate`, `x`, `y` | "curte", "deixa o like" |
| `flash` | flash branco | `em` | corte forte |

Kit de `adesivos` (`itens`): `"camera"`, `"play"`, `"musica"`, `"chat"`, `"email"`, `"foto"`, `"video"`, `"ia"`, `"lapis"`, `"paleta"`, `"coracao"`, `"estrela"`, `"mic"`, `"link"`, `"calendario"`, `"mapa"`, `"tesoura"`, `"lampada"`, `"foguete"`, `"grafico"` (ícones genéricos, sem marca), `{"tipo": "emoji", "nome": "💡"}`, `{"tipo": "forma", "forma": "estrela|circulo|anel|brilho|seta", "cor": "#1F3DC7"}`.

## Opções globais do roteiro

`saida` ("final.mp4"), `fundo` ("#F6F0E6", o bege), `acento` ("#1F3DC7", o azul da grade e das palavras), `tamanho` (1.0 = rosto com ~440 px de largura na tela; o corpo nunca passa de ~900 px), `rosto_y` (0.28 = topo do rosto na tela), `busto` (0.95 = onde o corpo é cortado, em alturas de rosto abaixo do queixo; aumente para mostrar mais ombro), `tinta_modo` ("atras" = pingos saem de trás do busto, padrão; "escorre" = a própria imagem cede e escorre para dentro de cada pingo), `tinta_inicio` (3.2 s até a tinta escorrer toda; 0 = já começa escorrida), `tinta_fim` (true = escorre mais no último 1,8 s), `tinta_comprimento` (1.0), `grade` (true), `saturacao` (1.18), `aproxima_no_fim` (true), `sfx_volume` (1.0), `trilha` (arquivo de música) + `trilha_volume` (0.18; abaixa sozinha quando a pessoa fala), `forcar_lentes`, `processos`.

## Regras que deixam bonito (aprendidas no vídeo de demonstração)

- **Palavras gigantes embaixo, nunca na altura do rosto.** Atrás da cabeça ficam ilegíveis; embaixo, entre os escorridos, ficam ótimas. Duas linhas: `y` 0.776 e 0.896 com `tam` 300. Uma linha: `y` 0.80–0.85. Em cima (`y` 0.06) só durante a `parede`.
- **`soco` leve (1.06).** Zoom forte joga as palavras gigantes para fora da tela.
- `rotulo` e `italico` dividem o topo: não use os dois na mesma hora, a não ser com `y` diferentes.
- `contorno` precisa de espaço em volta da cabeça: não junte com `fileiras` nem com `parede`.
- `foto` mostra o fundo real da gravação. Com fundo verde, só funciona nos trechos gravados sem o verde.
- Abra em meio-tom e passe para a cor na 2ª ou 3ª palavra forte: é o gancho.
- Termine com `italico` ("muito obrigada,") + `gigante` ("TCHAU."): a tinta escorre mais no final.
- Cor clara e saturada; não escureça o vídeo.

## Erros comuns

| Sintoma | Causa | Correção |
|---|---|---|
| "palavra não encontrada" | grafia diferente, ou `#n` no `ate` | `--palavras`; no `ate`, conte a partir do `de` |
| tinta escorrendo de uma mesa ou dos braços | corte do busto baixo demais | `"busto": 0.7` |
| pessoa pequena ou grande demais | rosto muito perto ou longe da câmera | `"tamanho": 1.2` ou `0.85` |
| lentes manchando os olhos | sem óculos escuros (ou óculos claros) | tire o efeito `lentes` |
| contorno da pessoa tremendo ou com buracos | recorte automático oscilando (fundo parecido com a roupa) | grave com fundo liso ou verde; refaça `mask/` |
| palavra gigante cortada | `tam` alto ou zoom | `tam` menor; tire o `soco` naquele trecho |
