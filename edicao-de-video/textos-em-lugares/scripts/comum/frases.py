"""Frases da cena a partir da transcrição — usado por todos os efeitos.

Lê transcricao.json (de transcrever.py) e, se existir, cena.json da pasta da cena:
  {
    "trocas":   {"cloud": "Claude"},        # corrige palavras da transcrição (sem mudar a contagem)
    "destaques": ["texto", "escada"],       # palavras-chave (amarelas/gigantes); vazio = escolha automática
    "max_palavras": 6,                      # tamanho máximo de uma frase
    "geometria": {...}                      # números do lugar, cada efeito diz quais lê (cfg())
  }
Uma frase = palavras seguidas sem pausa longa (> 0,3 s) e sem ponto final no meio.
Cada palavra vira um dicionário: {"t": texto, "s": início, "e": fim, "chave": bool}.
"""
import json, os, re, unicodedata

PARADAS = set("""a o as os um uma uns umas e é de da do das dos em no na nos nas pra pro para por com sem que
se eu tu ele ela nós vós eles elas você vocês me te lhe isso isto aquilo esse essa este esta aqui ali lá
mas ou nem já não sim tá tão muito mais menos bem só também então como quando onde porque qual quem
ser estar ter vai vou foi era tem ao à às aos the and to of a an fazer faz feito precisa precisar saber sabem
olha olhe ver vê pegar colocar tudo outro outra cara depois desse dessa deste desta aparecendo coisa jeito""".split())

def _norm(t):
    t = unicodedata.normalize("NFKD", t.lower()); t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", t)

def config():
    return json.load(open("cena.json")) if os.path.exists("cena.json") else {}

def cfg(nome, padrao):
    """número/valor do lugar: cena.json -> "geometria" -> nome; senão o padrão do script"""
    return config().get("geometria", {}).get(nome, padrao)

def palavras():
    d = json.load(open("transcricao.json"))
    if isinstance(d, dict): d = d.get("words", d.get("segments", []))
    ws = [w for s in d for w in s["w"]] if d and isinstance(d[0].get("w"), list) else d
    troca = {_norm(k): v for k, v in config().get("trocas", {}).items()}
    out = []
    for w in ws:
        t = w["w"].strip()
        n = _norm(t)
        if n in troca:   # mantém a pontuação original
            t = re.sub(r"^[\w\-À-ÿ]+", troca[n], t) if re.match(r"^[\w\-À-ÿ]+", t) else troca[n]
        out.append({"t": t, "s": float(w["s"]), "e": float(w["e"]), "chave": False})
    return out

def frases(max_palavras=None, pausa=0.3):
    c = config()
    mx = max_palavras or c.get("max_palavras", 8)
    ws = palavras()
    fr, cur = [], []
    for w in ws:
        if cur:
            fim = re.search(r"[.!?]$", cur[-1]["t"]); virg = re.search(r"[,;:]$", cur[-1]["t"])
            if w["s"] - cur[-1]["e"] > pausa or fim or (virg and len(cur) >= 3):
                fr.append(cur); cur = []
        cur.append(w)
    if cur: fr.append(cur)
    out = []
    for w in ws:
        t = w["w"].strip()
        n = _norm(t)
        if n in troca:   # mantém a pontuação original
            t = re.sub(r"^[\w\-À-ÿ]+", troca[n], t) if re.match(r"^[\w\-À-ÿ]+", t) else troca[n]
        out.append({"t": t, "s": float(w["s"]), "e": float(w["e"]), "chave": False})
    return out

def frases(max_palavras=None, pausa=0.3):
    c = config()
    mx = max_palavras or c.get("max_palavras", 8)
    ws = palavras()
    fr, cur = [], []
    for w in ws:
        if cur:
            fim = re.search(r"[.!?]$", cur[-1]["t"]); virg = re.search(r"[,;:]$", cur[-1]["t"])
            if w["s"] - cur[-1]["e"] > pausa or fim or (virg and len(cur) >= 3):
                fr.append(cur); cur = []
        cur.append(w)
    if cur: fr.append(cur)
    # pedacinhos (1-2 palavras) juntam com a vizinha
    j = 0
    while j < len(fr):
        f = fr[j]
        if len(f) <= 2 and len(fr) > 1:
            fim = re.search(r"[.!?]$", f[-1]["t"])
            if j + 1 < len(fr) and not fim and len(f) + len(fr[j + 1]) <= mx + 1:
                fr[j + 1] = f + fr[j + 1]; del fr[j]; continue
            if j > 0 and len(f) + len(fr[j - 1]) <= mx + 1 and not re.search(r"[.!?]$", fr[j - 1][-1]["t"]) or (j > 0 and fim and len(f) == 1):
                fr[j - 1] = fr[j - 1] + f; del fr[j]; continue
        j += 1
    out = []
    for f in fr:   # frase comprida demais: parte no meio (de preferência numa vírgula)
        while len(f) > mx:
            corte = [i for i in range(2, len(f) - 1) if re.search(r"[,;:]$", f[i - 1]["t"])]
            i = min(corte, key=lambda i: abs(i - len(f) / 2)) if corte else (len(f) + 1) // 2
            out.append(f[:i]); f = f[i:]
        out.append(f)
    fr = out
    # conectivo solto no fim ("... de fazer e") passa pra frase seguinte
    for j in range(len(fr) - 1):
        while len(fr[j]) > 1 and _norm(fr[j][-1]["t"]) in {"e", "mas", "que", "o", "a", "de", "do", "da", "pra", "um", "uma", "no", "na"} \
                and not re.search(r"[,.!?;:]$", fr[j][-1]["t"]):
            fr[j + 1].insert(0, fr[j].pop())
    dest = {_norm(x) for x in c.get("destaques", [])}
    for f in fr:
        if dest:
            for w in f: w["chave"] = _norm(w["t"]) in dest
        else:   # automática: a palavra "de conteúdo" mais longa da frase
            cand = [w for w in f if _norm(w["t"]) not in PARADAS and len(_norm(w["t"])) >= 4]
            if cand: max(cand, key=lambda w: (len(_norm(w["t"])), w["s"]))["chave"] = True
    return fr

def texto(f, maiusc=True):
    s = " ".join(w["t"] for w in f)
    return s.upper() if maiusc else s

def linhas(f, max_chars=14):
    """quebra uma frase em linhas curtas (a palavra-chave sempre sozinha na linha dela)"""
    out, cur = [], []
    for w in f:
        if w["chave"]:
            if cur: out.append(cur); cur = []
            out.append([w]); continue
        if cur and len(" ".join(x["t"] for x in cur + [w])) > max_chars:
            out.append(cur); cur = []
        cur.append(w)
    if cur: out.append(cur)
    return out

if __name__ == "__main__":
    for f in frases():
        print(f"{f[0]['s']:6.2f}  " + " ".join(("*" + w["t"].upper() + "*") if w["chave"] else w["t"] for w in f))
