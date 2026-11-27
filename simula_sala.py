"""Una sala finta per la prova generale: N telefoni che votano e scrivono catene.

    uv run python simula_sala.py              # reagisce a quello che apri dal notebook
    uv run python simula_sala.py --pilota     # fa tutto da solo: votazioni, catene, fine

Parla con il server esattamente come i telefoni veri (stesse API).
"""
from __future__ import annotations

import argparse
import json
import random
import secrets
import threading
import time
import urllib.error
import urllib.request

from sala import PORTA, Sala

BASE = f"http://127.0.0.1:{PORTA}"  # SALA_PORTA per provarlo su un altro server
_apri = urllib.request.build_opener(urllib.request.ProxyHandler({})).open

# Cosa "pensa" la sala finta per ogni prompt (pesi = quanto è popolare la risposta, da una a tre parole).
RISPOSTE = {
    "A Roma, quando piove, il traffico": {"impazzisce": 12, "si blocca": 8, "aumenta": 7, "va in tilt": 5,
                                          "è un incubo": 4, "peggiora": 3, "esplode": 1, "scompare": 1},
    "Il codice funzionava ieri sera, ma stamattina": {"non funziona più": 11, "non parte": 8, "è esploso": 5,
                                                      "dà errore": 4, "pandas è cambiato": 3},
    "La cosa più bella di Python è": {"la sintassi": 9, "la community": 7, "la semplicità": 6,
                                      "l'indentazione": 4, "pandas": 3, "che è gratis": 3},
    "Mia nonna dice sempre che la pizza": {"è sacra": 8, "con l'ananas": 6, "va mangiata calda": 4,
                                           "fa ingrassare": 3, "napoletana è meglio": 2},
    "Dopo la terza birra, ogni data scientist": {"diventa filosofo": 7, "parla di LLM": 6, "è in overfitting": 4,
                                                 "balla": 3, "crede nel deep learning": 2},
}
# Un piccolo "cervello" a bigrammi per le catene: localmente sensato, globalmente assurdo.
FRASI = [
    "traffico impazzisce la mamma di Guido mangia sempre il gelato al pistacchio di Bronte",
    "traffico intenso come il caffè della macchinetta rotta da tre anni luce spenta",
    "traffico romano antico come il Colosseo è pieno di turisti tedeschi che bevono birra",
    "il gatto dorme sul divano di casa mia quando piove forte e tuona",
    "la birra artigianale costa troppo ma è buona come il pane di mia nonna",
    "il modello non converge perché il learning rate è troppo alto per il gatto",
]
SUCCESSIVI: dict[str, list[str]] = {}
for _f in FRASI:
    _p = _f.lower().split()
    for _a, _b in zip(_p, _p[1:]):
        SUCCESSIVI.setdefault(_a, []).append(_b)
TUTTE = sorted({w for f in FRASI for w in f.lower().split()})
NOMI = ["Giulia", "Marco", "Sara", "Luca", "Chiara", "Matteo", "Elena", "Davide", "Francesca", "Andrea",
        "Valentina", "Simone", "Martina", "Lorenzo", "Alessia"]


def api(percorso: str, dati: dict | None = None):
    corpo = json.dumps(dati).encode() if dati is not None else None
    req = urllib.request.Request(BASE + percorso, data=corpo, method="POST" if dati is not None else "GET",
                                 headers={"Content-Type": "application/json"})
    try:
        with _apri(req, timeout=5) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"errore": e.code}
    except OSError:
        return None


def telefono(n: int, stop: threading.Event, ritmo: float) -> None:
    d = secrets.token_hex(12)
    votati: set[str] = set()
    rng = random.Random(n)
    api("/api/nome", {"d": d, "nome": f"{NOMI[n % len(NOMI)]} {'BRSTV'[n // len(NOMI) % 5]}."})
    while not stop.is_set():
        s = api(f"/api/stato?d={d}")
        if s and s.get("fase") == "vota" and s["prompt"] not in votati:
            scelte = RISPOSTE.get(s["prompt"], {"boh": 1})
            time.sleep(rng.uniform(0.2, 3) * ritmo)
            api("/api/voto", {"d": d, "prompt": s["prompt"],
                              "testo": rng.choices(list(scelte), weights=list(scelte.values()))[0]})
            votati.add(s["prompt"])
        elif s and s.get("fase") == "catena" and not s.get("finite"):
            t = api("/api/catena/turno", {"d": d})
            if t and "catena" in t:
                time.sleep(rng.uniform(0.3, 2.5) * ritmo)
                ultima = t["visibili"][-1].lower()
                parola = rng.choice(SUCCESSIVI.get(ultima) or TUTTE)
                api("/api/catena/parola", {"d": d, "catena": t["catena"], "testo": parola})
        time.sleep(rng.uniform(0.8, 1.6) * ritmo)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persone", type=int, default=30)
    ap.add_argument("--pilota", action="store_true", help="apre e chiude lui le fasi (prova generale completa)")
    ap.add_argument("--ritmo", type=float, default=1.0, help="<1 per una sala più veloce")
    args = ap.parse_args()

    sala = Sala(BASE)
    if not sala.online():
        raise SystemExit("Il server non risponde: avvia prima `uv run python server.py`.")
    stop = threading.Event()
    for i in range(args.persone):
        threading.Thread(target=telefono, args=(i, stop, args.ritmo), daemon=True).start()
    print(f"📱 {args.persone} telefoni finti collegati.")

    if not args.pilota:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return

    for prompt in list(RISPOSTE)[:2]:
        sala.fase("vota", prompt=prompt)
        print(f"🗳️  votazione aperta: {prompt}…")
        time.sleep(6 * args.ritmo)
    sala.avvia_catene("traffico", n=8, lunghezza=12)
    print("🔗 catene avviate")
    for _ in range(600):
        dati = sala.dati()
        fatte = sum(len(c["parole"]) for c in dati["catene"])
        totale = sum(c["lunghezza"] for c in dati["catene"])
        print(f"\r   {fatte}/{totale} parole", end="", flush=True)
        if fatte >= totale:
            break
        time.sleep(0.5)
    sala.fase("attesa")
    stop.set()
    dati = sala.dati()
    print(f"\n✅ fatto: {dati['persone']} persone, {sum(len(v) for v in dati['voti'].values())} voti, "
          f"{len(dati['catene'])} catene")
    for c in dati["catene"]:
        print(f"   [memoria {c['memoria']}] {' '.join(c['parole'])}")


if __name__ == "__main__":
    main()
