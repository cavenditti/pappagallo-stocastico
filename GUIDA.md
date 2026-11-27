# 🦜 Il pappagallo stoca**ico: guida per chi conduce

Un'unica esperienza in tre atti (circa 45 minuti), dove ogni atto produce i dati per quello successivo. Niente carta e penna: il pubblico gioca dal telefono, su un sito che gira sul tuo portatile.

| Atto | Cosa fa la sala (dal telefono) | Cosa mostra il notebook | Dati prodotti |
|---|---|---|---|
| 1. Indovina il prossimo token | scrive come continua la frase (da una a tre parole) | token, probabilità, il modello che "vota" 300 volte | i voti |
| 2. Catena di Markov umana | aggiunge parole vedendo solo le ultime 1 o 2 | regole n-gramma, Pappagallo d'oro (perplessità), modello smemorato | le frasi |
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

## La rete: online, con il router come piano B

Modello, sito e notebook girano tutti sul portatile. Il piano A è metterlo **su Internet** con Tailscale Funnel: in sala il segnale c'è, e ognuno usa i dati del proprio telefono, senza Wi-Fi e senza limiti di dispositivi.

| Opzione | Quando va bene |
|---|---|
| **Online con Tailscale Funnel** | il piano A: indirizzo fisso, HTTPS, nessun limite di telefoni. Serve Internet sul portatile |
| Un router qualsiasi (anche uno di casa riciclato, senza Internet) | il piano B. Il nostro Zyxel regge 32 dispositivi |
| Hotspot del Mac (Condivisione Internet) | il piano C: niente hardware in più e indirizzo fisso, ma va provato prima (vedi sotto) |
| Hotspot del telefono | solo per gruppi piccoli: di solito regge una decina di dispositivi al massimo |

Si passa da una all'altra con `/aggiorna-qr online`, `/aggiorna-qr 192.168.1.10` o `/aggiorna-qr hotspot` in Claude Code: cambia il codice, i QR e le slide (anche il passo del Wi-Fi, che online sparisce). Poi riscarica il PDF.

### Online con Tailscale Funnel (piano A)

Funnel pubblica su Internet un server del portatile, a un indirizzo fisso: **https://carlos-macbook-pro.tailefac23.ts.net** (nome del Mac + nome della tailnet, in `URL_ONLINE` in `sala.py`).

- **La prima volta**: l'app Tailscale deve essere installata e con l'accesso fatto, e Funnel va abilitato per la tailnet. Al primo avvio `server.py` stampa il link per farlo (`login.tailscale.com/f/funnel?...`).
- **Poi non c'è niente da fare**: `uv run python server.py` accende Funnel e lo spegne quando chiudi il server. In cima deve comparire ✅ "porta a questo portatile, via Internet".
- **Il portatile ha bisogno di Internet**: il Wi-Fi del locale, o il telefono via USB. Il traffico è minimo: 45 telefoni che chiedono lo stato ogni 1,5 secondi fanno pochi KB al secondo.
- **La prova**: un telefono con i **dati mobili** (Wi-Fi spento) inquadra il QR della slide 3. Dal portatile stesso l'indirizzo passa per la tailnet, quindi non prova la strada pubblica.
- **Sicurezza**: online chiunque abbia l'indirizzo può aprire la pagina e votare, ma non può comandare il gioco. I comandi del palco (aprire le votazioni, avviare le catene, azzerare) vogliono un codice segreto che `server.py` scrive in `.palco` a ogni avvio e che il notebook legge da lì.
- **Se Internet cade** in sala: `/aggiorna-qr 192.168.1.10` (serve Internet per le slide, quindi meglio prepararsi il PDF del piano B in anticipo), oppure fai inquadrare il QR in cima al notebook.

### Il router: cosa impostare

Col router (piano B) le slide stampano due QR fissi: il primo per entrare nella rete, il secondo per aprire il gioco. Va bene un router di casa qualsiasi, anche senza Internet. Nelle sue impostazioni:

