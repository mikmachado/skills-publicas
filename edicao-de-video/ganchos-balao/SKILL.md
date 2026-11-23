---
name: ganchos-balao
description: Edita um Reels/TikTok 9:16 em que um balão de mensagem (estilo WhatsApp) com a frase-gancho fica acima da cabeça da pessoa e é "destruído" de 3 jeitos, numerados 1/3, 2/3, 3/3, seguindo os gestos dela. 1/3 = puxa uma cordinha e o balão apagado acende piscando; 2/3 = murro para cima, o balão quebra em cacos de vidro e um cai na cabeça; 3/3 = tesoura com os dedos corta o balão em duas metades que caem (ou cutucão que estoura com fumaça, ou mão que apaga a mensagem por trás). No fim, a pessoa escreve o CTA no ar com o dedo ("COMENTE / GANCHO") e as letras nascem na ponta do dedo, sincronizadas quadro a quadro, sempre NA FRENTE de tudo (como escritas na lente da câmera). Tudo com efeitos sonoros (clique, vidro, toc, tesoura, rasgo, pop) e saída HDR. Use quando pedirem "ganchos no balão", "balão de mensagem destruído", "Esto es un hook", "balão que acende/quebra/é cortado", "3 ganchos", "escrever no ar com o dedo", "comente gancho".
---

# Ganchos no balão

Um balão de mensagem com a frase-gancho fica acima da cabeça da pessoa. Ela o destrói de 3 jeitos, um por trecho, com o contador **1/3 · 2/3 · 3/3** no topo, e fecha escrevendo o CTA no ar com o dedo. Os efeitos ficam **presos aos gestos reais** dela (punho, murro, dedos), não ao relógio.

Requisitos: macOS (Vision da Apple via `swiftc`; fontes Helvetica Neue e Marker Felt do sistema), `ffmpeg` e Python 3 com `numpy opencv-python pillow`. O recorte da pessoa usa um venv com `torch transformers` (SegFormer) (crie uma vez: `python3 -m venv .venv && .venv/bin/pip install torch transformers pillow opencv-python`). Rode os scripts com `python3 -I` e `<skill>` = a pasta desta skill. O exemplo completo está em `exemplos/porta-de-vidro.json`.

## Lições (não repetir os erros)

- **Siga o gesto que a pessoa fez**, não o da referência (no vídeo original, depois do murro o gesto era tesoura, e não tapa). Olhe a filmagem quadro a quadro (`grade.py`) antes de decidir o 3/3. Dedos em V = `tesoura`; dedo esticado = `cutucao`; mão varrendo = `apagar`.
- **Na hora de "apagar" a mensagem, a mão passa ATRÁS do balão**, senão ela cobre tudo e não se vê a mensagem sumindo. Nos outros gestos (cordinha, murro, tesoura), a mão passa na frente (máscara da pessoa).
- **A escrita fica SEMPRE NA FRENTE, como se ela escrevesse na lente da câmera: sem máscara nenhuma.** A mão NÃO passa na frente das letras. A oclusão da mão foi testada da mão (por cor de pele e depois pelos pontos do Vision) e qualquer letra atrás da mão foi vista como falha. É mais simples e fica melhor.
- **Escrita sincronizada de verdade:** rastreie a ponta do indicador em TODOS os quadros (Vision, `dedo.py`). A letra avança pelo quanto o dedo andou (0.3) e por até onde ele foi para a direita (0.7); se o dedo para, a escrita para. Encaixe cada linha na faixa onde o dedo escreve (mesma altura e mesma largura, um pouco maior). Marcar o dedo "a olho" a cada 6 quadros errou feio, às vezes caindo no rosto.
- **Câmera traseira:** a pessoa escreve da direita para a esquerda na tela. Use `"espelhar": true` na escrita: só o trecho do CTA é espelhado, e o texto continua lendo normal.
- **Balão grande e legível**, mas com folga das bordas (o Instagram cobre as laterais). `escala_balao` em torno de 1.0–1.15; a largura sai do tamanho da frase.
- **Frase-gancho com número e promessa**, numa linha só. A escolhida foi "3 ganchos que ninguém pula". Frases longas viram duas linhas e o balão fica pesado.
- Cor sugerida: **laranja** (balão laranja com letra branca e escrita laranja). Também existe `"cor": "verde"` (WhatsApp).
- **Fundo claro (janela)**: contador escuro com halo branco (`"contador_escuro": true`).
- **HDR do iPhone continua HDR** (HLG 10 bits). Nunca converta a saída para SDR.
- Sempre entregue a versão **-POSTAR.mp4** (HEVC HDR, −14 LUFS, < 30 MB).

## Passo a passo

