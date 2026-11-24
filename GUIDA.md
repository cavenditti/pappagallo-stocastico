# 🦜 Il pappagallo stoca**ico: guida per chi conduce

Un'unica esperienza in tre atti (circa 45 minuti), dove ogni atto produce i dati per quello successivo. Niente carta e penna: il pubblico gioca dal telefono, su un sito che gira sul tuo portatile.

| Atto | Cosa fa la sala (dal telefono) | Cosa mostra il notebook | Dati prodotti |
|---|---|---|---|
| 1. Indovina il prossimo token | vota la parola successiva | token, probabilità, il modello che "vota" 300 volte | i voti |
| 2. Catena di Markov umana | aggiunge parole vedendo solo le ultime 1 o 2 | regole n-gramma, Premio Perplessità, modello smemorato | le frasi |
| 3. La sala addestra il modello | guarda (e ride) | interpolazione λ, poi 20 passi di backprop | un modello cambiato |

Il filo conduttore: **la sala è un modello linguistico**. Nell'Atto 1 campiona da una distribuzione, nell'Atto 2 è un n-gramma, nell'Atto 3 diventa i dati di addestramento.

## Cosa c'è nella cartella

| File | A cosa serve |
|---|---|
| `pappagallo.py` | il notebook marimo: lo proietti, ed è anche il pannello di controllo |
| `server.py` + `sito/index.html` | il sito per i telefoni (voti e catene) |
| `sala.py` | il collegamento fra notebook e sito |
| `aiuti.py` | grafici e utilità di testo |
| `simula_sala.py` | una sala finta, per le prove |

Le slide per spiegare il gioco sono un deck su claude.ai (link nella chat). Per proiettarle senza rete, **scaricale in PDF** il giorno prima (Share › Export).

---

## La rete: niente Internet, ma una rete comune

Telefoni e portatile devono stare sulla **stessa rete Wi-Fi**. Internet non serve: modello, sito e notebook girano tutti sul portatile.

| Opzione | Quando va bene |
|---|---|
| **Router da viaggio** (alimentato via USB, nessuna SIM) | la scelta sicura per 30–50 persone |
| Hotspot del telefono | solo per gruppi piccoli: di solito regge una decina di dispositivi al massimo |
| Wi-Fi della birreria | spesso isola i dispositivi fra loro, e allora i telefoni non vedono il portatile. Provalo prima |

### Le due cose da impostare sul router

Le slide stampano due QR fissi: il primo per entrare nella rete, il secondo per aprire il gioco. Il router va configurato perché tutti e due funzionino.

1. **Wi-Fi `pappagallo`, password `pydataroma` (WPA2).** È il QR della slide 3, "inquadra e collegati".
2. **Il nome `pappagallo.lan` deve puntare al portatile.** È il QR della slide 4, `http://pappagallo.lan:8000`. Sul router fai due cose: una *prenotazione DHCP* (il portatile riceve sempre lo stesso IP) e un *nome host* `pappagallo` per quell'IP. Su OpenWrt/LuCI le trovi in Network › DHCP and DNS › Static Leases (con Hostname `pappagallo`); i router GL.iNet hanno di solito le stesse voci nell'interfaccia avanzata.

**Controllo:** all'avvio, il notebook e `server.py` verificano che `pappagallo.lan` arrivi proprio a questo portatile. Se va tutto bene compare ✅. Altrimenti il notebook mostra un avviso e un QR di riserva via IP, che funziona sempre ma non è quello delle slide.

**Per cambiare rete o indirizzo:** imposta `SALA_WIFI`, `SALA_WIFI_PASSWORD` e `SALA_URL`, poi rigenera i QR per le slide con il comando qui sotto. Scrive `qr/wifi.svg|png` e `qr/gioco.svg|png`; nel deck, sostituisci le immagini dei QR nelle slide 3, 4 e 9.

```bash
uv run python sala.py
```

Se il portatile ha più interfacce di rete e il notebook sceglie quella sbagliata, forzala con `SALA_HOST=192.168.x.y`.

### E un captive portal?

L'idea sarebbe che, appena entrati nel Wi-Fi, il telefono apra da solo la pagina del gioco. Con l'hotspot di macOS non è praticabile: Condivisione Internet richiede una connessione da condividere e gestisce DHCP e DNS a modo suo, senza impostazioni per un portale. Con un router OpenWrt si può fare, mandando tutto il DNS al portatile e servendo il gioco sulla porta 80. Però le finestre "captive" di iOS e Android sono browser ridotti, che la gente chiude con un tocco. Due QR ben grandi sono più affidabili.

---

## Preparazione (il giorno prima, con Internet)

```bash
uv sync                                  # torch, transformers, marimo, fastapi
uv run hf download Qwen/Qwen3-0.6B-Base  # ~1,2 GB: va scaricato a casa
```

**Prova generale** con una sala finta, in tre terminali:

```bash
uv run python server.py
```

```bash
HF_HUB_OFFLINE=1 uv run marimo edit pappagallo.py
```

```bash
uv run python simula_sala.py
```

