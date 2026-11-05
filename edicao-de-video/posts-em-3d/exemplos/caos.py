import json, math, random
random.seed(7)
A, B = 'midia/meu-reel.mp4', 'midia/outro-reel.mp4'
posts = [(A,0.3),(A,33),(B,2),(A,38),(A,44),(B,30),(A,12),(B,34)]
players = [("midia/capa1.jpg","Under Pressure","Queen & David Bowie",248),("midia/capa2.jpg","Stressed Out","Twenty One Pilots",202),
 ("midia/capa3.jpg","Mr. Brightside","The Killers",222),("midia/capa4.jpg","Dancing Queen","ABBA",231),("midia/capa5.jpg","Here Comes the Sun","The Beatles",185)]
coms = [("@ana.lu","posta mais vídeo assim!!!","1.204"),("@pedro_cria","cadê o tutorial???","87"),("@ju.edita","você sumiu?","12"),
 ("@rafa.design","responde meu direct por favor","3"),("@bia.reels","isso é IA né","45"),("@lucas.motion","como faz isso? me ensina","230"),
 ("@mari.conteudo","quanto você cobra pra editar?","9"),("@gui.ia","primeiraaa","2"),("@carol.cria","não entendi nada kkkk","61"),
 ("@leo.videos","manda o link do app","18"),("@nina.post","já viu a trend de hoje?","33")]
nots = [("Mensagens","Ana Lu","viu o reel que te mandei??","#34C759","M"),("E-mail","Cliente","Re: alteração no vídeo (urgente)","#0A84FF","@"),
 ("Lembretes","Postar hoje","O reels das 18h ainda não saiu","#FF9500","!"),("Agenda","Gravação em 10 min","Estúdio · levar o tripé","#FF3B30","15"),
 ("Social","@pedro_cria","mencionou você em um comentário","#DD2A7B","@"),("Bateria","Bateria fraca","10% restante","#30D158","%"),
 ("Mensagens","Família","32 mensagens novas","#34C759","M"),("Social","Seu post","47 novas curtidas","#8134AF","+"),
 ("E-mail","Newsletter","Últimas 3 horas de desconto!","#0A84FF","@"),("Mensagens","Bia","oi?? tá aí?","#34C759","M")]
itens = [("post",p) for p in posts]+[("player",p) for p in players]+[("comentario",c) for c in coms]+[("notificacao",n) for n in nots]
inicio = [i for i in itens if i[0]=="post"][:3]
resto = [i for i in itens if i not in inicio]; random.shuffle(resto)
itens = inicio + resto
N = len(itens); FIM = 12.9
rosto = (470, 600, 860, 1050)
out = []
for k,(tipo,d) in enumerate(itens):
    t = 0.25 + (FIM-0.25)*(k/(N-1))**0.62
    for _ in range(40):
        x = random.uniform(110, 970); y = random.uniform(130, 1780)
        if not (rosto[0]-60 < x < rosto[2]+60 and rosto[1]-80 < y < rosto[3]+60): break
    lado = 1 if x < 540 else -1
    e = {"entra": round(t,2), "x": round(x), "y": round(y)}
    if tipo=="post":
        e.update(midia=d[0], de=d[1], largura=random.randint(250,370), rot=[random.uniform(-10,10), lado*random.uniform(16,34), random.uniform(-9,9)])
    elif tipo=="player":
        e.update(tipo="player", midia=d[0], musica=d[1], artista=d[2], duracao=d[3], pos=random.randint(20,120),
                 largura=random.randint(240,320), rot=[random.uniform(-10,10), lado*random.uniform(14,30), random.uniform(-8,8)])
    elif tipo=="comentario":
        e.update(tipo="comentario", usuario=d[0], texto=d[1], curtidas=d[2], quando=random.choice(["agora","1 min","2 min","5 min"]),
                 largura=random.randint(420,560), rot=[random.uniform(-8,8), lado*random.uniform(8,26), random.uniform(-10,10)], anim="pop")
        e["frente"] = random.random() < 0.3
    else:
        e.update(tipo="notificacao", app=d[0], titulo=d[1], texto=d[2], cor_app=d[3], simbolo=d[4], quando="agora",
                 largura=random.randint(540,700), rot=[random.uniform(-6,6), lado*random.uniform(6,20), random.uniform(-6,6)], anim="cai")
        e["frente"] = random.random() < 0.35
    e["rot"] = [round(v,1) for v in e["rot"]]
    out.append(e)
for nome in ("caos.mp4",):
    cfg = {"base":"base.mp4","mascara":"mask_tudo","saida":nome,"fundo":"original","luzes":False,"sombra":0.2,
           "deriva":26,"deriva_giro":3,"flutuar":1.6,"duracao_entrada":0.5,"some_tudo":13.6,"some_duracao":0.18,
           "opacidade":0.85,"trilha":"trilha-caos.wav","trilha_volume":0.9,"voz_antes":0.25,"voz_depois":1.0,"posts":out}
    json.dump(cfg, open(nome.replace(".mp4",".json"),"w"), ensure_ascii=False, indent=1)
print(N)
