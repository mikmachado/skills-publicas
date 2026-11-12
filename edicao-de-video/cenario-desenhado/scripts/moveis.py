"""Assentos desenhados embaixo da Mica (todos presos à linha do assento sy e ao centro cx).
Cada função devolve uma lista de partes na mesma ordem lógica (encosto, braços, assento, frente, pés, detalhes)
para a transformação de um no outro ficar natural."""
from desenho import *


def cadeira(cx, sy):
    """poltrona laranja-clara com braços rosa, contorno verde"""
    L = 300
    return [
        parte(ret(cx - L + 20, sy - 470, cx + L - 20, sy + 20, 120), LARANJA_C, VERDE_E, 11),      # encosto (claro: esconde falhas do tênis)
        parte(ret(cx - L - 70, sy - 170, cx - L + 60, sy + 140, 60), ROSA, VERDE_E, 11),           # braço esq
        parte(ret(cx + L - 60, sy - 170, cx + L + 70, sy + 140, 60), ROSA, VERDE_E, 11),           # braço dir
        parte(ret(cx - L + 30, sy - 40, cx + L - 30, sy + 70, 40), BEGE, VERDE_E, 10),             # assento
        parte(ret(cx - L - 50, sy + 90, cx + L + 50, sy + 230, 30), LARANJA, VERDE_E, 11),         # frente/base
        parte(poli(cx - L - 20, sy + 220, cx - L + 20, sy + 220, cx - L + 0, sy + 360, cx - L - 30, sy + 360), VERDE, VERDE_E, 9),
        parte(poli(cx + L - 20, sy + 220, cx + L + 20, sy + 220, cx + L + 30, sy + 360, cx + L - 0, sy + 360), VERDE, VERDE_E, 9),
        parte(poli(cx - 200, sy - 380, cx - 200, sy - 60), None, ROSA_E, 8, aberta=True),           # costuras do encosto
        parte(poli(cx + 200, sy - 380, cx + 200, sy - 60), None, ROSA_E, 8, aberta=True),
        parte(elipse(cx - 120, sy + 160, 16, 16), ROSA, VERDE_E, 6),                               # botões
        parte(elipse(cx + 120, sy + 160, 16, 16), ROSA, VERDE_E, 6),
    ]


def sofa(cx, sy):
    """sofá bege claro (atrás das pernas) com frente verde e almofadas laranja listradas de rosa"""
    return [
        parte(ret(-60, sy - 300, 1140, sy + 40, 70), BEGE, VERDE, 12),                            # encosto (claro)
        parte(ret(-80, sy - 120, 90, sy + 300, 50), VERDE_C, LARANJA, 12),                          # braço esq
        parte(ret(990, sy - 120, 1160, sy + 300, 50), VERDE_C, LARANJA, 12),                        # braço dir
        parte(ret(60, sy - 20, 1020, sy + 90, 30), (252, 242, 226), VERDE, 11),                  # assento (claro)
        parte(ret(-40, sy + 90, 1120, sy + 330, 30), VERDE, LARANJA, 12),                           # frente
        parte(poli(110, sy + 320, 170, sy + 320, 160, sy + 420, 120, sy + 420), LARANJA, VERDE_E, 9),
        parte(poli(910, sy + 320, 970, sy + 320, 960, sy + 420, 920, sy + 420), LARANJA, VERDE_E, 9),
        parte(ret(70, sy - 230, 300, sy - 10, 40), LARANJA_C, LARANJA, 10),                         # almofada esq
        parte(ret(850, sy - 230, 1080, sy - 10, 40), LARANJA_C, LARANJA, 10),                       # almofada dir
        parte(poli(150, sy - 220, 150, sy - 20), None, ROSA_E, 9, aberta=True),                     # listras
        parte(poli(1000, sy - 220, 1000, sy - 20), None, ROSA_E, 9, aberta=True),
        parte(poli(220, sy - 220, 220, sy - 20), None, ROSA_E, 9, aberta=True),
        parte(poli(930, sy - 220, 930, sy - 20), None, ROSA_E, 9, aberta=True),
    ]


def banquinho(cx, sy):
    """banquinho redondo rosa, pernas verdes"""
    return [
        parte(elipse(cx, sy + 5, 250, 60), ROSA, LARANJA, 11),                                      # tampo (no lugar do encosto)
        parte(poli(cx - 200, sy + 50, cx - 160, sy + 50, cx - 250, sy + 440, cx - 290, sy + 440), VERDE, VERDE_E, 9),
        parte(poli(cx + 160, sy + 50, cx + 200, sy + 50, cx + 290, sy + 440, cx + 250, sy + 440), VERDE, VERDE_E, 9),
        parte(ret(cx - 245, sy + 5, cx + 245, sy + 60, 26), ROSA_E, LARANJA, 10),                    # aro
        parte(poli(cx - 20, sy + 60, cx + 20, sy + 60, cx + 16, sy + 420, cx - 16, sy + 420), VERDE, VERDE_E, 9),
        parte(ret(cx - 240, sy + 250, cx + 240, sy + 275, 10), LARANJA, VERDE_E, 8),                 # travessa
        parte(elipse(cx - 270, sy + 445, 34, 12), LARANJA, VERDE_E, 6),
        parte(poli(cx - 90, sy - 10, cx + 90, sy - 10), None, BRANCO, 7, aberta=True),               # brilho
        parte(poli(cx - 150, sy + 30, cx - 60, sy + 34), None, BRANCO, 7, aberta=True),
        parte(elipse(cx + 270, sy + 445, 34, 12), LARANJA, VERDE_E, 6),
        parte(elipse(cx, sy + 425, 30, 10), LARANJA, VERDE_E, 6),
    ]


def topo_predio(cx, sy, alto=1600):
    """borda do terraço de um prédio bege com janelas — a Mica senta na mureta"""
    x0, x1 = cx - 430, cx + 430
    partes = [
        parte(ret(x0, sy + 60, x1, sy + alto), BEGE, LARANJA, 12),                                  # fachada
        parte(ret(x0 - 40, sy - 10, x0 + 60, sy + 70, 8), ROSA, LARANJA, 10),                       # pilar esq
        parte(ret(x1 - 60, sy - 10, x1 + 40, sy + 70, 8), ROSA, LARANJA, 10),                       # pilar dir
        parte(ret(x0 - 40, sy - 10, x1 + 40, sy + 70, 10), ROSA, LARANJA, 11),                      # mureta
        parte(ret(x0 - 20, sy + 70, x1 + 20, sy + 120, 6), ROSA_E, LARANJA, 9),                     # cornija
        parte(ret(x0 + 60, sy + 330, x0 + 140, sy + 380, 6), LARANJA_C, LARANJA, 7),                # toldo
        parte(ret(x1 - 140, sy + 330, x1 - 60, sy + 380, 6), LARANJA_C, LARANJA, 7),
    ]
    # janelas em grade
    for j in range(int((alto - 200) // 230)):
        for i in range(4):
            wx = x0 + 90 + i * 200; wy = sy + 190 + j * 230
            acesa = (i * 7 + j * 3) % 5 == 0
            partes.append(parte(ret(wx, wy, wx + 120, wy + 150, 10), (255, 226, 140) if acesa else CEU_C, VERDE_E, 8))
    return partes
