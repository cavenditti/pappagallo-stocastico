"""Il collegamento fra il notebook (il palco) e il sito della sala (i telefoni).

Il notebook usa `Sala` per aprire e chiudere le votazioni, avviare le catene e
leggere i dati. Le chiamate di amministrazione funzionano solo da questo
portatile: il server le accetta soltanto da 127.0.0.1.

    uv run python sala.py    # rigenera i QR delle slide in qr/ (wifi e gioco)
"""
from __future__ import annotations

import json
import os
import socket
import urllib.parse
import urllib.request

PORTA = int(os.environ.get("SALA_PORTA", "8000"))
# La rete del router da viaggio e l'indirizzo fisso del gioco: sono stampati
# (come QR) sulle slide, quindi il router va configurato così.
WIFI_NOME = os.environ.get("SALA_WIFI", "pappagallo")
WIFI_PASSWORD = os.environ.get("SALA_WIFI_PASSWORD", "pydataroma")
URL_GIOCO = os.environ.get("SALA_URL", f"http://pappagallo.lan:{PORTA}")

# urllib rispetterebbe eventuali proxy di sistema: per parlare con localhost non ne vogliamo.
_apri = urllib.request.build_opener(urllib.request.ProxyHandler({})).open


def indirizzo_locale() -> str:
    """L'IP di questo portatile sulla rete del router o dell'hotspot (forzabile con SALA_HOST)."""
    if host := os.environ.get("SALA_HOST"):
        return host
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
    """Il QR delle slide porta a URL_GIOCO: su questa rete arriva davvero a questo portatile?"""
    host = urllib.parse.urlparse(URL_GIOCO).hostname or ""
    locale = indirizzo_locale()
    try:
        ip = socket.gethostbyname(host)
    except OSError:
        return False, f"`{host}` non si risolve su questa rete (manca il nome sul router?)"
    if ip != locale:
        return False, f"`{host}` porta a {ip}, ma questo portatile è a {locale}"
    return True, f"`{host}` porta a questo portatile ({locale})"


def url_da_mostrare() -> tuple[str, bool, str]:
    """L'indirizzo fisso se funziona, altrimenti quello via IP (con il motivo)."""
    ok, motivo = controlla_url_gioco()
    return (URL_GIOCO if ok else url_pubblico()), ok, motivo


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
    for nome, qr in (("wifi", _qr_wifi()), ("gioco", _qr_gioco(URL_GIOCO))):
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
        richiesta = urllib.request.Request(self.base + percorso, data=corpo, method=metodo,
                                           headers={"Content-Type": "application/json"})
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
    print(f"Gioco: {URL_GIOCO}")
    for percorso in salva_qr_slide():
        print("  scritto", percorso)
    ok, motivo = controlla_url_gioco()
    print(("✅ " if ok else "⚠️  ") + motivo.replace("`", ""))
