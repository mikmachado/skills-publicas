# Colagem surreal

Skill para o Claude Code que transforma um vídeo falado (gravado em fundo verde) numa **colagem editorial surreal**, frase a frase: você recortada em P&B sobre papel claro, objetos realistas coloridos e absurdos visuais que deixam literal o que você fala.

- cabeça gigante: a tampa do crânio voa, o cérebro sobe e uma versão mini sua senta dentro dele
- você pequena ao lado de objetos gigantes que levam um carimbo de X
- cópias coloridas suas imitando você
- TV antiga em glitch com feixe vermelho chegando em você
- mala que enche de verdade com as coisas que você cita, e você dirigindo um carro antigo
- cabeça de perfil num círculo de papel rasgado; celular em colagem que enche e explode
- tesoura recortando, figurinhas duotone, peixe e nuvem surreais, CTA com etiqueta vermelha
- cortes secos, câmera que aproxima e afasta, letra de marcador e efeitos sonoros

## Como usar

1. Grave a fala inteira em fundo verde, na ordem, trocando de enquadramento entre as frases (veja a tabela de takes no `SKILL.md`), e os takes extras curtos (sentada calada, objetos na mão).
2. Peça ao Claude: *"edita esse vídeo com a colagem surreal"* e mande os arquivos.
3. Ele prepara o recorte, escreve o `roteiro.json` com você, mostra quadros de prova e renderiza.

Saídas: o vídeo final, uma cópia leve, a camada só de textos (transparente, para ajustar no CapCut), os efeitos sonoros separados e a legenda `.srt`.

Requisitos: macOS, ffmpeg, Python 3 com `pillow numpy faster-whisper`.
