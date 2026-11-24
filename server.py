"""Il sito della sala: i telefoni del pubblico votano e scrivono le catene di Markov.

    uv run python server.py

Ascolta su tutte le interfacce (porta 8000) e stampa l'indirizzo e un QR code.
Non serve Internet: basta che telefoni e portatile siano sulla stessa rete
(un router da viaggio o un hotspot). Lo stato viene salvato in sala.json a ogni
modifica, quindi un riavvio non perde niente.
"""
from __future__ import annotations

import json
import random
import re
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from sala import PORTA, url_pubblico

QUI = Path(__file__).parent
FILE_STATO = QUI / "sala.json"
PAGINA = QUI / "sito" / "index.html"
DURATA_TURNO = 60  # secondi per scrivere la propria parola in una catena
PAROLA = re.compile(r"\w+['’]?|[^\w\s]", re.UNICODE)
ID_VALIDO = re.compile(r"[0-9a-f]{8,64}")

blocco = threading.Lock()
visti: dict[str, float] = {}  # dispositivo -> ultima volta che ha chiesto lo stato (solo in memoria)


def stato_vuoto() -> dict:
    return {"fase": "attesa", "prompt": None, "voti": {}, "catene": []}


def carica() -> dict:
    try:
        return {**stato_vuoto(), **json.loads(FILE_STATO.read_text())}
    except (OSError, ValueError):
        return stato_vuoto()


S = carica()


def salva() -> None:
    provvisorio = FILE_STATO.with_suffix(".tmp")
    provvisorio.write_text(json.dumps(S, ensure_ascii=False, indent=1))
    provvisorio.replace(FILE_STATO)


def prima_parola(testo: str) -> str | None:
    trovate = PAROLA.findall(testo.strip())
    return trovate[0].replace("’", "'")[:30] if trovate else None


def controlla_id(d: str) -> str:
    if not ID_VALIDO.fullmatch(d or ""):
        raise HTTPException(400, "Identificativo del telefono non valido: ricarica la pagina.")
    return d


def solo_palco(request: Request) -> None:
    if request.client is None or request.client.host not in {"127.0.0.1", "::1"}:
        raise HTTPException(403, "Solo il palco può farlo 😉")


def catene_finite() -> bool:
    return bool(S["catene"]) and all(len(c["parole"]) >= c["lunghezza"] for c in S["catene"])


app = FastAPI(title="Il pappagallo stoca**ico", docs_url=None, redoc_url=None)


@app.get("/")
def pagina():
    return FileResponse(PAGINA, headers={"Cache-Control": "no-store"})


@app.get("/api/ping")
def ping():
    return {"ok": True}


# --- il pubblico -------------------------------------------------------------
@app.get("/api/stato")
def stato(d: str):
    d = controlla_id(d)
    with blocco:
        visti[d] = time.time()
        if S["fase"] == "vota":
            return {"fase": "vota", "prompt": S["prompt"], "mio_voto": S["voti"].get(S["prompt"], {}).get(d)}
        if S["fase"] == "catena":
            mie = sum(c["autori"].count(d) for c in S["catene"])
            return {"fase": "catena", "finite": catene_finite(), "mie_parole": mie}
        return {"fase": "attesa"}


class Voto(BaseModel):
    d: str
    testo: str


@app.post("/api/voto")
def vota(v: Voto):
    d = controlla_id(v.d)
    testo = " ".join(v.testo.split())[:40]
    if not prima_parola(testo):
        raise HTTPException(400, "Scrivi almeno una parola.")
    with blocco:
        if S["fase"] != "vota":
            raise HTTPException(409, "La votazione è chiusa.")
        S["voti"].setdefault(S["prompt"], {})[d] = testo  # un voto per telefono, si può cambiare
        salva()
    return {"ok": True, "mio_voto": testo}


class Richiesta(BaseModel):
    d: str


@app.post("/api/catena/turno")
def chiedi_turno(r: Richiesta):
    """Assegna al telefono una catena libera e gli mostra solo le ultime parole."""
    d = controlla_id(r.d)
    with blocco:
        if S["fase"] != "catena":
            raise HTTPException(409, "Le catene non sono aperte.")
        ora = time.time()
        for c in S["catene"]:
            if c["turno"] and c["turno"]["scade"] < ora and c["turno"]["d"] != d:
                c["turno"] = None
        catena = next((c for c in S["catene"] if c["turno"] and c["turno"]["d"] == d), None)
        if catena is None:
            libere = [c for c in S["catene"]
                      if len(c["parole"]) < c["lunghezza"] and not c["turno"] and c["autori"][-1] != d]
            if not libere:
                return {"attendi": True, "finite": catene_finite()}
            random.shuffle(libere)
            # prima le catene dove non hai ancora scritto, poi le più corte
            catena = min(libere, key=lambda c: (d in c["autori"], len(c["parole"])))
            catena["turno"] = {"d": d, "scade": ora + DURATA_TURNO}
            salva()
        return {
            "catena": catena["id"],
            "visibili": catena["parole"][-catena["memoria"]:],
            "memoria": catena["memoria"],
            "posizione": len(catena["parole"]) + 1,
            "lunghezza": catena["lunghezza"],
            "scade_tra": max(0, round(catena["turno"]["scade"] - ora)),
        }