1. **Wi-Fi `pappagallo`, password `pydataroma` (WPA2).** È il QR della slide del Wi-Fi, "inquadra e collegati", che `/aggiorna-qr` rimette nel deck quando si passa al router.
2. **Spazio per tutti:** l'intervallo DHCP deve avere almeno 60 indirizzi. Alcuni router di fabbrica ne danno 50, e con 45 telefoni più il portatile si è al limite.
3. **Niente isolamento dei client:** usa la rete Wi-Fi principale, non quella "ospiti", che di solito impedisce ai telefoni di vedere il portatile.
4. **Un indirizzo fisso per il portatile.** È quello del QR del gioco. Ci sono tre strade, dalla più comoda:
   - **un nome**, se il router lo permette. Su OpenWrt: Network › DHCP and DNS › Static Leases, con Hostname `pappagallo`, e diventa `pappagallo.lan`. Su una FRITZ!Box, il nome del dispositivo funziona già come `nome.fritz.box`.
   - **una prenotazione DHCP** sul router: il portatile riceve sempre lo stesso IP. La trovi come "prenotazione indirizzo", "DHCP statico" o simili; su FRITZ!Box è "Assegna sempre lo stesso indirizzo IPv4 a questo dispositivo". Su macOS, per questa rete imposta "Indirizzo Wi-Fi privato" su **Fisso** (o disattivalo), altrimenti il router non riconosce il Mac.
   - **un IP manuale sul Mac**, senza toccare il router: in Impostazioni di Sistema › Wi-Fi › (la rete `pappagallo`) › Dettagli › TCP/IP, scegli "Utilizzo di DHCP con indirizzo manuale" e metti un indirizzo **fuori** dall'intervallo DHCP del router (per esempio `.200` se il router assegna da `.100` a `.199`).

**Poi scrivi l'indirizzo nel codice e rigenera i QR.** In `sala.py` imposta `INDIRIZZO_ROUTER` (un nome come `pappagallo.lan` oppure l'IP, per esempio `192.168.1.200`) e lancia:

```bash
uv run python sala.py
```

Scrive `qr/wifi`, `qr/gioco` e `qr/gioco-hotspot` (in SVG e PNG). Nel deck, sostituisci il QR del gioco nella slide del gioco e in quella finale con il nuovo `qr/gioco`. Le stesse impostazioni si possono dare con le variabili `SALA_INDIRIZZO`, `SALA_WIFI` e `SALA_WIFI_PASSWORD`.

