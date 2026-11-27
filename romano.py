"""Er pappagallo romano: lo stesso Qwen3-0.6B-Base, addestrato sul romanaccio.

    uv run python romano.py scarica                 # i testi dell'Ottocento da Liber Liber (~490 KB)
    uv run python romano.py addestra                # qualche minuto sul Mac; salva in modelli/pappagallo-romano/
    uv run python romano.py prova "Lo sai chi te saluta tanto?"

I testi: i sonetti del Belli (due raccolte) e "Usi, costumi e pregiudizi del popolo di Roma" di
Giggi Zanazzo, di pubblico dominio, dalla biblioteca di Liber Liber. Più romanaccio/frasi.txt, il
romanesco di oggi (intercalari, magnà, insulti da bar), che durante l'addestramento pesa di più.
I testi scaricati e il modello addestrato restano fuori da git.
"""
from __future__ import annotations

import argparse
import io
import math
import random
import re
import time
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

QUI = Path(__file__).parent
TESTI = QUI / "romanaccio" / "testi"
FRASI = QUI / "romanaccio" / "frasi.txt"
USCITA = QUI / "modelli" / "pappagallo-romano"
MODELLO = "Qwen/Qwen3-0.6B-Base"

LIBER_LIBER = "https://linux.studenti.polito.it/static_resources/liberliber/biblioteca"
ARCHIVI = {  # file -> percorso nella biblioteca (specchio di Liber Liber al Politecnico di Torino)
    "sonetti.zip": "b/belli/sonetti/sonetti.zip",
    "duecento.zip": "b/belli/duecento_sonetti_in_dialetto_romanesco/duecento.zip",
    "usi_cost.zip": "z/zanazzo/usi_costumi_e_pregiudizi_del_popolo_di_roma/usi_cost.zip",
}
# Il Belli ha anche i sonetti "lussuriosi": in un meetup, su un proiettore, er pappagallo romano deve
# essere sboccato da bar, non pornografico. Le strofe con queste radici restano fuori (--anche-sconci le tiene).
SCONCE = re.compile(r"\b(mi[g]?gnott|fica|fich|sorc[aà]|chiav|fott|scop|uscell|pipin|pisell|zinn|puttan|bordell|"
                    r"fregn|cazz|culo|cul[ei]|minchi|ciuccia|sega\b|pompin|vergin)", re.IGNORECASE)

PROVE = [
    "Lo sai chi te saluta tanto?",
    "A Roma, quando piove, il traffico",
    "Aò, ma che stai a",
    "La carbonara vera se fa co'",
    "Er modello nun converge perché",
]


# --- i testi ---------------------------------------------------------------
def scarica() -> None:
    TESTI.mkdir(parents=True, exist_ok=True)
    for nome, percorso in ARCHIVI.items():
        destinazione = TESTI / nome
        if destinazione.exists():
            print(f"  c'è già {nome}")
            continue
        with urllib.request.urlopen(f"{LIBER_LIBER}/{percorso}", timeout=60) as r:
            destinazione.write_bytes(r.read())
        print(f"  scaricato {nome} ({destinazione.stat().st_size // 1024} KB)")


_INTERNI = str.maketrans("àèéìíòóùúâêîôû", "aeeiioouuaeiou")
_FINALI = {"ú": "ù", "í": "ì", "ó": "ò", "ô": "ò", "â": "à", "ê": "è", "î": "ì", "û": "ù"}


def _parola_moderna(m: re.Match) -> str:
    """Il Belli scrive "bbene", "cche", "ppiú" e lo Zanazzo segna gli accenti ("mettétece"): qui si
    scrive come oggi, così il modello impara il romanesco e non l'ortografia dell'Ottocento."""
    w = m.group(0)
    if len(w) > 2 and w[1].islower() and (w[0].lower() == w[1] or w[0].lower() + w[1] == "cq") \
            and w[0].lower() in "bcdfglmnprstvz":
        w = (w[1].upper() if w[0].isupper() else w[1]) + w[2:]  # bbene -> bene, Ddio -> Dio, cqua -> qua
    if len(w) > 1:
        w = w[:-1].translate(_INTERNI) + _FINALI.get(w[-1], w[-1])
    return w


