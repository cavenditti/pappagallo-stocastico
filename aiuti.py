"""Grafici e piccole utilità di testo per il notebook.

Qui non c'è machine learning: tutto il codice interessante (probabilità,
campionamento, n-grammi, backprop) sta nel notebook, in bella vista.
I grafici restituiscono la figura: in marimo basta metterla come ultima espressione.
"""
from __future__ import annotations

import html
import re
from collections import Counter

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

from sala import risposta

# --- colori: uno per "chi parla", sempre lo stesso in tutti i grafici ---------
SALA = "#2a78d6"     # blu: la sala
MODELLO = "#eb6834"  # arancio: il modello
DOPO = "#1baf7a"     # verde acqua: il modello dopo aver ascoltato la sala
COLORI = {"Sala": SALA, "Modello": MODELLO, "Modello prima": MODELLO, "Modello dopo": DOPO}

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
EVIDENZA = "#cde2fb"  # sfondo per le parole scelte dalla sala


def stile() -> None:
    """Stile pensato per il proiettore: testo grande, griglia leggera, sfondo chiaro."""
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "sans-serif", "font.size": 14,
        "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
        "axes.titlesize": 17, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.titlepad": 14, "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": MUTED, "ytick.color": INK, "ytick.labelsize": 15,
        "axes.grid": True, "axes.grid.axis": "x", "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.axisbelow": True, "legend.frameon": False, "legend.fontsize": 14,
        "figure.dpi": 110,
    })


# --- parole -------------------------------------------------------------------
# Una "parola" per noi: lettere/cifre (con l'eventuale apostrofo di "l'", "dell'")
# oppure un singolo segno di punteggiatura.
PAROLA = re.compile(r"\w+['’]?|[^\w\s]", re.UNICODE)


def parole(testo: str, minuscole: bool = True) -> list[str]:
    if minuscole:
        testo = testo.lower()
    return [p.replace("’", "'") for p in PAROLA.findall(testo)]


def prima_parola(testo: str, minuscole: bool = True) -> str | None:
    p = parole(testo, minuscole)
    return p[0] if p else None


def unisci(lista: list[str]) -> str:
    """["il", "traffico", ",", "l'", "acqua"] -> "il traffico, l'acqua"."""
    testo = " ".join(lista)
    testo = re.sub(r" ([.,;:!?»)])", r"\1", testo)
    return testo.replace("' ", "'")


def elenca_voti(voti) -> list[str]:
    """Ogni voto come testo intero ("si blocca" resta "si blocca").

    Accetta la lista che arriva dal sito, {"impazzisce": 14, "si blocca": 8}
    oppure una stringa "impazzisce, aumenta, si blocca, ...".
    """
    if isinstance(voti, dict):
        return [voce.strip() for voce, n in voti.items() for _ in range(int(n))]
    if isinstance(voti, str):
        voti = re.split(r"[,;\n]+", voti)
    return [voce.strip() for voce in voti if voce.strip()]


def leggi_voti(voti) -> Counter:
    """Conta solo la prima parola: "si blocca" vale "si". È il confronto onesto con
    il modello, che sceglie un token alla volta."""
    return Counter(p for p in map(prima_parola, elenca_voti(voti)) if p)


def leggi_risposte(voti) -> Counter:
    """Conta le risposte intere (da una a tre parole), come le ha scritte la sala."""
    return Counter(r for r in map(risposta, elenca_voti(voti)) if r)


def risposta_del_modello(continuazione: str) -> str | None:
    """La "risposta" del modello: la sua continuazione fino alla prima pausa, massimo tre parole."""
    return risposta(re.split(r"[.,;:!?\n]", continuazione.strip(), maxsplit=1)[0])


def percento(p: float) -> str:
    if p >= 0.095:
        return f"{p:.0%}"
    if p >= 0.001:
        return f"{p:.1%}".replace(".", ",")
    return f"{p:.0e}".replace("e-0", "e-")