Il terzo comando collega 30 telefoni finti, che votano quando apri una votazione e scrivono quando avvii le catene. Con `--pilota` la prova va avanti da sola. Alla fine svuota i dati di prova; il file vecchio resta come backup:

```bash
uv run python -c "from sala import Sala; Sala().azzera()"
```

Una prova completa di tutto il notebook (`uv run python pappagallo.py`) dura circa 3 minuti su questo portatile.

---

## La sera

1. Accendi il router e collega il portatile.
2. Avvia `uv run python server.py`: stampa l'indirizzo, un QR code e il controllo su `pappagallo.lan` (✅ o ⚠️). Se macOS chiede di accettare connessioni in entrata per Python, rispondi **Consenti**.
3. Avvia `HF_HUB_OFFLINE=1 uv run marimo edit pappagallo.py` e porta lo zoom del browser al 125–150%. In alto, il notebook mostra i due QR (prima il Wi-Fi, poi il gioco), `🟢 dati dal sito` e quanti telefoni sono collegati.
4. Proietta le slide (dal PDF).

### Slide 1–4: benvenuto e collegamento (5')
La slide 3 è il passo 1 (il Wi-Fi), la slide 4 il passo 2 (il gioco). Resta sulla 4 finché il contatore dei telefoni collegati nel notebook non smette di salire. Molti telefoni avvisano che la rete non ha Internet: bisogna dire di restare collegati. Se un Android non apre la pagina, spesso basta disattivare per un attimo i dati mobili.

L'ultima slide (la 9) mostra di nuovo i due QR: lasciala su un secondo schermo, o tornaci fra un atto e l'altro, per chi arriva in ritardo.

### Atto 1: Indovina il prossimo token (15')
1. Scegli la frase nel menu, poi premi **▶️ Apri la votazione sui telefoni**.
2. Il grafico della sala si riempie dal vivo, aggiornandosi ogni 2 secondi.
3. Premi **⏹ Chiudi**, poi **🦜 Svela il modello**: ecco il confronto e la percentuale di accordo. Ogni clic su Svela è una nuova votazione del modello.
4. Seguono la tabella delle vostre parole spezzate in token e lo slider della temperatura.
5. Per il secondo giro, cambia frase e ripeti. Quella sul codice che non funziona più, con un pubblico PyData, funziona sempre.

Spunto: anche la tastiera del telefono suggerisce la parola successiva, ed è un altro pappagallo stocastico.

### Atto 2: La catena di Markov umana (15')
1. Imposta la parola iniziale (di default `traffico`), il numero di catene e la lunghezza, poi premi **▶️ Avvia le catene sui telefoni**. Le catene pari mostrano 1 parola, le dispari 2.
2. Sui telefoni compare **✍️ Tocca a me**: chi lo preme riceve una catena libera e ha 60 secondi per scrivere. La tabella di avanzamento non rivela il contenuto.
3. Quando le catene sono complete, premi **⏹ Chiudi** e poi **🎭 Rivela le frasi**.
4. Seguono, in ordine: le regole della sala, la sala come generatore (le ✨ sono frasi che nessuno ha scritto), il **🏆 Premio Perplessità** (la prima frase vince la birra, l'ultima il 🦜 Pappagallo d'oro), il grafico "più contesto, meno sorpresa" e il pappagallo smemorato.

Se premi due volte **Avvia**, le catene vecchie non si perdono: finiscono in `archivio_catene` dentro `sala.json`.

### Atto 3: La sala addestra il modello (10–15')
- **λ:** muovi lo slider. Le parole su sfondo blu vengono dalla sala, e il modello prova a ricucirle nel contesto.
- **🧠 Addestra con la sala:** addestra una *copia* del modello sui voti e sulle frasi, mostrando la barra di avanzamento e la loss. Seguono il grafico Sala / Modello prima / Modello dopo e il prompt mai visto ("Ieri sera al pub, il mio capo").
- **Manopole:** passi e learning rate stanno accanto al bottone. Per un modello più "ubriaco di sala", alza l'uno o l'altro.

---

## Se qualcosa va storto

| Problema | Soluzione |
|---|---|
| I telefoni non aprono la pagina | stessa rete? Wi-Fi che isola i client? firewall di macOS? Su Android, disattiva i dati mobili |
| Il sito si è spento | rilancia `server.py`: lo stato è salvato in `sala.json`, non si perde niente |
| Il sito proprio non va | il notebook passa da solo ai dati di esempio (in fondo al notebook) e lo segnala con `🔴` |
| Il modello è lento | in `il_modello_vota(...)` metti `n=150`, oppure passa a `Qwen/Qwen2.5-0.5B` in `MODEL_ID` |
| La memoria si esaurisce durante l'addestramento | chiudi le altre app oppure abbassa i passi |
| Il risultato è noioso | premi 🎲 **Rilancia**: è un campionamento, ogni volta esce qualcosa di diverso |

> Il modello alternativo `sapienzanlp/Minerva-350M-base-v1.0` (italiano nativo, Sapienza) è più "romano", ma su Hugging Face bisogna accettarne i termini e fare `uv run hf auth login`.
