"""Il sito della sala: i telefoni del pubblico votano e scrivono le catene di Markov.

    uv run python server.py

Ascolta su tutte le interfacce (porta 8000) e stampa l'indirizzo e un QR code.
In modo "online" (quello previsto) accende anche Tailscale Funnel, che porta il sito su
Internet: i telefoni usano i loro dati, niente Wi-Fi. Si spegne insieme al server.
Con il router o l'hotspot invece Internet non serve: basta una rete comune.
Lo stato viene salvato in sala.json a ogni modifica, quindi un riavvio non perde niente.
"""
from __future__ import annotations

import json
import os
import random
import re
import secrets
import subprocess
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from sala import FILE_PALCO, MAX_PAROLE_RISPOSTA, PORTA, modo, risposta, tailscale_cli, url_da_mostrare

QUI = Path(__file__).parent
FILE_STATO = QUI / "sala.json"
PAGINA = QUI / "sito" / "index.html"
DURATA_TURNO = 60  # secondi per scrivere la propria parola in una catena
# Se le catene libere ti mostrerebbero solo parole che hai già visto, aspetti al massimo
# così tanto che qualcuno ne finisca un'altra: avrà un'ultima parola nuova per te.
ATTESA_NOVITA = 12  # secondi
PAROLA = re.compile(r"\w+['’]?|[^\w\s]", re.UNICODE)
ID_VALIDO = re.compile(r"[0-9a-f]{8,64}")
# Chi parla da 127.0.0.1 non è per forza il palco: con Funnel anche Internet arriva da lì.
# Per questo i comandi del palco vogliono un codice segreto, nuovo a ogni avvio, che il
# notebook legge dal file .palco su questo portatile.
CODICE_PALCO = secrets.token_urlsafe(24)
FILE_PALCO.write_text(CODICE_PALCO)
os.chmod(FILE_PALCO, 0o600)
SERVER_ID = secrets.token_hex(8)  # per riconoscere questo server quando lo si chiama da fuori
MAX_NOME = 24  # caratteri: un nome o un soprannome, per la classifica dei Pappagalli d'oro

blocco = threading.Lock()
visti: dict[str, float] = {}  # dispositivo -> ultima volta che ha chiesto lo stato (solo in memoria)
attese: dict[str, float] = {}  # dispositivo -> da quando aspetta una catena con parole nuove (solo in memoria)
in_gioco: dict[str, float] = {}  # dispositivo -> ultima volta che ha chiesto un turno o scritto (solo in memoria)


def stato_vuoto() -> dict:
    # "viste": {telefono: parole che ha già visto o scritto nelle catene}, per mostrargliene sempre di nuove
    return {"fase": "attesa", "prompt": None, "voti": {}, "catene": [], "nomi": {}, "viste": {}}


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
    if (request.client is None or request.client.host not in {"127.0.0.1", "::1"}
            or not secrets.compare_digest(request.headers.get("x-palco", ""), CODICE_PALCO)):
        raise HTTPException(403, "Solo il palco può farlo 😉")


def catene_finite() -> bool:
    return bool(S["catene"]) and all(len(c["parole"]) >= c["lunghezza"] for c in S["catene"])


def ricorda_viste(d: str, parole: list[str]) -> None:
    viste = S["viste"].setdefault(d, [])
    for p in parole:
        if p.lower() not in viste:
            viste.append(p.lower())


def gia_viste(catena: dict, viste: set[str]) -> tuple[bool, int]:
    """(niente di nuovo?, quante parole già viste) fra quelle che la catena ti mostrerebbe."""
    visibili = [p.lower() for p in catena["parole"][-catena["memoria"]:]]
    ripetute = sum(p in viste for p in visibili)
    return ripetute == len(visibili), ripetute


def qualcuno_meglio(catena: dict, d: str, ora: float) -> bool:
    """Vale la pena che d aspetti invece di prendere questa catena (che non gli mostra niente di nuovo)?

    Sì se qualcun altro sta scrivendo (presto un'altra catena avrà un'ultima parola nuova per d)
    e c'è chi gioca, libero, a cui questa catena mostrerebbe parole nuove. Altrimenti aspettare
    rallenta e basta: in una sala piccola le ripetizioni non si possono evitare tutte.
    """
    occupati = {c["turno"]["d"] for c in S["catene"] if c["turno"]}
    if not occupati - {d}:
        return False
    return any(p != d and p not in occupati and p != catena["autori"][-1] and ora - t < 30
               and not gia_viste(catena, set(S["viste"].get(p, [])))[0]
               for p, t in in_gioco.items())


app = FastAPI(title="Il pappagallo stoca**ico", docs_url=None, redoc_url=None)
# Font e logo li serve il portatile: in sala i telefoni non hanno Internet.
app.mount("/risorse", StaticFiles(directory=QUI / "sito" / "risorse"), name="risorse")


@app.get("/")
def pagina():
    return FileResponse(PAGINA, headers={"Cache-Control": "no-store"})


@app.get("/api/ping")
def ping():
    return {"ok": True, "server": SERVER_ID}


# --- il pubblico -------------------------------------------------------------
@app.get("/api/stato")
def stato(d: str):
    d = controlla_id(d)
    with blocco:
        visti[d] = time.time()
        nome = S["nomi"].get(d)
        if S["fase"] == "vota":
            return {"fase": "vota", "nome": nome, "prompt": S["prompt"],
                    "mio_voto": S["voti"].get(S["prompt"], {}).get(d)}
        if S["fase"] == "catena":
            mie = sum(c["autori"].count(d) for c in S["catene"])
            return {"fase": "catena", "nome": nome, "finite": catene_finite(), "mie_parole": mie}
        return {"fase": "attesa", "nome": nome}


class Nome(BaseModel):
    d: str
    nome: str


