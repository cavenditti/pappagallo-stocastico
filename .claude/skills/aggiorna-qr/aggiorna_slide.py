"""Mette il nuovo QR del gioco nelle slide del deck (gioco e qr-finale).

    uv run python aggiorna_slide.py --indirizzo 192.168.1.200:8000 --blob <id> gioco.html qr-finale.html

In ogni slide cambia tre cose: il `src` dell'immagine del QR del gioco (riconosciuta dal suo
alt "QR code per aprire il gioco: …"), il suo alt, e l'indirizzo scritto sotto. Il resto della
slide, comprese le modifiche fatte a mano nell'editor, resta com'è. Se la slide non ha la forma
attesa si ferma senza scrivere niente.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ALT = "QR code per aprire il gioco: "
QR_GIOCO = re.compile(r'<img\b[^>]*\balt="' + re.escape(ALT) + r'([^"]+)"[^>]*>')
BLOB = re.compile(r"^[0-9a-f]{32}$")


def aggiorna(testo: str, indirizzo: str, blob: str) -> tuple[str, str, int]:
    """(slide aggiornata, indirizzo di prima, quante volte compariva scritto)."""
    trovati = list(QR_GIOCO.finditer(testo))
    if len(trovati) != 1:
        raise ValueError(f"mi aspettavo un solo QR del gioco, ne ho trovati {len(trovati)}")
    tag, vecchio = trovati[0].group(0), trovati[0].group(1)
    nuovo_tag, n_src = re.subn(r'\bsrc="[^"]*"', f'src="/_blob/{blob}"', tag, count=1)
    if n_src != 1:
        raise ValueError("il QR del gioco non ha un src")
    nuovo_tag = nuovo_tag.replace(ALT + vecchio, ALT + indirizzo)
    testo = testo.replace(tag, nuovo_tag, 1)
    scritto = testo.count(vecchio)
    if scritto == 0:
        raise ValueError(f"non trovo l'indirizzo {vecchio} scritto nella slide")
    return testo.replace(vecchio, indirizzo), vecchio, scritto


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--indirizzo", required=True, help="come appare sulla slide, es. 192.168.1.200:8000")
    p.add_argument("--blob", required=True, help="id dell'asset del nuovo QR (32 caratteri esadecimali)")
    p.add_argument("slide", nargs="+", type=Path)
    a = p.parse_args()

    indirizzo = a.indirizzo.removeprefix("http://").rstrip("/")
    blob = a.blob.removeprefix("/_blob/")
    if not BLOB.match(blob):
        p.error(f"--blob non sembra un id di asset: {a.blob}")

    nuove, resoconto = {}, []
    for percorso in a.slide:
        try:
            nuove[percorso], vecchio, scritto = aggiorna(percorso.read_text(), indirizzo, blob)
        except (OSError, ValueError) as errore:
            print(f"✗ {percorso.name}: {errore}. Nessun file modificato.", file=sys.stderr)
            return 1
        resoconto.append(f"✓ {percorso.name}: {vecchio} → {indirizzo} "
                         f"(QR + {scritto} scritt{'o' if scritto == 1 else 'i'})")
    for percorso, testo in nuove.items():  # si scrive solo se tutte le slide sono a posto
        percorso.write_text(testo)
    print("\n".join(resoconto))
    return 0


if __name__ == "__main__":
    sys.exit(main())
