---
name: cenario-desenhado
description: Edita um vídeo falado (Reels/TikTok 9:16) de uma pessoa sentada colocando ela num cenário de animação desenhado em traço de caneta/guache que se transforma - poltrona, sofá, banquinho e topo de prédio desenhados embaixo dela, fundo de parede com quadros que se mexem, céu azul com nuvens e sol, cidade de prédios com janelas piscando, vista do alto de um prédio com a câmera se afastando, móveis que viram outros (morph), trocas de cenário em íris com borda laranja, tipografia condensada animada letra a letra presa à fala, estrelinhas, placa e setas, efeitos sonoros. Começa e termina no cenário real se quiser. Paleta verde, laranja, bege e rosinha. Use quando pedirem "cenário desenhado", "cenário de animação", "fundo desenhado", "sofá desenhado atrás de mim", "me coloca sentada num prédio desenhado", "móveis que se transformam", "edição estilo Katana/Higgsfield com motion graphic do sofá", "tipografia animada com cenário ilustrado", ou "edita igual ao vídeo da Mica no prédio".
---

# Cenário desenhado

A pessoa real, sentada, recortada sobre um cenário desenhado à mão que muda ao longo da fala: o móvel embaixo dela se transforma em outro, o fundo troca numa íris que abre de dentro dela, a câmera se afasta para mostrar que ela está no alto de um prédio, e as palavras entram letra a letra no topo da tela. Tudo sai de um `roteiro.json` e dois comandos, em Python + ffmpeg, sem app de edição e sem IA generativa (os desenhos são feitos por código).

Requisitos: macOS (o recorte usa o Vision do Mac e as fontes do sistema), `ffmpeg`, Python 3 com `pillow numpy faster-whisper`. Rode sempre com `python3 -I`.

**Gravação que funciona:** pessoa **sentada** (cadeira, banco, de pernas cruzadas), centralizada, câmera parada, corpo inteiro do assento para cima, cabeça na metade de cima da tela (o topo fica para os textos). Fundo liso ajuda o recorte. Em pé também funciona com `"assento": "nenhum"`.

## Passo a passo

`S=~/.claude/skills/cenario-desenhado/scripts`, numa pasta nova para o projeto:

### 1. Preparar (uma vez por vídeo, ~2–3 min para 30 s)
```bash
python3 -I $S/preparar.py /caminho/do/bruto.MOV          # --lingua en para inglês
```
Gera `base.mp4` (1080×1920, 30 fps), `quadros/`, `mask/` (recorte), `pernas/` (recorte com pernas e tênis firmes), `transcricao.json` e `info.json` com as medidas do corpo: quadro em que a pessoa entra, topo da cabeça, **linha do assento** (onde as pernas apoiam) e centro. Os móveis se encaixam nessa linha.

Confira as medidas impressas e a transcrição (nomes próprios saem errados; corrija o campo `"w"` sem mudar a quantidade de palavras). Se o assento ficar alto ou baixo demais nos quadros de teste, sobrescreva no roteiro com `"assento_y"` (e `"centro_x"`, `"cabeca_y"`).

### 2. Ler as palavras
```bash
python3 -I $S/motor.py roteiro.json --palavras     # precisa existir um roteiro.json, pode ser {"cenas": [{"em": 0}]}
```

### 3. Escrever o `roteiro.json`
Leia a fala e case cada frase com uma cena. Ritmo: troca de cenário a cada 2–5 s, na palavra que justifica (ex.: "transformar" → o móvel vira outro; "alto de um prédio" → `terraco`; "céu", "movimento" → `ceu`; "cidade", "todo mundo" → `cidade`). Modelos: `exemplos/roteiro-completo.json` (todas as cenas e textos escritos à mão; a fala que ele espera está no campo `_fala`) e `exemplos/roteiro-curto.json` (só cenas, textos automáticos).

```json
{
  "saida": "final.mp4",
  "real_ate": "@cenário+0.15",
  "real_volta": "@que#2-0.1",
  "cenas": [
    {"em": 0,              "fundo": "parede", "cor": "rosa", "quadros": "A", "assento": "poltrona"},
    {"em": "@transformar", "fundo": "parede", "cor": "verde_claro", "quadros": "B", "assento": "sofa"},
    {"em": "@do",          "fundo": "terraco", "assento": "predio"}
  ],
  "textos": [
    {"linhas": [{"txt": "O", "tam": "p"}, {"txt": "cenário", "tam": "gg"}, {"txt": "é uma parte importante", "tam": "p"}]}
  ]
}
```

### 4. Conferir quadros
```bash
python3 -I $S/motor.py roteiro.json --textos                 # blocos de texto que vão entrar
python3 -I $S/motor.py roteiro.json --ver 2.9 9.3 16.9       # → ver/q_02.90.jpg …
```
Olhe um quadro no meio de cada cena e um logo depois de cada troca: móvel encaixado embaixo das pernas, textos acima da cabeça, recorte limpo nos pés.

### 5. Renderizar (~5 min para 30 s)
```bash
python3 -I $S/motor.py roteiro.json
```
Saem `final.mp4` (voz + efeitos sonoros, volume de Reels), `final-camada-textos.mov` (textos com fundo transparente, ProRes 4444, para ajustar no CapCut) e `final-sfx.wav` (só os efeitos).

