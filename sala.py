"""Il collegamento fra il notebook (il palco) e il sito della sala (i telefoni).

Il notebook usa `Sala` per aprire e chiudere le votazioni, avviare le catene e
leggere i dati. Le chiamate di amministrazione funzionano solo da questo
portatile: il server le accetta soltanto da 127.0.0.1.
"""
from __future__ import annotations

import json
import os
import socket
import urllib.request

PORTA = int(os.environ.get("SALA_PORTA", "8000"))
# La rete del router da viaggio (le stesse credenziali sono sulla slide 3).
WIFI_NOME = os.environ.get("SALA_WIFI", "pappagallo")
WIFI_PASSWORD = os.environ.get("SALA_WIFI_PASSWORD", "pydataroma")

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
    return f"http://{indirizzo_locale()}:{PORTA}"


def qr_svg(testo: str, scala: int = 8) -> str:
    import segno

    return segno.make(testo, error="m").svg_inline(scale=scala, dark="#0b0b0b", light="#ffffff", border=2)


def qr_wifi_svg(scala: int = 7) -> str:
    """QR "inquadra e collegati": la fotocamera del telefono propone di entrare nella rete."""
    import segno.helpers

    qr = segno.helpers.make_wifi(ssid=WIFI_NOME, password=WIFI_PASSWORD, security="WPA")
    return qr.svg_inline(scale=scala, dark="#0b0b0b", light="#ffffff", border=2)


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
