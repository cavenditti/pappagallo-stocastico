"""Il collegamento fra il notebook (il palco) e il sito della sala (i telefoni).

Il notebook usa `Sala` per aprire e chiudere le votazioni, avviare le catene e
leggere i dati. Le chiamate di amministrazione funzionano solo da questo
portatile: il server le accetta soltanto da 127.0.0.1.

    uv run python sala.py    # rigenera i QR delle slide in qr/ (wifi e gioco, per le due reti)

Tre modi di portare i telefoni al gioco:
- "online" (il piano): Tailscale Funnel mette il sito su Internet a URL_ONLINE; i telefoni usano i
  loro dati, niente Wi-Fi. server.py accende Funnel da solo.
- "router": un router qualsiasi, senza Internet; il gioco è su http://INDIRIZZO_ROUTER:8000, dove
  INDIRIZZO_ROUTER è un nome impostato sul router oppure l'IP fisso del portatile (es. 192.168.1.10)
- "hotspot": il Mac stesso (Condivisione Internet); il gioco è su http://192.168.2.1:8000
Vale MODO_PREDEFINITO, ma se il Mac sta condividendo la connessione è "hotspot"; si forza con SALA_MODO.
"""
from __future__ import annotations

import ipaddress
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PORTA = int(os.environ.get("SALA_PORTA", "8000"))
# Nome e password della rete, uguali nei due modi: sono stampati (come QR) sulle slide.
WIFI_NOME = os.environ.get("SALA_WIFI", "pappagallo")
WIFI_PASSWORD = os.environ.get("SALA_WIFI_PASSWORD", "pydataroma")
# Col router: dove trovano il portatile i telefoni (ed è quello che c'è sul QR delle slide).
# Un nome, se il router permette di aggiungerne uno; altrimenti l'IP fisso che dai al portatile (vedi GUIDA).
INDIRIZZO_ROUTER = os.environ.get("SALA_INDIRIZZO", "pappagallo.lan")
# L'indirizzo che macOS dà di solito al Mac quando fa da hotspot (Condivisione Internet).
HOTSPOT_IP = os.environ.get("SALA_HOTSPOT_IP", "192.168.2.1")
# Online: l'indirizzo pubblico di Tailscale Funnel per questo Mac (nome del Mac + nome della tailnet).
URL_ONLINE = os.environ.get("SALA_URL_ONLINE", "https://carlos-macbook-pro.tailefac23.ts.net")
URL_PER_MODO = {
    "online": URL_ONLINE,
    "router": f"http://{INDIRIZZO_ROUTER}:{PORTA}",
    "hotspot": f"http://{HOTSPOT_IP}:{PORTA}",
}
MODO_PREDEFINITO = "online"  # la rete prevista per la serata: "online" o "router" (le slide puntano lì)
# Il codice segreto del palco: lo scrive server.py a ogni avvio, lo usa il notebook (vedi Sala).
FILE_PALCO = Path(__file__).parent / ".palco"

# Atto 1: quante parole può scrivere la sala come risposta (le altre si tagliano).
MAX_PAROLE_RISPOSTA = 3
_BORDI = ".,;:!?…«»\"“”()[]{}"


def risposta(testo: str, max_parole: int = MAX_PAROLE_RISPOSTA) -> str | None:
    """Una risposta normalizzata: minuscole, senza punteggiatura attorno, al massimo `max_parole` parole."""
    pezzi = [p.strip(_BORDI) for p in testo.lower().replace("’", "'").split()]
    return " ".join([p for p in pezzi if p][:max_parole]) or None


# urllib rispetterebbe eventuali proxy di sistema: per parlare con localhost non ne vogliamo.
_apri = urllib.request.build_opener(urllib.request.ProxyHandler({})).open


def ip_hotspot() -> str | None:
    """Se il Mac sta facendo da hotspot (Condivisione Internet), il suo IP su quella rete."""
    if sys.platform != "darwin":
        return None
    for interfaccia in ("bridge100", "bridge101"):  # le interfacce che crea Condivisione Internet
        try:
            uscita = subprocess.run(["ipconfig", "getifaddr", interfaccia],
                                    capture_output=True, text=True, timeout=2)
        except (OSError, subprocess.SubprocessError):
            return None
        if uscita.returncode == 0 and uscita.stdout.strip():
            return uscita.stdout.strip()
    return None