def pulisci(testo: str, max_riga: int | None = None) -> str:
    righe = testo.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # l'intestazione di Liber Liber finisce con il paragrafo 'Se questo "libro elettronico"...'
    fine_intestazione = next((i for i, r in enumerate(righe[:120]) if r.startswith('Se questo "libro')), -1)
    buone = []
    for r in righe[fine_intestazione + 1:]:
        r = r.strip()
        if (re.fullmatch(r"\d+|[IVXL]+\.?|[*_\s-]+|\[?\d{1,2} \w+ \d{4}\]?\??|\[\d{4}\??\]", r)  # numeri, date
                or re.match(r"\d+\s", r)                                                # note a piè di pagina
                or (sum(c.isalpha() for c in r) > 3 and r.upper() == r)                  # titoli in maiuscolo
                or (max_riga and len(r) > max_riga)):                                   # prosa in italiano
            r = ""
        r = re.sub(r"(?<=[^\s\d])\d+\b", "", r)  # i rimandi alle note: "Cristo.4" -> "Cristo."
        buone.append(re.sub(r"[^\W\d_]+", _parola_moderna, r))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(buone)).strip()


def senza_sconci(testo: str) -> str:
    return "\n\n".join(s for s in testo.split("\n\n") if not SCONCE.search(s))


def testi_classici(anche_sconci: bool = False) -> list[str]:
    if not all((TESTI / n).exists() for n in ARCHIVI):
        raise SystemExit("Mancano i testi: lancia prima `uv run python romano.py scarica`.")
    testi = []
    for nome in ARCHIVI:
        with zipfile.ZipFile(TESTI / nome) as z:
            grezzo = z.read(next(n for n in z.namelist() if n.endswith(".txt"))).decode("cp1252", "replace")
        # nei "Duecento sonetti" le righe lunghe sono la prefazione e le note, in italiano
        pulito = pulisci(grezzo, max_riga=150 if nome == "duecento.zip" else None)
        testi.append(pulito if anche_sconci else senza_sconci(pulito))
    return testi


def frasi() -> list[str]:
    return [r.strip() for r in FRASI.read_text().splitlines() if r.strip() and not r.startswith("#")]


# --- il modello --------------------------------------------------------------
def dispositivo():
    import torch

    return "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"