class Aggiunta(BaseModel):
    d: str
    catena: int
    testo: str


@app.post("/api/catena/parola")
def aggiungi_parola(a: Aggiunta):
    d = controlla_id(a.d)
    parola = prima_parola(a.testo)
    if not parola:
        raise HTTPException(400, "Scrivi una parola.")
    with blocco:
        catena = next((c for c in S["catene"] if c["id"] == a.catena), None)
        if catena is None or not catena["turno"] or catena["turno"]["d"] != d:
            raise HTTPException(409, "Il tuo turno è scaduto: chiedine un altro.")
        catena["parole"].append(parola)
        catena["autori"].append(d)
        catena["turno"] = None
        salva()
        return {"ok": True, "parola": parola, "mie_parole": sum(c["autori"].count(d) for c in S["catene"])}


# --- il palco (solo da questo portatile) ------------------------------------
class Fase(BaseModel):
    fase: str
    prompt: str | None = None


@app.post("/api/admin/fase")
def cambia_fase(f: Fase, request: Request):
    solo_palco(request)
    if f.fase not in {"attesa", "vota", "catena"} or (f.fase == "vota" and not f.prompt):
        raise HTTPException(400, "Fase non valida.")
    with blocco:
        S["fase"], S["prompt"] = f.fase, f.prompt if f.fase == "vota" else S["prompt"]
        salva()
    return {"ok": True}


class NuoveCatene(BaseModel):
    inizio: str = "traffico"
    n: int = 8
    lunghezza: int = 12


@app.post("/api/admin/catene")
def nuove_catene(nc: NuoveCatene, request: Request):
    solo_palco(request)
    inizio = [p.replace("’", "'") for p in PAROLA.findall(nc.inizio)] or ["traffico"]
    with blocco:
        # Se le catene c'erano già (doppio clic?), non si buttano: finiscono nell'archivio in sala.json.
        if any(len(c["parole"]) > 1 for c in S["catene"]):
            S.setdefault("archivio_catene", []).append(S["catene"])
        S["catene"] = [
            {"id": i, "memoria": 1 if i % 2 == 0 else 2, "lunghezza": max(nc.lunghezza, len(inizio) + 1),
             "parole": list(inizio), "autori": ["palco"] * len(inizio), "turno": None}
            for i in range(max(1, min(nc.n, 40)))
        ]
        S["fase"] = "catena"
        salva()
    return {"ok": True, "catene": len(S["catene"])}


@app.get("/api/admin/dati")
def dati(request: Request):
    solo_palco(request)
    with blocco:
        ora = time.time()
        persone = {d for voti in S["voti"].values() for d in voti}
        persone |= {d for c in S["catene"] for d in c["autori"] if d != "palco"}
        return {
            "fase": S["fase"],
            "prompt": S["prompt"],
            "voti": {p: list(v.values()) for p, v in S["voti"].items()},
            "catene": [{"id": c["id"], "memoria": c["memoria"], "lunghezza": c["lunghezza"],
                        "parole": c["parole"], "occupata": bool(c["turno"])} for c in S["catene"]],
            "persone": len(persone),
            "connessi": sum(1 for t in visti.values() if ora - t < 10),
        }


@app.post("/api/admin/azzera")
def azzera(request: Request):
    solo_palco(request)
    with blocco:
        if FILE_STATO.exists():
            FILE_STATO.replace(FILE_STATO.with_name(f"sala-backup-{time.strftime('%Y%m%d-%H%M%S')}.json"))
        S.clear()
        S.update(stato_vuoto())
        salva()
    return {"ok": True}


if __name__ == "__main__":
    import segno

    url = url_pubblico()
    print(f"\n🦜  Il sito della sala è su  {url}\n")
    segno.make(url, error="m").terminal(compact=True)
    print("\n(il palco, cioè il notebook, parla con http://127.0.0.1:%d)\n" % PORTA)
    uvicorn.run(app, host="0.0.0.0", port=PORTA, log_level="warning")