def modo() -> str:
    """'hotspot' se il Mac sta condividendo la connessione, altrimenti MODO_PREDEFINITO (forzabile con SALA_MODO)."""
    forzato = os.environ.get("SALA_MODO", "").strip().lower()
    if forzato in URL_PER_MODO:
        return forzato
    return "hotspot" if ip_hotspot() else MODO_PREDEFINITO


def tailscale_cli() -> str | None:
    """Il comando tailscale: nel PATH, oppure dentro l'app per macOS."""
    app = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
    return shutil.which("tailscale") or (app if os.path.exists(app) else None)


def url_gioco() -> str:
    """L'indirizzo fisso stampato sulle slide per il modo attuale (forzabile con SALA_URL)."""
    return os.environ.get("SALA_URL") or URL_PER_MODO[modo()]


def indirizzo_locale() -> str:
    """L'IP con cui i telefoni vedono questo portatile (forzabile con SALA_HOST)."""
    if host := os.environ.get("SALA_HOST"):
        return host
    if ip := ip_hotspot():  # col Mac come hotspot i telefoni lo vedono lì, non sulla rete di uscita
        return ip
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # non spedisce niente: serve solo a scegliere l'interfaccia
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def url_pubblico() -> str:
    """L'indirizzo del gioco via IP: funziona sempre, ma cambia con la rete."""
    return f"http://{indirizzo_locale()}:{PORTA}"


def controlla_url_gioco() -> tuple[bool, str]:
    """Il QR delle slide porta a url_gioco(): su questa rete arriva davvero a questo portatile?"""
    if modo() == "hotspot" and not ip_hotspot():
        return False, "modo hotspot, ma Condivisione Internet non è attiva (nessuna interfaccia bridge100)"
    if modo() == "online":
        return _controlla_online()
    host = urllib.parse.urlparse(url_gioco()).hostname or ""
    locale = indirizzo_locale()
    try:
        ipaddress.ip_address(host)
        e_un_ip = True
    except ValueError:
        e_un_ip = False
    if e_un_ip and not _e_mio(host):
        return False, f"le slide puntano a `{host}`, ma questo portatile è a {locale}: dagli l'IP fisso {host}"
    try:
        ip = socket.gethostbyname(host)
    except OSError:
        return False, f"`{host}` non si risolve su questa rete (manca il nome sul router?)"
    if not _e_mio(ip):
        return False, f"`{host}` porta a {ip}, ma questo portatile è a {locale}"
    return True, f"`{host}` porta a questo portatile"


def _e_mio(ip: str) -> bool:
    """L'IP appartiene a una delle interfacce di questo portatile? (Cavo e Wi-Fi insieme, per esempio.)"""
    if os.environ.get("SALA_HOST"):
        return ip == os.environ["SALA_HOST"]
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((ip, 0))  # ci si può legare solo a un indirizzo che è davvero nostro
        return not ipaddress.ip_address(ip).is_loopback
    except (OSError, ValueError):
        return False


def _ping(url: str, timeout: float) -> str | None:
    """L'identificativo del server che risponde a url (cambia a ogni avvio di server.py)."""
    try:
        import certifi
        contesto = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        contesto = ssl.create_default_context()
    apri = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=contesto))
    try:
        with apri.open(url.rstrip("/") + "/api/ping", timeout=timeout) as r:
            return json.load(r).get("server")
    except (OSError, ValueError):
        return None


def _controlla_online() -> tuple[bool, str]:
    mio = _ping(f"http://127.0.0.1:{PORTA}", 2)
    if mio is None:
        return False, "il server non è acceso: lancia `uv run python server.py` (accende anche Funnel)"
    suo = _ping(url_gioco(), 8)
    if suo is None:
        return False, f"`{url_gioco()}` non risponde: Funnel è acceso? (lo accende server.py, guarda cosa dice)"
    if suo != mio:
        return False, f"`{url_gioco()}` porta a un altro server, non a questo"
    return True, f"`{url_gioco()}` porta a questo portatile, via Internet"