**Oppure fai tutto in un colpo con Claude Code**, da questa cartella: `/aggiorna-qr 192.168.1.200` (o `/aggiorna-qr qui` per l'IP che il portatile ha adesso). Imposta `INDIRIZZO_ROUTER`, rigenera i QR, carica il nuovo QR nel deck e aggiorna QR e indirizzo scritto nelle slide 4 e 9, lasciando com'è il resto delle slide. Serve Internet, quindi fallo prima della serata, e dopo **riscarica il PDF**.

**Controllo:** all'avvio, il notebook e `server.py` verificano che l'indirizzo delle slide arrivi proprio a questo portatile. Se va tutto bene compare ✅. Altrimenti il notebook mostra un avviso e un QR di riserva via IP, che funziona sempre ma non è quello delle slide.

Se il portatile ha più interfacce di rete e il notebook sceglie quella sbagliata, forzala con `SALA_HOST=192.168.x.y`.

### Il nostro router: Zyxel VMG8823-B50B

È un modem VDSL degli operatori (Infostrada, Tiscali, Fastweb), ma senza linea telefonica fa benissimo da router della sala: Wi-Fi e DHCP non hanno bisogno di Internet. Il LED di Internet resta spento o rosso, ed è normale. Il piano: il portatile ha sempre **`192.168.1.10`**, quindi il QR del gioco è `http://192.168.1.10:8000`. Un IP non dipende dal DNS dei telefoni, quindi è la scelta più robusta.

**Da fare a casa, il giorno prima:**

1. **Reset di fabbrica**, se il router è già stato usato: a router acceso, tieni premuto il tasto **RESET** sul retro per più di 10 secondi, finché le luci non ripartono.
2. **Collega il Mac con un cavo** a una porta LAN gialla (serve un adattatore USB-C/Ethernet). In sala resterà così: il cavo non toglie banda ai 45 telefoni e l'indirizzo MAC dell'adattatore non cambia mai. Senza adattatore va bene anche il Wi-Fi, ma per la rete `pappagallo` imposta "Indirizzo Wi-Fi privato" su **Fisso**.
3. Apri **http://192.168.1.1** e accedi con utente **`admin`** e la password stampata sull'etichetta sotto il router. Con il firmware dell'operatore qualche menu può essere nascosto, ma quelli qui sotto di solito ci sono.

| Menu | Cosa impostare |
|---|---|
| Network Setting › Wireless › General | SSID **`pappagallo`**, sicurezza **WPA2-PSK**, password **`pydataroma`**; stesso nome e password sulle due bande (2,4 e 5 GHz) |
| Network Setting › Wireless (Others / Advanced) | se c'è un limite di client per rete, almeno **64**; a 5 GHz un canale fisso fra **36 e 48** (gli altri sono canali DFS: se il router sente un radar, la rete sparisce per un minuto) |
| Network Setting › Wireless › WPS | WPS **spento** |
| Network Setting › Wireless › Guest/More AP | nessuna rete ospiti: si usa solo `pappagallo` |
| Network Setting › Home Networking › LAN Setup | IP **`192.168.1.1`**, maschera **`255.255.255.0`** (sono quelli di fabbrica); server DHCP attivo, con almeno 60 indirizzi |
| Network Setting › Home Networking › Static DHCP | aggiungi l'indirizzo MAC del portatile → **`192.168.1.10`** |
| Network Setting › DNS › DNS Entry (facoltativo) | `pappagallo.lan` → `192.168.1.10`, per chi scrive l'indirizzo a mano e preferisce un nome |

L'indirizzo MAC giusto è quello dell'interfaccia con cui il Mac sta sul router: "Ethernet Address" della voce dell'adattatore (o del Wi-Fi) in

```bash
networksetup -listallhardwareports
```

4. Scollega e ricollega il cavo, poi controlla che il Mac abbia preso `192.168.1.10` (`en7` è un esempio: usa la "Device" della lista di prima):

   ```bash
   ipconfig getifaddr en7
   ```

5. Le slide devono puntare a quell'indirizzo: in Claude Code, `/aggiorna-qr 192.168.1.10` (serve Internet, quindi fallo dalla rete di casa), poi riscarica il PDF.
6. **La prova:** con il Mac sul router, avvia `uv run python server.py`. Deve dire ✅. Poi collega 3 o 4 telefoni inquadrando i QR delle slide.

**Attenzione al Mac con due reti.** Se il Mac è sul router con il cavo e intanto anche sul Wi-Fi di casa, macOS può usare il router (che non ha Internet) per tutto, e Claude o il browser smettono di funzionare. Per configurare il router basta il cavo; per usare Internet, scollegalo. In sala spegni il Wi-Fi del Mac, oppure collegalo a `pappagallo`.

### Piano B: l'hotspot del Mac

Il Mac può creare da sé la rete `pappagallo` con Condivisione Internet. Il vantaggio: il Mac è il router, quindi il suo indirizzo è fisso (di solito `192.168.2.1`) e non c'è niente da configurare per il nome. Il codice se ne accorge da solo: quando la condivisione è attiva passa in modo **hotspot** e usa `http://192.168.2.1:8000`.

I limiti:

- **Serve una connessione da condividere.** Senza, macOS può smettere di trasmettere la rete. Usa l'iPhone collegato via USB. I telefoni del pubblico non usano Internet: parlano solo con il portatile.
- **Apple non dichiara quanti dispositivi regge.** È un'antenna sola, quella del portatile che intanto fa girare il modello: con 40 telefoni va provato.
- **Il Wi-Fi del Mac diventa la rete del gioco,** quindi il portatile non può collegarsi ad altri Wi-Fi nel frattempo.

**Come si accende:**

1. Collega l'iPhone via USB, con l'hotspot personale attivo.
2. In Impostazioni di Sistema › Generali › Condivisione › Condivisione Internet › ⓘ: "Condividi la connessione da" → **iPhone USB**; "Ai dispositivi che utilizzano" → **Wi-Fi**.
3. In Opzioni Wi-Fi: nome **`pappagallo`**, sicurezza WPA2/WPA3 Personal, password **`pydataroma`**. Poi attiva Condivisione Internet.
4. Controlla l'indirizzo del Mac sulla nuova rete. Deve essere `192.168.2.1`; se è diverso, imposta `SALA_HOTSPOT_IP`, rigenera i QR e aggiorna le slide:

   ```bash
   ipconfig getifaddr bridge100
   ```

5. Avvia `server.py` e il notebook come al solito: in cima deve comparire "✅ Rete: **hotspot del Mac**".

**Le slide:** la slide del gioco e quella finale mostrano un indirizzo solo. Per passare all'hotspot, in Claude Code lancia `/aggiorna-qr hotspot`: mette `192.168.2.1:8000` e il suo QR nelle due slide. Per tornare al router, `/aggiorna-qr <indirizzo del router>`. Con l'hotspot il portatile ha Internet (dall'iPhone), quindi si può fare anche sul posto; poi riscarica il PDF. La slide del Wi-Fi è la stessa nei due casi. In emergenza, il QR in cima al notebook è sempre quello giusto per la rete attuale.

**La prova a casa (obbligatoria):**

1. Accendi la condivisione e collega 3–4 telefoni al gioco.
2. Lancia anche la sala finta, per avere carico vero:

   ```bash
   uv run python simula_sala.py --pilota
   ```

3. Spegni i dati mobili dell'iPhone di uscita: la rete `pappagallo` deve restare su, e i telefoni devono continuare a giocare. Se cade, in birreria serve il router.

### E un captive portal?

L'idea sarebbe che, appena entrati nel Wi-Fi, il telefono apra da solo la pagina del gioco. Con l'hotspot di macOS non è praticabile: Condivisione Internet richiede una connessione da condividere e gestisce DHCP e DNS a modo suo, senza impostazioni per un portale. Con un router OpenWrt si può fare, mandando tutto il DNS al portatile e servendo il gioco sulla porta 80. Però le finestre "captive" di iOS e Android sono browser ridotti, che la gente chiude con un tocco. Due QR ben grandi sono più affidabili.

---

## Preparazione (il giorno prima, con Internet)

```bash
uv sync                                  # torch, transformers, marimo, fastapi
uv run hf download Qwen/Qwen3-0.6B-Base  # ~1,2 GB: va scaricato a casa
```

**Er pappagallo romano** (il bis): si addestra a casa, una volta sola, e finisce in `modelli/pappagallo-romano/` (circa 1,2 GB, fuori da git).

```bash
uv run python romano.py scarica
```

```bash
uv run python romano.py addestra
```

Il primo scarica tre libri dell'Ottocento in romanesco, di pubblico dominio, da Liber Liber (~490 KB): i sonetti del Belli e gli *Usi, costumi e pregiudizi del popolo di Roma* di Zanazzo. Il secondo addestra il modello per qualche minuto, mescolando quei testi con il romanaccio di oggi di `romanaccio/frasi.txt`: aggiungetene pure, una frase per riga, poi riaddestrate. Le strofe sconce del Belli restano fuori. Per vedere com'è venuto:

```bash
uv run python romano.py prova "Lo sai chi te saluta tanto?"
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
2. Avvia `uv run python server.py`: online accende anche Funnel; poi stampa l'indirizzo, un QR code e il controllo sull'indirizzo delle slide (✅ o ⚠️). Se macOS chiede di accettare connessioni in entrata per Python, rispondi **Consenti**.
3. Avvia `HF_HUB_OFFLINE=1 uv run marimo edit pappagallo.py` e porta lo zoom del browser al 125–150%. In alto, il notebook mostra il QR del gioco (col router anche quello del Wi-Fi), `🟢 dati dal sito` e quanti telefoni sono collegati.
4. Proietta le slide (dal PDF).

### Slide 1–3: benvenuto e collegamento (5')
Online basta la slide 3: si inquadra il QR con i dati del telefono. Col router `/aggiorna-qr` rimette prima la slide del Wi-Fi, e i passi diventano due. Al primo accesso il sito chiede un nome o un soprannome: serve per la classifica dei Pappagalli d'oro, e si può cambiare in fondo alla pagina. Resta sulla 4 finché il contatore dei telefoni collegati nel notebook non smette di salire. Molti telefoni avvisano che la rete non ha Internet: bisogna dire di restare collegati. Se un Android non apre la pagina, spesso basta disattivare per un attimo i dati mobili.

L'ultima slide (la 8) mostra di nuovo il QR del gioco: lasciala su un secondo schermo, o tornaci fra un atto e l'altro, per chi arriva in ritardo.

### Atto 1: Indovina il prossimo token (15')
1. Scegli la frase nel menu, poi premi **▶️ Apri la votazione sui telefoni**. Si risponde con **una, due o tre parole**; se qualcuno ne scrive di più, il sito tiene le prime tre.
2. Il grafico della sala si riempie dal vivo con le risposte intere, aggiornandosi ogni 2 secondi.
3. Premi **⏹ Chiudi**, poi **🦜 Svela il modello**. Ogni clic su Svela è una nuova votazione del modello. Compaiono due cose:
   - il confronto sulla **prima parola**, con la percentuale di accordo. È il confronto onesto: il modello sceglie un token alla volta, e "si blocca" per lui comincia con "si";
   - le **risposte intere**, una colonna per voi e una per il modello (che si ferma alla prima pausa, al massimo dopo tre parole). In grassetto quelle date da entrambi.
4. Seguono la tabella delle vostre risposte spezzate in token, con la loro probabilità esatta per il modello, e lo slider della temperatura.
5. Per il secondo giro, cambia frase e ripeti. Quella sul codice che non funziona più, con un pubblico PyData, funziona sempre.

Spunto: anche la tastiera del telefono suggerisce la parola successiva, ed è un altro pappagallo stocastico.

### Atto 2: La catena di Markov umana (15')
1. Imposta la parola iniziale (di default `traffico`), il numero di catene e la lunghezza, poi premi **▶️ Avvia le catene sui telefoni**. Le catene pari mostrano 1 parola, le dispari 2.
2. Sui telefoni compare **✍️ Tocca a me**: chi lo preme riceve una catena libera e ha 60 secondi per scrivere. La tabella di avanzamento non rivela il contenuto.
3. Quando le catene sono complete, premi **⏹ Chiudi** e poi **🎭 Rivela le frasi**.
4. Seguono, in ordine: le regole della sala, la sala come generatore (le ✨ sono frasi che nessuno ha scritto), il grafico "più contesto, meno sorpresa", il **🦜 Pappagallo d'oro** e il pappagallo smemorato, che parte solo quando premi **🦜 Togli la memoria al modello** (una ventina di secondi, durante i quali il notebook non risponde).
5. **🏆 Proclama i Pappagalli d'oro**: il modello misura la sorpresa di ogni parola scritta da ognuno, cioè le risposte dell'Atto 1 e le parole delle catene, ciascuna con il contesto che vedeva chi l'ha scritta. Poi fa la media per persona: vincono la perplessità più alta (🏆, il pappagallo più imprevedibile) e la più bassa (🦜, il più prevedibile), con un Pappagallo d'oro e una birra a testa. In gara chi ha scritto almeno 3 parole. Il calcolo prende qualche secondo; i nomi sono quelli scelti sul telefono.

Se premi due volte **Avvia**, le catene vecchie non si perdono: finiscono in `archivio_catene` dentro `sala.json`.

### Atto 3: La sala addestra il modello (10–15')
- **λ:** muovi lo slider. Le parole su sfondo blu vengono dalla sala, e il modello prova a ricucirle nel contesto.
- **🧠 Addestra con la sala:** addestra una *copia* del modello sui voti e sulle frasi, mostrando la barra di avanzamento e la loss. Seguono il grafico Sala / Modello prima / Modello dopo e il prompt mai visto ("Ieri sera al pub, il mio capo").
- **Manopole:** passi e learning rate stanno accanto al bottone. Per un modello più "ubriaco di sala", alza l'uno o l'altro.

---

### Bis: er pappagallo romano (5')
Dopo il "Grazie!", se c'è tempo: premi **🏛️ Sveja er pappagallo romano** e scrivi una frase, anche suggerita dalla sala. Il grafico mette a confronto la parola successiva secondo il modello normale e secondo quello romano, e sotto ognuno dei due continua la frase. Stesso modello, altri dati: è l'Atto 3 in grande. Poi **🧠 Addestra er romano co' la sala**: addestra una copia del romano sugli stessi esempi dell'Atto 3 (voti e catene, con gli stessi passi e learning rate) e lo mette contro il Qwen 0.6B originale, sia sulla frase dell'Atto 1 (con l'accordo con la sala) sia sulla frase libera. Servono le catene già rivelate.

## Se qualcosa va storto

| Problema | Soluzione |
|---|---|
| I telefoni non aprono la pagina | stessa rete? Wi-Fi che isola i client? firewall di macOS? Su Android, disattiva i dati mobili |
| Il sito si è spento | rilancia `server.py`: lo stato è salvato in `sala.json`, non si perde niente |
| Il sito proprio non va | il notebook passa da solo ai dati di esempio (in fondo al notebook) e lo segnala con `🔴` |
| Il modello è lento | in `il_modello_vota(...)` metti `n=150`, oppure passa a `Qwen/Qwen2.5-0.5B` in `MODEL_ID` |
| La memoria si esaurisce durante l'addestramento | chiudi le altre app oppure abbassa i passi |
| Il risultato è noioso | premi 🎲 **Rilancia** (per il pappagallo smemorato, di nuovo il suo bottone): è un campionamento, ogni volta esce qualcosa di diverso |

> Il modello alternativo `sapienzanlp/Minerva-350M-base-v1.0` (italiano nativo, Sapienza) è più "romano", ma su Hugging Face bisogna accettarne i termini e fare `uv run hf auth login`.
