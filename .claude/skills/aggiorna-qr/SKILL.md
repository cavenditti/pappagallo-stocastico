---
name: aggiorna-qr
description: Cambia l'indirizzo del gioco (router, o hotspot del Mac), rigenera i QR e mette il nuovo QR del gioco nelle slide 4 e 9 del deck su claude.ai. Usala quando l'utente dà il nuovo IP o nome del portatile sulla rete del router, vuole passare all'hotspot (o tornare al router), o chiede di cambiare il QR del gioco nelle slide.
argument-hint: <ip-o-nome del portatile, es. 192.168.1.200> | qui | hotspot
---

# Aggiorna il QR del gioco nel deck

Nuovo indirizzo richiesto: `$ARGUMENTS`

Il deck è https://claude.ai/artifact/A6Ju2Uh3r48N3wtFo2AxxM (tipo Slides). Le slide da cambiare
sono `project/slides/gioco.html` (slide 4) e `project/slides/qr-finale.html` (slide 9): sono le
uniche con il QR del gioco e mostrano un indirizzo solo, quello della rete che si usa. Il QR del
Wi-Fi non si tocca.

## 1. L'indirizzo

- Prendi l'host dagli argomenti: un IP (`192.168.1.200`) o un nome (`pappagallo.fritz.box`).
  Togli `http://`, la porta e lo `/` finale, se ci sono.
- Se l'argomento è `qui`, usa l'IP attuale del portatile:
  `uv run python -c "from sala import indirizzo_locale; print(indirizzo_locale())"`.
  Ricorda all'utente che deve essere un indirizzo fisso (vedi GUIDA.md, "Il router: cosa impostare").
- Se l'argomento è `hotspot`, le slide vanno sull'hotspot del Mac: **non toccare `sala.py`** (il
  modo hotspot si riconosce da solo), salta il punto 2.1, prendi come testo la riga
  `Gioco (hotspot): http://…` del punto 2.2 e usa `qr/gioco-hotspot.svg` al punto 3.1.
- Se non c'è nessun argomento, chiedi l'indirizzo e fermati.

## 2. Il codice e i QR

1. In `sala.py`, nella riga `INDIRIZZO_ROUTER = os.environ.get("SALA_INDIRIZZO", "…")`, metti il
   nuovo host come valore di default.
2. Lancia `uv run python sala.py`. Rigenera `qr/` e stampa `Gioco (router): http://…`: quell'URL
   senza `http://` (es. `192.168.1.200:8000`) è il testo da scrivere sulle slide. Riporta la riga
   del controllo. Un ⚠️ è normale se il portatile non è collegato a quella rete in questo momento.

## 3. Le slide

1. Carica il nuovo QR come asset: Artifact `publish` con `url` del deck,
   `file_path` = `<repo>/qr/gioco.svg` (o `qr/gioco-hotspot.svg` per l'hotspot), `asset: true`.
   Tieni l'id di 32 caratteri che restituisce.
2. Rileggi le due slide dal deck, perché l'utente le modifica nell'editor: Artifact `read` con
   `paths: ["project/slides/gioco.html", "project/slides/qr-finale.html"]`. Il risultato dice in
   quale cartella le ha salvate (chiamala CARTELLA: contiene `project/`).
3. Applica il cambio con lo script accanto a questo file:
   ```bash
   uv run python .claude/skills/aggiorna-qr/aggiorna_slide.py --indirizzo <host:porta> --blob <id> CARTELLA/project/slides/gioco.html CARTELLA/project/slides/qr-finale.html
   ```
   Cambia solo il `src` e l'alt del QR del gioco, e l'indirizzo scritto. Se si ferma con ✗, la
   slide è stata ristrutturata a mano: fai le stesse tre modifiche con Edit e dillo all'utente.
4. Pubblica: Artifact `publish` con `url` del deck, `root` = CARTELLA,
   `file_path` = `CARTELLA/project/slides/gioco.html`,
   `files` = `{"project/slides/qr-finale.html": "project/slides/qr-finale.html"}`.
   Se la pubblicazione viene rifiutata perché c'è una versione più nuova, ripeti dal punto 2.
5. Verifica: rileggi le due slide e controlla che entrambe contengano il nuovo id e il nuovo indirizzo.

## 4. Alla fine

- Di' all'utente quali slide sono cambiate e da quale indirizzo a quale.
- Ricordagli di **riscaricare il PDF** del deck (Share › Export): in sala si proietta quello.
- Proponi il commit di `sala.py` e `qr/`; non farlo senza un sì.