### 1. Preparar
```bash
mkdir -p ~/dev/meu-gancho && cd ~/dev/meu-gancho
bash <skill>/scripts/preparar.sh /caminho/do/bruto.MOV
```
Gera `base.mp4`, `quadros/NNNN.jpg` (SDR, só para analisar) e `f/todos.jpg`, uma folha com um quadro a cada 5, numerados. **Olhe `f/todos.jpg`** e anote onde está cada trecho: o braço sobe para a cordinha, o murro, o gesto do 3/3, a escrita e a saída.

### 2. Marcar os gestos com a grade
```bash
python3 -I <skill>/scripts/grade.py 14 50 3          # de 14 a 50, de 3 em 3
python3 -I <skill>/scripts/grade.py 214 340 6 --espelhar
```
A grade tem as **coordenadas escritas** (px do quadro 1080x1920). Leia direto nos números, sem fazer conta de escala. Anote:
- **cordinha:** o punho quadro a quadro (`punho`), quando pega (`pega`), quando acende (`acende` = quando o puxão termina) e quando solta (`solta`). Atalho: `bash maos.sh 8 58 maos_13.json` + `python3 -I punho.py maos_13.json 8` sugerem o `punho`.
- **murro:** o quadro em que o punho bate na base do balão (`impacto`), onde bate (`ponto`), e quando/onde a cabeça "recebe" o caco (`na_cabeca`, `cabeca`), de preferência no instante em que ela se encolhe ou põe a mão na cabeça.
- **3/3:** o `modo`; para `tesoura`, os `tiques` (cada fechada dos dedos), `corte` (da base, onde estão os dedos, até o topo) e `estouro` (quando parte).
- **centro_balao:** acima da cabeça, com a base do balão na altura que o punho alcança no murro.

### 3. Recorte da pessoa (só onde a mão encosta no balão)
```bash
<venv>/bin/python <skill>/scripts/mascara.py 14-50,76-94,158-184
```
Leva ~5 s por quadro, então gere só os trechos necessários. Se o venv não existir: `python3 -m venv .venv && .venv/bin/pip install torch transformers pillow opencv-python`.

### 4. Ponta do dedo na escrita
```bash
bash <skill>/scripts/maos.sh 214 385 maos_cta.json --espelhar     # início e fim do CTA; --espelhar se o CTA for espelhado
python3 -I <skill>/scripts/dedo.py
```
**Olhe `f/dedo_ok.jpg`** (o círculo amarelo tem que estar na ponta do dedo) e `f/trajeto.jpg` (o desenho do dedo no ar). O `dedo.py` imprime o x do dedo ao longo do tempo: quando o x volta para a esquerda, começou a 2ª linha. Isso define `janela` e `faixa_dedo` de cada linha.

Se o Vision travar (aconteceu num dia; no outro voltou), o `maos.sh` desiste em 4 min. Tente de novo mais tarde; marcar o dedo à mão é o último recurso.

### 5. projeto.json
Copie `exemplos/porta-de-vidro.json` para `projeto.json` e preencha:

| campo | o quê |
|---|---|
| `trechos` | `[início, fim, "1/3"]`… e o CTA com `null`. Os cortes são secos entre eles |
| `mensagem`, `cta` | frase do balão; as 2 linhas escritas no ar |
| `cor`, `cor_escrita` | `laranja`/`verde`; RGB da escrita |
| `escala_balao`, `centro_balao` | tamanho e centro (x, y) do balão |
| `cordinha` | `ancora` (`esquerda`/`direita`: o lado do braço que puxa), `punho` {quadro: [x,y]}, `pega`, `acende`, `solta` |
| `soco` | `impacto`, `ponto` [x,y], `na_cabeca`, `cabeca` [x,y] |
| `terceiro` | `modo` (`tesoura`/`cutucao`/`apagar`), `contato`, `estouro`; tesoura: `corte`, `tiques`; apagar: `mao` {quadro: x da mão}; cutucão/apagar: `ponto` |
| `escrita` | `espelhar`; `linha1`/`linha2`: `tam_cx_base` [tamanho, centro x, base y], `janela` [quadros], `faixa_dedo` [x ini, x fim]; `sublinhado` (quadro) |
| `volume_original` | 1 = mantém o som do vídeo; 0 = só efeitos |

### 6. Conferir e renderizar
```bash
python3 -I <skill>/scripts/ganchos.py --ver 30 84 98 172 180 260 300 350   # ver.jpg + f/ver_N.jpg
bash <skill>/scripts/montar.sh nome-do-video
```
Na conferência, procure:
- a cordinha saindo do canto do balão até dentro do punho;
- o murro batendo na base do balão;
- o caco chegando na cabeça no instante da reação;
- o corte da tesoura entre duas palavras;
- a letra nascendo na ponta do dedo, inteira e na frente da mão;
- o texto inteiro quando a pessoa sai.

Saídas: `nome.mov` (master HDR), `nome-leve.mp4` (para conferir no celular) e **`nome-POSTAR.mp4`** (para postar).