def url_da_mostrare() -> tuple[str, bool, str]:
    """L'indirizzo fisso se funziona, altrimenti quello via IP (con il motivo). Online non c'è un piano B via IP."""
    ok, motivo = controlla_url_gioco()
    return (url_gioco() if ok or modo() == "online" else url_pubblico()), ok, motivo


def _qr_gioco(testo: str):
    import segno

    return segno.make(testo, error="m")


def _qr_wifi():
    import segno.helpers

    return segno.helpers.make_wifi(ssid=WIFI_NOME, password=WIFI_PASSWORD, security="WPA")


def qr_svg(testo: str, scala: int = 8) -> str:
    return _qr_gioco(testo).svg_inline(scale=scala, dark="#0b0b0b", light="#ffffff", border=2)


def qr_wifi_svg(scala: int = 7) -> str:
    """QR "inquadra e collegati": la fotocamera del telefono propone di entrare nella rete."""
    return _qr_wifi().svg_inline(scale=scala, dark="#0b0b0b", light="#ffffff", border=2)


def salva_qr_slide(cartella: str = "qr") -> list[str]:
    """I QR per le slide, in SVG e PNG: da caricare nel deck se cambi rete o indirizzo."""
    from pathlib import Path

    Path(cartella).mkdir(exist_ok=True)
    scritti = []
    codici = (("wifi", _qr_wifi()),
              ("gioco", _qr_gioco(URL_PER_MODO["router"])),
              ("gioco-online", _qr_gioco(URL_PER_MODO["online"])),
              ("gioco-hotspot", _qr_gioco(URL_PER_MODO["hotspot"])))
    for nome, qr in codici:
        for estensione in ("svg", "png"):
            percorso = f"{cartella}/{nome}.{estensione}"
            qr.save(percorso, scale=20, border=2, dark="#1B2A22", light="#FFFDF7")
            if estensione == "svg":  # con il viewBox l'immagine si ridimensiona senza tagli
                lato = qr.symbol_size(scale=20, border=2)[0]
                testo = Path(percorso).read_text().replace(
                    'class="segno"', f'viewBox="0 0 {lato} {lato}"', 1)
                Path(percorso).write_text(testo)
            scritti.append(percorso)
    return scritti


class Sala:
    def __init__(self, base: str = f"http://127.0.0.1:{PORTA}", timeout: float = 2.0):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def _chiama(self, metodo: str, percorso: str, dati: dict | None = None):
        corpo = json.dumps(dati).encode() if dati is not None else None
        intestazioni = {"Content-Type": "application/json"}
        if FILE_PALCO.exists():  # il codice del palco, riletto ogni volta: cambia se riavvii il server
            intestazioni["X-Palco"] = FILE_PALCO.read_text().strip()
        richiesta = urllib.request.Request(self.base + percorso, data=corpo, method=metodo, headers=intestazioni)
        try:
            with _apri(richiesta, timeout=self.timeout) as risposta:
                return json.load(risposta)
        except (OSError, ValueError):
            return None

    def online(self) -> bool:
        return self._chiama("GET", "/api/ping") is not None

    def fase(self, fase: str, prompt: str | None = None):
        return self._chiama("POST", "/api/admin/fase", {"fase": fase, "prompt": prompt})

    def avvia_catene(self, inizio: str, n: int, lunghezza: int):
        return self._chiama("POST", "/api/admin/catene", {"inizio": inizio, "n": n, "lunghezza": lunghezza})

    def dati(self) -> dict | None:
        """{"fase", "prompt", "voti": {prompt: [testi]}, "catene": [...], "persone", "connessi"}"""
        return self._chiama("GET", "/api/admin/dati")

    def azzera(self):
        """Svuota voti e catene (il vecchio file viene conservato come backup)."""
        return self._chiama("POST", "/api/admin/azzera", {})


if __name__ == "__main__":
    print(f"Wi-Fi: {WIFI_NOME} / {WIFI_PASSWORD}")
    for nome, url in URL_PER_MODO.items():
        print(f"Gioco ({nome}): {url}")
    for percorso in salva_qr_slide():
        print("  scritto", percorso)
    ok, motivo = controlla_url_gioco()
    print(f"Modo attuale: {modo()} → {url_gioco()}")
    print(("✅ " if ok else "⚠️  ") + motivo.replace("`", ""))