def addestra(passi: int, lotto: int, blocco: int, lr: float, peso_frasi: float, seme: int,
             anche_sconci: bool = False) -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    random.seed(seme)
    torch.manual_seed(seme)
    dev = dispositivo()
    tok = AutoTokenizer.from_pretrained(MODELLO)
    classici = tok("\n\n".join(testi_classici(anche_sconci))).input_ids
    nostre = [tok(f + "\n").input_ids for f in frasi()]
    print(f"📚 {len(classici):,} token dall'Ottocento, {sum(map(len, nostre)):,} dalle {len(nostre)} frasi di oggi")

    def esempio() -> list[int]:
        if random.random() < peso_frasi:  # le frasi di oggi, in un ordine sempre diverso
            random.shuffle(nostre)
            ids = [t for f in nostre for t in f]
            inizio = random.randrange(0, max(1, len(ids) - blocco))
            return ids[inizio:inizio + blocco]
        inizio = random.randrange(0, len(classici) - blocco)
        return classici[inizio:inizio + blocco]

    model = AutoModelForCausalLM.from_pretrained(MODELLO, dtype=torch.float32).to(dev)
    model.get_input_embeddings().weight.requires_grad_(False)  # come nell'Atto 3: le parole restano quelle
    allenabili = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(allenabili, lr=lr, weight_decay=0.0)
    riscaldamento = max(1, passi // 15)
    pianifica = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1, (s + 1) / riscaldamento)
                                                  * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(1, s / passi)))))
    model.train()
    t0, perdite = time.time(), []
    for passo in range(1, passi + 1):
        ids = torch.tensor([esempio() for _ in range(lotto)], device=dev)
        perdita = model(input_ids=ids, labels=ids).loss
        perdita.backward()
        torch.nn.utils.clip_grad_norm_(allenabili, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        pianifica.step()
        perdite.append(perdita.item())
        if passo % 20 == 0 or passo == passi:
            media = sum(perdite[-20:]) / len(perdite[-20:])
            print(f"  passo {passo:4d}/{passi}  loss {media:.3f}  ({time.time() - t0:.0f} s)", flush=True)
    model.eval()
    USCITA.mkdir(parents=True, exist_ok=True)
    model.to(torch.bfloat16).save_pretrained(USCITA)  # in bf16: metà spazio, stessa sostanza
    tok.save_pretrained(USCITA)
    (USCITA / "LEGGIMI.txt").write_text(
        f"Qwen3-0.6B-Base addestrato sul romanaccio da romano.py: {passi} passi, lotti da {lotto}x{blocco} token, "
        f"lr {lr}, frasi di oggi al {peso_frasi:.0%}. Testi: Belli e Zanazzo (Liber Liber) + romanaccio/frasi.txt.\n")
    print(f"💾 salvato in {USCITA.relative_to(QUI)}/ ({time.time() - t0:.0f} s in tutto)")


def prova(frasi_prova: list[str], n: int = 120) -> None:
    """Le prime parole che i due pappagalli scelgono dopo ogni frase, più una continuazione a testa."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not (USCITA / "config.json").exists():
        raise SystemExit("Manca il modello: lancia prima `uv run python romano.py addestra`.")
    dev = dispositivo()
    tok = AutoTokenizer.from_pretrained(MODELLO)
    modelli = {"normale": AutoModelForCausalLM.from_pretrained(MODELLO, dtype=torch.float32).to(dev).eval(),
               "romano": AutoModelForCausalLM.from_pretrained(USCITA, dtype=torch.float32).to(dev).eval()}
    for frase in frasi_prova:
        print(f"\n🗣️  «{frase}…»")
        for nome, m in modelli.items():
            enc = tok([frase] * n, return_tensors="pt").to(dev)
            with torch.no_grad():
                out = m.generate(**enc, do_sample=True, temperature=0.9, top_p=0.95, top_k=0, max_new_tokens=14,
                                 pad_token_id=tok.pad_token_id)
            seguiti = tok.batch_decode(out[:, enc.input_ids.shape[1]:], skip_special_tokens=True)
            prime = Counter(m_.group(0) for s in seguiti if (m_ := re.search(r"[^\W\d_]+'?", s)))
            top = ", ".join(f"{w} {c / n:.0%}" for w, c in prime.most_common(6))
            print(f"   {nome:>7}: {top}")
            print(f"            → {frase} {seguiti[0].strip().splitlines()[0] if seguiti[0].strip() else ''}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sotto = ap.add_subparsers(dest="cosa", required=True)
    sotto.add_parser("scarica", help="scarica i testi dell'Ottocento da Liber Liber")
    a = sotto.add_parser("addestra", help="addestra e salva er pappagallo romano")
    a.add_argument("--passi", type=int, default=300)
    a.add_argument("--lotto", type=int, default=8)
    a.add_argument("--blocco", type=int, default=128, help="token per esempio")
    a.add_argument("--lr", type=float, default=3e-5)
    a.add_argument("--peso-frasi", type=float, default=0.2, help="quota degli esempi presi da frasi.txt")
    a.add_argument("--seme", type=int, default=0)
    a.add_argument("--anche-sconci", action="store_true", help="tiene anche le strofe sconce del Belli")
    p = sotto.add_parser("prova", help="confronta il modello normale e quello romano")
    p.add_argument("frasi", nargs="*", default=PROVE)
    sotto.add_parser("testo", help="stampa un pezzo dei testi puliti, per controllarli")
    args = ap.parse_args()

    if args.cosa == "scarica":
        scarica()
    elif args.cosa == "addestra":
        addestra(args.passi, args.lotto, args.blocco, args.lr, args.peso_frasi, args.seme, args.anche_sconci)
    elif args.cosa == "prova":
        prova(args.frasi)
    else:
        for t in testi_classici():
            print(t[5000:6500], "\n" + "=" * 60)


if __name__ == "__main__":
    main()