def numero(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def distribuzione(conteggi: Counter) -> dict[str, float]:
    totale = sum(conteggi.values()) or 1
    return {k: v / totale for k, v in conteggi.most_common()}


def accordo(p: dict[str, float], q: dict[str, float]) -> float:
    """Sovrapposizione fra due distribuzioni: somma dei minimi (1 = identiche, 0 = disgiunte)."""
    return sum(min(p.get(w, 0.0), q.get(w, 0.0)) for w in set(p) | set(q))


def visibile(token: str) -> str:
    """Rende visibile lo spazio iniziale dei token: " traffico" -> "␣traffico"."""
    return token.replace(" ", "␣").replace("\n", "⏎") or "∅"


# --- grafici ------------------------------------------------------------------
def _etichette(ax, barre, valori, soglia=0.01):
    for barra, v in zip(barre, valori):
        if v >= soglia:
            ax.text(barra.get_width() + 0.004, barra.get_y() + barra.get_height() / 2,
                    percento(v),
                    va="center", fontsize=12, color=INK2)


def grafico_token(coppie: list[tuple[str, float]], titolo: str, xmax: float | None = None):
    """Le probabilità grezze dei prossimi token, così come le vede il modello."""
    etichette = [visibile(t) for t, _ in coppie]
    valori = [p for _, p in coppie]
    fig, ax = plt.subplots(figsize=(11, 1.2 + 0.42 * len(coppie)))
    barre = ax.barh(range(len(coppie)), valori, height=0.72, color=MODELLO)
    _etichette(ax, barre, valori, soglia=0.0)
    ax.set_yticks(range(len(coppie)), etichette, fontfamily="monospace")
    ax.invert_yaxis()
    ax.set_xlim(0, xmax or max(valori) * 1.18)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_title(titolo)
    plt.tight_layout()
    plt.close(fig)
    return fig


def confronta(serie: dict[str, dict[str, float]], titolo: str, top: int = 10):
    """Barre orizzontali raggruppate: stesse parole, una barra per ogni 'votante'."""
    punteggio: Counter = Counter()
    for dist in serie.values():
        for w, p in dist.items():
            punteggio[w] = max(punteggio[w], p)
    voci = [w for w, _ in punteggio.most_common(top)]
    n = len(serie)
    h = 0.8 / n
    fig, ax = plt.subplots(figsize=(11, 1.4 + 0.3 * len(voci) * (n + 0.6)))
    massimo = 0.0
    for i, (nome, dist) in enumerate(serie.items()):
        y = [j + (i - (n - 1) / 2) * h for j in range(len(voci))]
        valori = [dist.get(w, 0.0) for w in voci]
        massimo = max(massimo, *valori)
        barre = ax.barh(y, valori, height=h * 0.86, color=COLORI.get(nome, INK2), label=nome)
        _etichette(ax, barre, valori)
    ax.set_yticks(range(len(voci)), voci)
    ax.invert_yaxis()
    ax.set_xlim(0, massimo * 1.2)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_title(titolo)
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.close(fig)
    return fig


def grafico_perplessita(righe: list[tuple[str, str, float]], titolo: str):
    """Un punto per frase, una riga per gruppo; la tacca nera è la media geometrica."""
    import math
    import random

    gruppi = list(dict.fromkeys(g for _, g, _ in righe))
    fig, ax = plt.subplots(figsize=(11, 1.6 + 0.9 * len(gruppi)))
    rng = random.Random(0)
    for i, g in enumerate(gruppi):
        valori = [ppl for _, gg, ppl in righe if gg == g]
        ax.scatter(valori, [i + rng.uniform(-0.12, 0.12) for _ in valori], s=90, color=SALA,
                   edgecolor=SURFACE, linewidth=2, zorder=3)
        media = math.exp(sum(math.log(v) for v in valori) / len(valori))
        ax.plot([media, media], [i - 0.3, i + 0.3], color=INK, linewidth=2.5, zorder=4)
        ax.text(media, i - 0.36, numero(media), ha="center", va="bottom",
                fontsize=13, color=INK)
    ax.set_xscale("log")
    ax.set_yticks(range(len(gruppi)), gruppi)
    ax.set_ylim(len(gruppi) - 0.5, -0.7)
    ax.set_xlabel("perplessità del modello (scala log): più è alta, più la frase lo sorprende")
    ax.set_title(titolo)
    plt.tight_layout()
    plt.close(fig)
    return fig


def grafico_loss(perdite: list[float]):
    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.plot(range(1, len(perdite) + 1), perdite, color=DOPO, linewidth=2.2, marker="o", markersize=7)
    ax.set_xlabel("passo di backpropagation")
    ax.set_ylabel("loss")
    ax.grid(axis="y")
    ax.set_title("Il modello impara la sala: la loss scende")
    plt.tight_layout()
    plt.close(fig)
    return fig


def frase_evidenziata(lista: list[str], fonti: list[str], n_inizio: int) -> str:
    """HTML: le parole arrivate dalla sala con lo sfondo evidenziato."""
    pezzi = []
    for i, w in enumerate(lista):
        w_html = html.escape(w, quote=False)
        if i >= n_inizio and fonti[i - n_inizio] == "sala":
            w_html = (f'<span style="background:{EVIDENZA};color:{INK};border-radius:4px;'
                      f'padding:1px 5px;font-weight:600">{w_html}</span>')
        pezzi.append(w_html)
    testo = " ".join(pezzi)
    testo = re.sub(r" ([.,;:!?»)])", r"\1", testo)
    return testo.replace("' ", "'")