@app.post("/api/nome")
def scegli_nome(n: Nome):
    """Il nome che compare nella classifica dei Pappagalli d'oro (si può cambiare quando si vuole)."""
    d = controlla_id(n.d)
    nome = " ".join("".join(ch for ch in n.nome[:200] if ch.isprintable()).split())[:MAX_NOME].strip()
    if not nome:
        raise HTTPException(400, "Scrivi un nome o un soprannome.")
    with blocco:
        S["nomi"][d] = nome
        salva()
    return {"ok": True, "nome": nome}


class Voto(BaseModel):
    d: str
    testo: str
    prompt: str | None = None  # la frase a cui il telefono sta rispondendo


@app.post("/api/voto")
def vota(v: Voto):
    d = controlla_id(v.d)
    testo = risposta(v.testo[:200])  # da una a tre parole: le altre si tagliano
    if not testo:
        quante = {1: "una", 2: "due", 3: "tre"}.get(MAX_PAROLE_RISPOSTA, str(MAX_PAROLE_RISPOSTA))
        raise HTTPException(400, f"Scrivi da una a {quante} parole.")
    with blocco:
        if S["fase"] != "vota":
            raise HTTPException(409, "La votazione è chiusa.")
        if v.prompt is not None and v.prompt != S["prompt"]:  # la frase è cambiata mentre scrivevi
            raise HTTPException(409, "La frase è cambiata: guarda lo schermo e rispondi alla nuova.")
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
        in_gioco[d] = ora
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
            viste = set(S["viste"].get(d, []))
            # prima le catene che ti mostrano parole nuove (che non hai già visto o scritto),
            # poi quelle dove non hai ancora scritto, poi le più corte
            catena = min(libere, key=lambda c: (*gia_viste(c, viste), d in c["autori"], len(c["parole"])))
            if (gia_viste(catena, viste)[0] and qualcuno_meglio(catena, d, ora)
                    and ora - attese.setdefault(d, ora) < ATTESA_NOVITA):
                # solo parole già viste (tipo la parola iniziale, di nuovo): meglio aspettare un attimo
                # che qualcuno finisca la sua parola, e questa catena la prende chi non l'ha vista
                return {"attendi": True, "finite": False, "nuove": True}
            attese.pop(d, None)
            catena["turno"] = {"d": d, "scade": ora + DURATA_TURNO}
            ricorda_viste(d, catena["parole"][-catena["memoria"]:])
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
        ricorda_viste(d, [parola])
        in_gioco[d] = time.time()
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
        S["viste"] = {}  # catene nuove: per ora nessuno ha visto niente
        attese.clear()
        in_gioco.clear()
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
            "voti_persone": {p: dict(v) for p, v in S["voti"].items()},  # {frase: {telefono: risposta}}
            "catene": [{"id": c["id"], "memoria": c["memoria"], "lunghezza": c["lunghezza"],
                        "parole": c["parole"], "autori": c["autori"], "occupata": bool(c["turno"])}
                       for c in S["catene"]],
            "nomi": dict(S["nomi"]),
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


def avvia_funnel() -> subprocess.Popen | None:
    """`tailscale funnel PORTA` in primo piano: resta acceso finché gira il server, poi sparisce."""
    cli = tailscale_cli()
    if cli is None:
        print("⚠️   Tailscale non trovato: installa l'app (tailscale.com) e accedi, oppure usa il router.")
        return None
    # Una piccola sentinella in shell: se questo processo muore in qualsiasi modo (anche ucciso),
    # spegne Funnel entro un secondo, così il sito non resta su Internet per sbaglio.
    sentinella = (f'"{cli}" funnel {PORTA} & f=$!; '
                  f'while kill -0 {os.getpid()} 2>/dev/null && kill -0 $f 2>/dev/null; do sleep 1; done; '
                  'kill $f 2>/dev/null')
    funnel = subprocess.Popen(["/bin/sh", "-c", sentinella], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True)

    def ripeti():  # quello che dice Tailscale (per esempio il link per abilitare Funnel la prima volta)
        for riga in funnel.stdout:
            if riga.strip():
                print(f"   [funnel] {riga.rstrip()}", flush=True)

    threading.Thread(target=ripeti, daemon=True).start()
    return funnel


if __name__ == "__main__":
    import segno

    funnel = avvia_funnel() if modo() == "online" else None

    def annuncia():
        url, ok, motivo = url_da_mostrare()
        print(f"\n🦜  Il sito della sala è su  {url}   (rete: {modo()})")
        print(("✅  " if ok else "⚠️   il QR delle slide non porta qui: ") + motivo.replace("`", "") + "\n")
        segno.make(url, error="m").terminal(compact=True)
        print("\n(il palco, cioè il notebook, parla con http://127.0.0.1:%d)\n" % PORTA, flush=True)
        if funnel and not ok:  # la prima volta Funnel ci mette qualche minuto: lo diciamo appena funziona
            print("⏳  riprovo ogni 15 secondi finché l'indirizzo pubblico non risponde…", flush=True)
            for _ in range(80):  # 20 minuti
                time.sleep(15)
                if funnel.poll() is not None:
                    return
                ok, motivo = url_da_mostrare()[1:]
                if ok:
                    print("✅  " + motivo.replace("`", ""), flush=True)
                    return

    # il controllo chiama il sito, quindi aspetta che il server (e Funnel) siano partiti
    threading.Thread(target=lambda: (time.sleep(5.0 if funnel else 1.0), annuncia()), daemon=True).start()
    try:
        uvicorn.run(app, host="0.0.0.0", port=PORTA, log_level="warning")
    finally:
        if funnel and funnel.poll() is None:
            funnel.terminate()  # Funnel si spegne: il sito non è più su Internet
            funnel.wait(timeout=5)