## Tempos (presos às palavras)

Número em segundos ou palavra da transcrição: `"@palavra"` (1ª vez), `"@palavra#2"` (2ª vez), `"@palavra+0.2"`, `"@palavra-0.1"`, `"@palavra:fim"`. Maiúscula não conta; acento conta. Palavras com mais de 3 letras também acham pelo começo ("@transf" acha "transformar").

## Cenas

| campo | valores | o que faz |
|---|---|---|
| `em` | tempo | quando a cena começa (a 1ª é 0). A troca é uma íris com borda laranja que abre de dentro da pessoa; o móvel se transforma no novo em ~0,5 s |
| `fundo` | `parede`, `ceu`, `cidade`, `terraco` | parede com quadros balançando (coração pulsando, sol girando, ondas, montanha, planta) + planta e luminária; céu com nuvens andando, sol e passarinhos; cidade de prédios coloridos com janelas piscando e calçada; terraço = céu e cidade lá embaixo, **a câmera se afasta** e mostra o prédio alto (volta de supetão na cena seguinte) |
| `assento` | `poltrona`, `sofa`, `banquinho`, `predio`, `nenhum` | o que fica embaixo da pessoa. `predio` combina com `terraco` |
| `cor` | `rosa`, `verde_claro`, `bege`, `ceu_claro`, … ou `"#RRGGBB"` | cor da parede (só `parede`) |
| `quadros` | `A` ou `B` | conjunto de quadros na parede |
| `planta_e_luminaria` | true/false | enfeites dos lados |

## Textos

Sem `"textos"`, a skill gera sozinha: cada frase vira um bloco com as palavras pequenas em volta e a mais longa gigante. Fica muito melhor escrevendo à mão, escolhendo a palavra forte de cada frase.

Cada bloco entra quando a primeira palavra é dita e sai quando o próximo começa. Cada linha precisa ser **um trecho contínuo da fala**, na ordem e com a grafia da transcrição (sem pontuação).

| campo da linha | valores |
|---|---|
| `txt` | o trecho da fala |
| `tam` | `p` (frase pequena, 70 px), `m` (160), `g` (240), `gg` (320); `g`/`gg`/`m` em maiúsculas condensadas, letra por letra com mola |
| `px` | tamanho exato, se quiser |
| `cor`, `sombra` | nomes da paleta ou `#RRGGBB` (padrão: laranja com sombra verde-escura; pequenas em verde-escuro) |
| `efeito` | `onda` (letras ondulando: "movimento"), `pula` (letras pulando: "legal"), `brilho` (estrelinhas em volta: "mágica"), `placa` (faixa laranja atrás + setas para baixo: palavra de comentário) |

Linhas largas encolhem para caber; o bloco inteiro encolhe se fosse encostar na cabeça (inclusive com a câmera afastada no terraço).

## Opções globais

`saida` ("final.mp4"), `real_ate` (o vídeo começa no cenário real e o desenho invade nesse tempo; omita para começar desenhado), `real_volta` (o cenário real volta nesse tempo e fica até o fim), `inicio` (corta o começo; padrão = quando a pessoa aparece), `assento_y`, `centro_x`, `cabeca_y`, `tamanho_moveis` (padrão pela largura das pernas), `saturacao` (1.15), `sfx_volume` (1.0), `trilha` (arquivo de música) + `trilha_volume` (0.18, abaixa sozinha quando a pessoa fala), `processos`.

## Regras que deixam bonito (aprendidas no vídeo da Mica)

- **Atrás das pernas, cores claras.** O recorte deixa um contornozinho branco nos pés (o banco real); sobre assento claro ele some, sobre cor escura fica evidente. Os móveis já vêm claros onde encostam nas pernas; se mudar cores em `moveis.py`, mantenha isso.
- **A frente do assento passa por cima da base das pernas** (a pessoa "afunda" na almofada) — é o que esconde o banco real. Se aparecer banco embaixo dos pés, abaixe `assento_y` uns 10 px; se cortar demais a perna, suba.
- **Começar e terminar no cenário real** (`real_ate`, `real_volta`) deixa claro que é a mesma pessoa, no lugar de verdade, e o desenho "invade".
- Transformação de móvel com **troca de cor seca na metade** (misturar laranja com verde dá marrom).
- Textos só no topo, acima da cabeça. Uma palavra forte por bloco, no máximo 3–4 linhas.
- Cor clara e saturada; não escureça.

## Erros comuns

| Sintoma | Causa | Correção |
|---|---|---|
| "palavra não encontrada" / "texto não encontrado na fala" | grafia diferente da transcrição, ou linhas fora de ordem | `--palavras`; copie o trecho exatamente |
| móvel flutuando ou entrando no corpo | linha do assento medida errada (roupa clara, banco da mesma cor) | `"assento_y"` no roteiro |
| móveis grandes ou pequenos demais | pessoa longe/perto da câmera | `"tamanho_moveis": 0.9` |
| pés piscando ou com buracos | recorte automático oscilando | fundo liso na gravação; refaça `mask/` e `pernas/` |
| texto em cima do rosto | cabeça muito alta no quadro | `"cabeca_y"` menor (o texto encolhe mais) ou reenquadre a gravação |
