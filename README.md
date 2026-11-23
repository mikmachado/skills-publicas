# Skills públicas da Mik

Skills para o [Claude Code](https://claude.com/claude-code) que eu uso nas minhas edições e mostro no Instagram [@mik_machado](https://www.instagram.com/mik_machado/).

Uma **skill** é uma pasta com instruções (`SKILL.md`) e, às vezes, scripts que ensinam o Claude a fazer uma tarefa do jeito certo. Depois de instalada, você só pede em português ("coloca a legenda na parede em perspectiva") e o Claude segue o passo a passo da skill.

## Skills disponíveis

| Categoria | Skill | O que faz |
| --- | --- | --- |
| Edição de vídeo | [texto-em-perspectiva](edicao-de-video/texto-em-perspectiva/) | Cola legenda, posts e prints numa parede real do vídeo, em perspectiva, com você passando na frente. Faz também os cortes, a cor e o som. [Guia com imagens](edicao-de-video/texto-em-perspectiva/guia/README.md) |
| Edição de vídeo | [posts-em-3d](edicao-de-video/posts-em-3d/) | Posts de Instagram, telas de música, comentários e notificações flutuando em 3D atrás de você, com giro, rebote, sombra e som. Inclui a variação "caos", que some de uma vez. |
| Edição de vídeo | [vox-motion-graphics](edicao-de-video/vox-motion-graphics/) | Vídeo explicativo narrado em motion graphics (estilo Vox ou diorama de papel), do tema ao MP4 pronto, usando o Higgsfield. |
| Edição de vídeo | [colagem-derretendo](edicao-de-video/colagem-derretendo/) | Você derretendo em tinta preta no meio de uma colagem editorial: grade azul, palavras gigantes, meio-tom, frases em volta da cabeça, cenas nos óculos escuros e efeitos sonoros. [Guia com imagens](edicao-de-video/colagem-derretendo/guia/README.md) |
| Edição de vídeo | [cenario-desenhado](edicao-de-video/cenario-desenhado/) | Você sentada num cenário desenhado à mão que vai se transformando enquanto fala: poltrona, sofá, banquinho, topo de prédio, céu e cidade, com textos animados e começo e fim no cenário real. |
| Edição de vídeo | [textos-em-lugares](edicao-de-video/textos-em-lugares/) | A legenda da sua fala pintada no cenário real: no chão, num painel gigante atrás de você, nos degraus de uma escada, em volta do corpo, em anéis no chão e na parede, com você passando na frente. Faz também a montagem para Reels. |
| Edição de vídeo | [texto-seguindo-gestos](edicao-de-video/texto-seguindo-gestos/) | Você desenha formas no ar com as mãos e a frase fica presa na forma: arco, quadrado, círculo, linha, zigue-zague, ondas. O texto aparece por onde a mão passa, a forma fecha e sai. Mantém o HDR do iPhone. |
| Edição de vídeo | [desenhos-animados](edicao-de-video/desenhos-animados/) | Desenhos coloridos animados por cima do cenário real: linhas tremidas contornando muro, prédios, árvores e você, parede virando mosaico colorido, rabiscos no chão, título de filme, palavras pipocando presas à parede e frase final. Funciona com você parada na parede ou andando. [Guia com imagens](edicao-de-video/desenhos-animados/guia/README.md) |
| Edição de vídeo | [ganchos-balao](edicao-de-video/ganchos-balao/) | Balão de mensagem com a frase-gancho destruído de 3 jeitos seguindo seus gestos (cordinha acende, murro quebra em cacos, tesoura corta ao meio) e o CTA escrito no ar com o dedo, com a letra nascendo na ponta do dedo. Efeitos sonoros e HDR. [Guia com imagens](edicao-de-video/ganchos-balao/guia/README.md) |

## Como instalar uma skill

1. Instale o [Claude Code](https://claude.com/claude-code) (app desktop ou terminal).
2. Baixe este repositório: botão verde **Code → Download ZIP**, ou no terminal:
   ```bash
   git clone https://github.com/mikmachado/skills-publicas.git
   ```
3. Copie a pasta da skill que você quer para `~/.claude/skills/`. Exemplo:
   ```bash
   mkdir -p ~/.claude/skills
   cp -R skills-publicas/edicao-de-video/texto-em-perspectiva ~/.claude/skills/
   ```
4. Abra o Claude Code e peça. Ele encontra a skill sozinho pela descrição; se quiser garantir, diga "use a skill texto-em-perspectiva".

Cada skill tem um `README.md` com o que ela precisa instalado (por exemplo ffmpeg e Python) e um exemplo de pedido.

## Como as pastas estão organizadas

```
skills-publicas/
├── README.md                      ← você está aqui
└── edicao-de-video/               ← uma pasta por categoria
    ├── README.md                  ← lista das skills da categoria
    └── texto-em-perspectiva/      ← uma pasta por skill (é ela que vai para ~/.claude/skills)
        ├── README.md              ← para pessoas: o que faz e como usar
        ├── SKILL.md               ← para o Claude: as instruções
        ├── scripts/               ← ferramentas que o Claude roda
        └── exemplos/              ← arquivos de exemplo
```
