---
name: aggiorna-qr
description: Cambia la rete del gioco (online con Tailscale Funnel, router o hotspot del Mac), rigenera i QR e mette il QR giusto nella slide del gioco e in quella finale del deck su claude.ai, con o senza la slide del Wi-Fi. Usala quando l'utente vuole passare online, al router (con un IP o un nome) o all'hotspot, o chiede di cambiare il QR del gioco nelle slide.
argument-hint: online | <ip-o-nome del portatile sul router, es. 192.168.1.10> | qui | hotspot
---

# Aggiorna il QR del gioco nel deck

Nuova rete o indirizzo richiesto: `$ARGUMENTS`

Il deck è https://claude.ai/artifact/A6Ju2Uh3r48N3wtFo2AxxM (tipo Slides). Le slide coinvolte:
- `project/slides/gioco.html` (la slide del gioco) e `project/slides/qr-finale.html` (l'ultima): il
  QR del gioco e l'indirizzo scritto;
- la slide del Wi-Fi `project/slides/entra.html` e la carta del Wi-Fi nell'ultima slide: esistono solo
  col router o con l'hotspot. **Online i telefoni usano i loro dati: niente Wi-Fi**, e chi entrasse
  nella rete `pappagallo` (senza Internet) non vedrebbe il gioco. Online quindi la slide del Wi-Fi
  non c'è proprio: i suoi testi stanno in `slide-wifi.html` e `carta-wifi.html`, accanto a questo file.

## 1. Che rete

| argomento | rete | `MODO_PREDEFINITO` in sala.py | QR | testo sulle slide |
|---|---|---|---|---|
| `online` | Tailscale Funnel | `"online"` | `qr/gioco-online.svg` | `URL_ONLINE` senza `https://` |
| un IP o un nome (togli `http://`, porta e `/` finale) | router | `"router"` | `qr/gioco.svg` | `host:8000` |
| `qui` | router, con l'IP attuale del portatile (`uv run python -c "from sala import indirizzo_locale; print(indirizzo_locale())"`): ricorda che deve essere fisso | `"router"` | `qr/gioco.svg` | `host:8000` |
| `hotspot` | hotspot del Mac | non cambia (si riconosce da solo) | `qr/gioco-hotspot.svg` | `192.168.2.1:8000` |

Se non c'è nessun argomento, chiedi quale rete e fermati.

## 2. Il codice e i QR

1. In `sala.py` imposta `MODO_PREDEFINITO` come nella tabella. Per il router, metti anche il nuovo
   host come default nella riga `INDIRIZZO_ROUTER = os.environ.get("SALA_INDIRIZZO", "…")`.
2. Lancia `uv run python sala.py`: rigenera `qr/` e stampa gli URL di ogni modo. Riporta la riga del
   controllo; un ⚠️ è normale se il server non è acceso o il portatile non è su quella rete.

## 3. Le slide

1. Carica il QR della tabella come asset: Artifact `publish` con `url` del deck, `file_path` =
   `<repo>/qr/…svg`, `asset: true`. Tieni l'id di 32 caratteri che restituisce.
2. Rileggi le slide dal deck, perché l'utente le modifica nell'editor: Artifact `read` con `paths`
   `project/deck.json`, `project/slides/gioco.html`, `project/slides/qr-finale.html`.
   Il risultato dice in quale cartella le ha salvate (chiamala CARTELLA: contiene `project/`).
3. Il QR e l'indirizzo, con lo script accanto a questo file:
   ```bash
   uv run python .claude/skills/aggiorna-qr/aggiorna_slide.py --indirizzo <testo della tabella> --blob <id> CARTELLA/project/slides/gioco.html CARTELLA/project/slides/qr-finale.html
   ```
   Cambia solo il `src` e l'alt del QR del gioco, e l'indirizzo scritto. Se si ferma con ✗, la
   slide è stata ristrutturata a mano: fai le stesse modifiche con Edit e dillo all'utente.
4. Il passo del Wi-Fi, con Edit, solo se cambia il tipo di rete (online ↔ router/hotspot):
   - **verso online:** togli `"entra"` dall'`order` di `deck.json` e cancella la slide (nel publish,
     `"project/slides/entra.html": null`); in `qr-finale.html` togli la `div.qr-carta` del Wi-Fi
     (quella con "collegarsi al Wi-Fi") e l'etichetta "2 · Il gioco" diventa "Il gioco"; in
     `gioco.html` l'occhiello è "Col telefono" e nella nota c'è "Basta la connessione del telefono, niente app."
   - **verso router o hotspot:** crea `CARTELLA/project/slides/entra.html` copiando
     `.claude/skills/aggiorna-qr/slide-wifi.html` e rimetti `"entra"` nell'`order` subito prima di
     `"gioco"`; in `qr-finale.html` rimetti, prima della carta del gioco, il contenuto di
     `carta-wifi.html` e l'etichetta torna "2 · Il gioco"; in `gioco.html` l'occhiello torna
     "Passo 2 di 2" e "Basta la connessione del telefono, niente app." diventa "Niente app e niente account."
5. Pubblica: Artifact `publish` con `url` del deck, `root` = CARTELLA, `file_path` =
   `CARTELLA/project/slides/gioco.html`, `files` = gli altri file modificati o cancellati (percorsi
   relativi a CARTELLA; `null` per cancellare). Se viene rifiutata perché c'è una versione più nuova,
   ripeti dal punto 2.
6. Verifica: rileggi le slide e controlla il nuovo id, il nuovo indirizzo e il passo del Wi-Fi.

## 4. Alla fine

- Di' all'utente quali slide sono cambiate e da quale rete/indirizzo a quale.
- Ricordagli di **riscaricare il PDF** del deck (Share › Export): in sala si proietta quello.
- Online: `uv run python server.py` accende Funnel da solo; la prova vera è un telefono con i dati mobili.
- Proponi il commit di `sala.py` e `qr/`; non farlo senza un sì.
