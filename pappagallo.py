import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Il pappagallo stoca**ico")


@app.cell
def _():
    import copy
    import gc
    import math
    import random
    from collections import Counter, defaultdict

    import marimo as mo
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from aiuti import (accordo, confronta, distribuzione, elenca_voti, frase_evidenziata, grafico_loss,
                       grafico_perplessita, grafico_token, leggi_risposte, leggi_voti, numero, parole, percento,
                       prima_parola, risposta_del_modello, stile, unisci, visibile)
    from sala import WIFI_NOME, WIFI_PASSWORD, Sala, modo, qr_svg, qr_wifi_svg, url_da_mostrare, url_gioco

    stile()
    IN_NOTEBOOK = mo.running_in_notebook()  # da script (prova generale) i bottoni si considerano premuti
    return (
        AutoModelForCausalLM,
        AutoTokenizer,
        Counter,
        IN_NOTEBOOK,
        Sala,
        WIFI_NOME,
        WIFI_PASSWORD,
        accordo,
        confronta,
        copy,
        defaultdict,
        distribuzione,
        elenca_voti,
        frase_evidenziata,
        gc,
        grafico_loss,
        grafico_perplessita,
        grafico_token,
        leggi_risposte,
        leggi_voti,
        math,
        mo,
        modo,
        numero,
        parole,
        percento,
        prima_parola,
        qr_svg,
        qr_wifi_svg,
        random,
        risposta_del_modello,
        torch,
        unisci,
        url_da_mostrare,
        url_gioco,
        visibile,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 🦜 Il pappagallo stoca\*\*ico
    ### La sala contro il modello: tre atti, una birra, zero metafore

    1. **Indovina il prossimo token.** Votate la parola successiva dal telefono, poi il modello "vota" 300 volte. Pescate dalla stessa distribuzione?
    2. **Catena di Markov umana.** Ognuno vede solo l'ultima parola (o le ultime due) e aggiunge la successiva. Insieme diventate un modello a n-grammi.
    3. **La sala addestra il modello.** Con le vostre regole e le vostre frasi cambiamo un LLM vero: prima con un trucco da dieci righe, poi con un mini-batch di backpropagation.

    Il modello è piccolo, aperto, e gira su questo portatile. Il sito gira qui pure lui: non serve Internet.
    """)
    return


@app.cell
def _(AutoModelForCausalLM, AutoTokenizer, mo, torch):
    MODEL_ID = "Qwen/Qwen3-0.6B-Base"  # "base", non "instruct": vogliamo il pappagallo, non l'assistente
    # alternative: 
        # "Qwen/Qwen2.5-0.5B"
        # "sapienzanlp/Minerva-350M-base-v1.0" (italiano nativo, termini da accettare su HF)
    DEVICE = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"

    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    tok.padding_side = "right"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, dtype=torch.float32).to(DEVICE).eval()

    mo.md(f"`{MODEL_ID}` · **{model.num_parameters() / 1e6:.0f} milioni** di parametri · `{DEVICE}`")
    return DEVICE, model, tok


@app.cell
def _(
    Sala,
    WIFI_NOME,
    WIFI_PASSWORD,
    mo,
    modo,
    qr_svg,
    qr_wifi_svg,
    url_da_mostrare,
    url_gioco,
):
    sito = Sala()
    # Le slide puntano a un indirizzo fisso (router: pappagallo.lan, hotspot del Mac: 192.168.2.1):
    # se su questa rete non arriva qui, mostriamo l'indirizzo via IP.
    _url, _ok, _motivo = url_da_mostrare()
    _rete = {"router": "router da viaggio", "hotspot": "hotspot del Mac"}[modo()]
    aggiorna = mo.ui.refresh(options=["1s", "2s", "5s"], default_interval="2s", label="live")
    _avviso = (mo.md(f"✅ Rete: **{_rete}**. Il QR delle slide funziona: {_motivo}.") if _ok else
               mo.callout(mo.md(f"**Rete: {_rete}. Il QR del gioco sulle slide (`{url_gioco()}`) non porta qui**: "
                                f"{_motivo}. Fai inquadrare questo QR, oppure sistema la rete (vedi GUIDA.md)."),
                          kind="warn"))
    mo.vstack([
        mo.md("## 📱 Entra nella sala"),
        mo.hstack([
            mo.vstack([mo.Html(qr_wifi_svg(scala=6)),
                       mo.md(f"**1 · Wi-Fi** `{WIFI_NOME}`<br>password `{WIFI_PASSWORD}`")], align="center"),
            mo.vstack([mo.Html(qr_svg(_url, scala=6)),
                       mo.md(f"**2 · Il gioco**<br>`{_url}`")], align="center"),
            aggiorna,
        ], justify="start", align="center", gap=3),
        _avviso,
    ])
    return aggiorna, sito


@app.cell
def _(DEMO_CATENE, DEMO_VOTI, sito):
    def dati_sala() -> dict:
        """I dati veri dal sito; se il sito è spento, quelli di esempio (in fondo al notebook)."""
        dati = sito.dati()
        if dati is not None:
            return {**dati, "fonte": "🟢 dati dal sito"}
        return {"fase": None, "prompt": None, "voti": DEMO_VOTI, "catene": DEMO_CATENE, "persone": 0,
                "connessi": 0, "fonte": "🔴 sito spento (`uv run python server.py`): uso i dati di esempio"}

    return (dati_sala,)


@app.cell
def _(aggiorna, dati_sala, mo):
    aggiorna  # a ogni tick questa cella si ricalcola
    _d = dati_sala()
    mo.md(f"{_d['fonte']} · 📱 **{_d['connessi']}** telefoni collegati ora · {_d['persone']} persone hanno giocato")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Atto 1: Indovina il prossimo token

    Sul telefono compare una frase troncata. Scrivete come continua: **una, due o tre parole**.
    """)
    return


@app.cell
def _(mo):
    FRASI_TRONCATE = [
        "A Roma, quando piove, il traffico",
        "Il codice funzionava ieri sera, ma stamattina",
        "La cosa più bella di Python è",
        "Mia nonna dice sempre che la pizza",
        "Dopo la terza birra, ogni data scientist",
    ]
    prompt_ui = mo.ui.dropdown(FRASI_TRONCATE, value=FRASI_TRONCATE[0], label="Frase troncata")
    prompt_ui
    return (prompt_ui,)


@app.cell
def _(mo, prompt_ui, sito):
    PROMPT = prompt_ui.value
    apri_voto = mo.ui.button(label="▶️ Apri la votazione sui telefoni", kind="success",
                             on_click=lambda _: sito.fase("vota", prompt=PROMPT))
    chiudi_voto = mo.ui.button(label="⏹ Chiudi la votazione", on_click=lambda _: sito.fase("attesa"))
    mo.vstack([mo.md(f"# {PROMPT}…"), mo.hstack([apri_voto, chiudi_voto], justify="start")])
    return (PROMPT,)


@app.cell
def _(PROMPT, aggiorna, confronta, dati_sala, distribuzione, leggi_risposte, mo):
    aggiorna
    _d = dati_sala()
    _voti = _d["voti"].get(PROMPT, [])
    _aperta = _d["fase"] == "vota" and _d["prompt"] == PROMPT
    _intestazione = mo.md(("🗳️ **votazione aperta**" if _aperta else "votazione chiusa") + f" · {len(_voti)} voti")
    if _voti:
        _grafico = confronta({"Sala": distribuzione(leggi_risposte(_voti))}, f"La sala: «{PROMPT}…»")
    else:
        _grafico = mo.md("*Ancora nessun voto: inquadrate il QR code e votate.*")
    mo.vstack([_intestazione, _grafico])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Cosa vede davvero il modello

    Il modello non vede parole, vede **token**. E per *ognuno* dei token del suo vocabolario calcola una probabilità.
    """)
    return


@app.cell
def _(PROMPT, mo, numero, tok, visibile):
    _ids = tok(PROMPT).input_ids
    mo.md("&nbsp; ".join(f"`{visibile(tok.decode([i]))}`" for i in _ids)
          + f"\n\n{len(_ids)} token · vocabolario di {numero(len(tok))} token")
    return


@app.cell
def _(DEVICE, tok, torch):
    @torch.no_grad()
    def prossimo_token(m, prompt: str, temperatura: float = 1.0) -> torch.Tensor:
        # La distribuzione sul prossimo token: un numero per ogni token del vocabolario.
        ids = tok(prompt, return_tensors="pt").input_ids.to(DEVICE)
        logits = m(ids).logits[0, -1]  # punteggi grezzi nell'ultima posizione
        return torch.softmax(logits / temperatura, dim=-1)

    def top_token(m, prompt: str, k: int = 15, temperatura: float = 1.0):
        valori, indici = prossimo_token(m, prompt, temperatura).topk(k)
        return [(tok.decode([i]), v) for i, v in zip(indici.tolist(), valori.tolist())]

    return (top_token,)


@app.cell
def _(PROMPT, grafico_token, model, top_token):
    grafico_token(top_token(model, PROMPT), f"I 15 token più probabili dopo «{PROMPT}»")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Ora vota il modello

    La sala ha votato una volta a testa. Il modello vota **300 volte**: ogni voto è un'estrazione casuale dalla sua distribuzione (temperatura 1, nessun filtro).
    È esattamente quello che fa quando "scrive".

    Il confronto vero è sulla **prima parola**: il modello sceglie un token alla volta, e la vostra prima parola è il vostro primo "token". Poi guardiamo anche le risposte intere.
    """)
    return


@app.cell
def _(Counter, DEVICE, prima_parola, tok, torch):
    @torch.no_grad()
    def il_modello_continua(m, prompt: str, n: int = 300, temperatura: float = 1.0) -> list[str]:
        # n continuazioni campionate: abbastanza token per arrivare a tre parole.
        enc = tok([prompt] * n, return_tensors="pt").to(DEVICE)
        uscita = m.generate(**enc, do_sample=True, temperature=temperatura, top_k=0, top_p=1.0,
                            max_new_tokens=10, pad_token_id=tok.pad_token_id)
        return tok.batch_decode(uscita[:, enc.input_ids.shape[1]:], skip_special_tokens=True)

    def il_modello_vota(m, prompt: str, n: int = 300, temperatura: float = 1.0) -> Counter:
        # Un voto = la prima parola di una continuazione campionata.
        return Counter(p for p in map(prima_parola, il_modello_continua(m, prompt, n, temperatura)) if p)

    return il_modello_continua, il_modello_vota


@app.cell
def _(mo):
    svela = mo.ui.run_button(label="🦜 Svela il modello", kind="success")
    svela
    return (svela,)


@app.cell
def _(
    Counter,
    IN_NOTEBOOK,
    PROMPT,
    accordo,
    confronta,
    dati_sala,
    distribuzione,
    il_modello_continua,
    leggi_risposte,
    leggi_voti,
    mo,
    model,
    percento,
    prima_parola,
    risposta_del_modello,
    svela,
):
    mo.stop(IN_NOTEBOOK and not svela.value,
            mo.md("*Chiudi la votazione, poi premi **Svela il modello**. Ogni clic è una nuova votazione del modello.*"))
    _voti = dati_sala()["voti"].get(PROMPT, [])
    _continuazioni = il_modello_continua(model, PROMPT)  # 300 voti del modello, usati due volte
    # 1) la prima parola: il confronto onesto, un token alla volta
    p_sala = distribuzione(leggi_voti(_voti))
    p_modello = distribuzione(Counter(p for p in map(prima_parola, _continuazioni) if p))
    # 2) le risposte intere: la sala fino a tre parole, il modello fino alla prima pausa (massimo tre)
    r_sala = distribuzione(leggi_risposte(_voti))
    r_modello = distribuzione(Counter(r for r in map(risposta_del_modello, _continuazioni) if r))

    _s, _m = list(r_sala.items())[:8], list(r_modello.items())[:8]
    _tabella = ["| | la sala | | il modello | |", "|---:|---|---:|---|---:|"]
    for _i in range(max(len(_s), len(_m))):
        _cella = []
        for _lista, _altra in ((_s, r_modello), (_m, r_sala)):
            _testo, _quota = _lista[_i] if _i < len(_lista) else ("", None)
            _cella += [f"**{_testo}**" if _testo in _altra else _testo, percento(_quota) if _quota else ""]
        _tabella.append(f"| {_i + 1} | " + " | ".join(_cella) + " |")
    mo.vstack([
        confronta({"Sala": p_sala, "Modello": p_modello}, f"La prima parola, sala contro modello: «{PROMPT}…»"),
        mo.md(f"## Accordo sala ↔ modello sulla prima parola: **{accordo(p_sala, p_modello):.0%}**"),
        mo.md("### Le risposte intere\n*In grassetto quelle che avete dato sia voi sia il modello.*\n\n"
              + "\n".join(_tabella)),
    ])
    return (r_sala,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Le vostre risposte, una per una

    Quanto avrebbe potuto scriverle il modello? Probabilità esatta, con la regola della catena: $P(\text{risposta}) = \prod_i P(\text{token}_i \mid \text{tutto ciò che viene prima})$,
    moltiplicata per la probabilità che l'ultima parola *finisca lì*, cioè che il token successivo cominci una parola nuova.
    Tre parole sono tanti token: ogni token in più moltiplica per un numero minore di 1.
    """)
    return


@app.cell
def _(DEVICE, math, model, tok, torch):
    # Quali token iniziano una parola nuova (spazio, a capo, punteggiatura)? Serve a sapere dove finisce una parola.
    # (Lo strato di uscita è un po' più grande del vocabolario: le righe in più non escono mai, restano False.)
    INIZIA_PAROLA = torch.zeros(model.get_output_embeddings().weight.shape[0], dtype=torch.bool)
    INIZIA_PAROLA[: len(tok)] = torch.tensor([not tok.decode([i])[:1].isalnum() for i in range(len(tok))])
    INIZIA_PAROLA = INIZIA_PAROLA.to(DEVICE)

    @torch.no_grad()
    def prob_parola(m, prompt: str, parola: str) -> tuple[float, list[str]]:
        ids = tok(prompt, return_tensors="pt").input_ids.to(DEVICE)
        pezzi = tok(" " + parola, add_special_tokens=False, return_tensors="pt").input_ids.to(DEVICE)
        logp = torch.log_softmax(m(torch.cat([ids, pezzi], dim=1)).logits[0], dim=-1)
        n = ids.shape[1]
        catena = sum(logp[n - 1 + j, t] for j, t in enumerate(pezzi[0]))  # regola della catena
        fine = torch.logsumexp(logp[-1][INIZIA_PAROLA], dim=0)  # ...e poi la parola finisce
        return math.exp((catena + fine).item()), [tok.decode([t]) for t in pezzi[0]]

    return (prob_parola,)


@app.cell
def _(PROMPT, mo, model, percento, prob_parola, r_sala, visibile):
    _righe = ["| risposta | sala | modello | token |", "|---|---:|---:|---|"]
    for _risposta, _quota in list(r_sala.items())[:12]:
        _p, _pezzi = prob_parola(model, PROMPT, _risposta)  # funziona anche con più parole
        _righe.append(f"| **{_risposta}** | {percento(_quota)} | {percento(_p)} | "
                      f"`{' + '.join(visibile(x) for x in _pezzi)}` |")
    mo.md("\n".join(_righe))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### La temperatura, ovvero quante birre ha bevuto il pappagallo

    Prima del softmax si dividono i logit per $T$. Con $T$ basso il pappagallo è sobrio e prevedibile; con $T$ alto diventa creativo, e poi delirante.
    La classifica dei token resta la stessa: cambia solo quanto è "piatta" la distribuzione.
    """)
    return


@app.cell
def _(mo):
    temperatura_ui = mo.ui.slider(0.1, 2.5, step=0.1, value=1.0, show_value=True, full_width=True,
                                  label="🌡️ temperatura")
    temperatura_ui
    return (temperatura_ui,)


@app.cell
def _(PROMPT, continua, grafico_token, mo, model, temperatura_ui, top_token):
    _T = temperatura_ui.value
    mo.vstack([
        grafico_token(top_token(model, PROMPT, k=10, temperatura=_T), f"T = {_T}: «{PROMPT}…»", xmax=1.0),
        mo.md(f"**Il pappagallo a T = {_T}:** {PROMPT} *{continua(model, PROMPT, temperatura=_T)}*"),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Atto 2: La catena di Markov umana

    - Sul telefono premete **✍️ Tocca a me**: vi viene assegnata una frase di cui vedete **solo l'ultima parola**, oppure le ultime due.
    - Scrivete la parola che viene dopo. Poi prendetene un'altra, da un'altra frase.
    - Ci sono tante frasi in parallelo, e tutte partono dalla stessa parola dell'Atto 1.

    Ognuno di voi sta calcolando $P(\text{parola} \mid \text{parola precedente})$. Nessuno conosce la frase intera.
    """)
    return


@app.cell
def _(mo):
    inizio_ui = mo.ui.text(value="traffico", label="Parola iniziale")
    n_catene_ui = mo.ui.slider(2, 20, value=8, show_value=True, label="Catene")
    lunghezza_ui = mo.ui.slider(6, 20, value=12, show_value=True, label="Parole per catena")
    mo.hstack([inizio_ui, n_catene_ui, lunghezza_ui], justify="start", gap=2)
    return inizio_ui, lunghezza_ui, n_catene_ui


@app.cell
def _(inizio_ui, lunghezza_ui, mo, n_catene_ui, sito):
    _avvia = mo.ui.button(label="▶️ Avvia le catene sui telefoni", kind="success",
                          on_click=lambda _: sito.avvia_catene(inizio_ui.value, n_catene_ui.value, lunghezza_ui.value))
    _chiudi = mo.ui.button(label="⏹ Chiudi le catene", on_click=lambda _: sito.fase("attesa"))
    mo.hstack([_avvia, _chiudi], justify="start")
    return


@app.cell
def _(aggiorna, dati_sala, mo):
    aggiorna
    _d = dati_sala()
    _righe = ["| | memoria | avanzamento | |", "|---|---|---|---:|"]
    for _i, _c in enumerate(_d["catene"]):
        _n, _l = len(_c["parole"]), _c["lunghezza"]
        _scrive = " ✍️" if _c.get("occupata") else ""
        _righe.append(f"| catena {_i + 1} | {_c['memoria']} | `{'▰' * _n}{'▱' * max(0, _l - _n)}`{_scrive} | {_n}/{_l} |")
    _fatte = sum(len(_c["parole"]) for _c in _d["catene"])
    _totale = sum(_c["lunghezza"] for _c in _d["catene"]) or 1
    mo.vstack([mo.md(f"**{_fatte}/{_totale} parole** ({_fatte / _totale:.0%}) · {_d['fonte']}"), mo.md("\n".join(_righe))])
    return


@app.cell
def _(mo):
    rivela = mo.ui.run_button(label="🎭 Rivela le frasi", kind="success")
    rivela
    return (rivela,)


@app.cell
def _(IN_NOTEBOOK, dati_sala, mo, rivela, unisci):
    mo.stop(IN_NOTEBOOK and not rivela.value, mo.md("*Quando le catene sono finite, chiudile e premi **Rivela le frasi**.*"))
    FRASI_CATENA = [(_c["memoria"], unisci(_c["parole"])) for _c in dati_sala()["catene"] if len(_c["parole"]) >= 4]
    mo.stop(not FRASI_CATENA, mo.callout(mo.md("Ancora nessuna catena con almeno 4 parole."), kind="warn"))
    mo.md("\n\n".join(f"### {_f}\n<small>memoria {_m}</small>" for _m, _f in FRASI_CATENA))
    return (FRASI_CATENA,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Le regole della sala

    Contiamo chi viene dopo chi. Questa tabella **è** il modello: un dizionario di contatori.
    """)
    return


@app.cell
def _(Counter, FRASI_CATENA, defaultdict, mo, parole):
    def regole_ngrammi(frasi: list[str], memoria: int) -> dict[tuple, Counter]:
        regole = defaultdict(Counter)
        for frase in frasi:
            p = parole(frase)
            for i in range(memoria, len(p)):
                regole[tuple(p[i - memoria:i])][p[i]] += 1
        return regole

    TUTTE = [_f for _, _f in FRASI_CATENA]
    REGOLE = {_m: regole_ngrammi(TUTTE, _m) for _m in (1, 2)}

    _bivi = sorted(REGOLE[1].items(), key=lambda kv: -sum(kv[1].values()))[:12]
    _righe = ["| dopo… | la sala ha scritto |", "|---|---|"]
    for (_prec,), _dopo in _bivi:
        _righe.append(f"| **{_prec}** | " + ", ".join(f"{w} ×{n}" for w, n in _dopo.most_common()) + " |")
    mo.md("\n".join(_righe))
    return REGOLE, TUTTE


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### La sala come generatore di testo

    Facciamo una passeggiata a caso nella tabella. Escono frasi che **nessuno di voi ha scritto** ✨
    """)
    return


@app.cell
def _(mo):
    rilancia_sala = mo.ui.button(label="🎲 Rilancia", value=0, on_click=lambda v: v + 1)
    rilancia_smemorato = mo.ui.button(label="🎲 Rilancia", value=0, on_click=lambda v: v + 1)
    rilancia_lambda = mo.ui.button(label="🎲 Rilancia", value=0, on_click=lambda v: v + 1)
    return rilancia_lambda, rilancia_sala, rilancia_smemorato


@app.cell
def _(REGOLE, TUTTE, inizio_ui, mo, parole, random, rilancia_sala, unisci):
    def la_sala_genera(regole, memoria: int, inizio: str, n_parole: int = 18) -> str:
        p = parole(inizio)
        for _ in range(n_parole):
            scelte = regole.get(tuple(p[-memoria:]))
            if not scelte:
                break
            p.append(random.choices(list(scelte), weights=list(scelte.values()))[0])
        return unisci(p)

    _ = rilancia_sala.value
    _originali = [unisci(parole(_f)) for _f in TUTTE]
    _righe = []
    for _ in range(6):
        _frase = la_sala_genera(REGOLE[1], 1, inizio_ui.value)
        _nuova = not any(_o.startswith(_frase) for _o in _originali)
        _righe.append(("✨ " if _nuova else "&emsp; ") + _frase)
    mo.vstack([mo.md("\n\n".join(_righe)), rilancia_sala])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 🏆 Premio Perplessità

    La **perplessità** misura quanto una frase sorprende il modello: $e^{\text{loss media per token}}$.
    La frase più assurda vince una birra. Il 🦜 Pappagallo d'oro va alla più prevedibile.
    """)
    return


@app.cell
def _(
    DEVICE,
    FRASI_CATENA,
    FRASI_NORMALI,
    grafico_perplessita,
    math,
    mo,
    model,
    numero,
    tok,
    torch,
):
    @torch.no_grad()
    def perplessita(m, frase: str) -> float:
        ids = tok(frase, return_tensors="pt").input_ids.to(DEVICE)
        return math.exp(m(ids, labels=ids).loss.item())  # loss = media di −log P(token | tutti i precedenti)

    _gruppo = {1: "memoria 1 parola", 2: "memoria 2 parole"}
    _righe = [(_f, _gruppo[_m], perplessita(model, _f)) for _m, _f in FRASI_CATENA]
    _righe += [(_f, "frase normale", perplessita(model, _f)) for _f in FRASI_NORMALI]

    _classifica = sorted((r for r in _righe if r[1] != "frase normale"), key=lambda r: -r[2])
    _tabella = ["| | frase | memoria | perplessità |", "|---|---|---|---:|"]
    for _i, (_f, _g, _ppl) in enumerate(_classifica):
        _premio = "🏆" if _i == 0 else "🦜" if _i == len(_classifica) - 1 else f"{_i + 1}."
        _tabella.append(f"| {_premio} | {_f} | {_g} | {numero(_ppl)} |")
    mo.vstack([mo.md("\n".join(_tabella)), grafico_perplessita(_righe, "Più contesto, meno sorpresa")])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Il pappagallo smemorato

    E se togliessimo la memoria al modello? È la stessa rete, ma a ogni passo vede solo le ultime 1 o 2 parole.

    Diventa… voi.
    """)
    return


@app.cell
def _(DEVICE, parole, prima_parola, tok, torch, unisci):
    @torch.no_grad()
    def campiona_parola(m, contesto: str, temperatura: float = 1.0) -> str | None:
        # Il modello estrae token finché non finisce una parola: ecco una parola "scritta" dal modello.
        enc = tok(contesto, return_tensors="pt").to(DEVICE)
        uscita = m.generate(**enc, do_sample=True, temperature=temperatura, top_k=0, top_p=1.0,
                            max_new_tokens=8, pad_token_id=tok.pad_token_id)
        nuovo = tok.decode(uscita[0, enc.input_ids.shape[1]:], skip_special_tokens=True)
        return prima_parola(nuovo, minuscole=False)

    def pappagallo_smemorato(m, inizio: str, memoria: int | None, n_parole: int = 16) -> str:
        p = parole(inizio, minuscole=False)
        for _ in range(n_parole):
            contesto = unisci(p[-memoria:] if memoria else p)  # ← qui tagliamo la memoria
            if (w := campiona_parola(m, contesto)) is None:
                break
            p.append(w)
        return unisci(p)

    @torch.no_grad()
    def continua(m, prompt: str, temperatura: float = 1.0, n_token: int = 24) -> str:
        enc = tok(prompt, return_tensors="pt").to(DEVICE)
        uscita = m.generate(**enc, do_sample=True, temperature=temperatura, top_k=0, top_p=1.0,
                            max_new_tokens=n_token, pad_token_id=tok.pad_token_id)
        return tok.decode(uscita[0, enc.input_ids.shape[1]:], skip_special_tokens=True).split("\n")[0].strip()

    return campiona_parola, continua, pappagallo_smemorato


@app.cell
def _(PROMPT, mo, model, pappagallo_smemorato, rilancia_smemorato):
    _ = rilancia_smemorato.value
    _righe = []
    for _memoria in (1, 2, None):
        _nome = f"memoria {_memoria}" if _memoria else "memoria piena"
        _righe.append(f"**{_nome}:** {pappagallo_smemorato(model, PROMPT, _memoria)}")
    mo.vstack([mo.md("\n\n".join(_righe)), rilancia_smemorato])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Atto 3: La sala addestra il modello

    Adesso usiamo le vostre regole per cambiare il comportamento del modello. Ci sono due modi:

    1. **Il trucco, senza gradienti.** A ogni parola, con probabilità $\lambda$ decide la sala (la vostra tabella), altrimenti decide il modello.
       È un modello interpolato, $P = \lambda \, P_\text{sala} + (1-\lambda) \, P_\text{modello}$, lo stesso trucco con cui si "lisciavano" gli n-grammi già negli anni '80.
    2. **La backpropagation.** Facciamo qualche passo di discesa del gradiente su un mini-batch fatto delle vostre frasi e dei vostri voti. Questa volta i pesi cambiano davvero.
    """)
    return


@app.cell
def _(mo):
    lam_ui = mo.ui.slider(0.0, 1.0, step=0.1, value=0.5, show_value=True, full_width=True,
                          label="λ: quanto ascolta la sala")
    lam_ui
    return (lam_ui,)


@app.cell
def _(
    PROMPT,
    REGOLE,
    campiona_parola,
    frase_evidenziata,
    lam_ui,
    mo,
    model,
    parole,
    random,
    rilancia_lambda,
    unisci,
):
    def pappagallo_ascolta_la_sala(m, inizio: str, lam: float, memoria: int = 1, n_parole: int = 20) -> str:
        p = parole(inizio, minuscole=False)
        n_inizio, fonti = len(p), []
        for _ in range(n_parole):
            scelte = REGOLE[memoria].get(tuple(w.lower() for w in p[-memoria:]))
            if scelte and random.random() < lam:  # con probabilità λ decide la sala...
                w, fonte = random.choices(list(scelte), weights=list(scelte.values()))[0], "sala"
            else:                                 # ...altrimenti il modello, con tutto il contesto
                w, fonte = campiona_parola(m, unisci(p)), "modello"
            if w is None:
                break
            p.append(w)
            fonti.append(fonte)
        return frase_evidenziata(p, fonti, n_inizio)

    _ = rilancia_lambda.value
    mo.vstack([
        mo.md("\n\n".join(f"→ {pappagallo_ascolta_la_sala(model, PROMPT, lam_ui.value)}" for _ in range(2))),
        mo.md("<small>Su sfondo blu le parole scelte dalla sala.</small>"),
        rilancia_lambda,
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Un mini-batch di backpropagation

    I dati di addestramento siete voi: le frasi delle catene, più ogni voto dell'Atto 1 come esempio a sé
    («A Roma, quando piove, il traffico impazzisce»). Il modello originale non lo tocchiamo: addestriamo una **copia**.
    """)
    return


@app.cell
def _(FRASI_CATENA, dati_sala, elenca_voti, mo, random):
    esempi = [_f for _, _f in FRASI_CATENA]
    VOTI_SALA = {_p: _v for _p, _v in dati_sala()["voti"].items() if _v}
    for _prompt, _voti in VOTI_SALA.items():  # ogni voto diventa un esempio
        esempi += [f"{_prompt} {_voce}" for _voce in elenca_voti(_voti)]
    random.shuffle(esempi)
    mo.md(f"**{len(esempi)} esempi.** Qualcuno:\n\n" + "\n".join(f"- {_e}" for _e in esempi[:5]))
    return VOTI_SALA, esempi


@app.cell
def _(DEVICE, mo, random, tok, torch):
    def addestra(m, esempi: list[str], passi: int = 20, lr: float = 5e-5, batch: int = 16) -> list[float]:
        m.train()
        m.get_input_embeddings().weight.requires_grad_(False)  # il vocabolario resta com'è
        ottimizzatore = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=lr)
        perdite = []
        with mo.status.progress_bar(total=passi, title="Backpropagation", subtitle="…") as barra:
            for _passo in range(passi):
                lotto = random.sample(esempi, min(batch, len(esempi)))  # il mini-batch
                enc = tok(lotto, return_tensors="pt", padding=True).to(DEVICE)
                etichette = enc.input_ids.masked_fill(enc.attention_mask == 0, -100)  # niente loss sul padding
                loss = m(**enc, labels=etichette).loss  # media di −log P(token giusto)
                loss.backward()        # i gradienti
                ottimizzatore.step()   # un passo in discesa
                ottimizzatore.zero_grad()
                perdite.append(loss.item())
                barra.update(subtitle=f"loss {loss.item():.3f}")
        m.eval()
        return perdite

    return (addestra,)


@app.cell
def _(mo):
    passi_ui = mo.ui.slider(5, 60, value=20, show_value=True, label="passi")
    lr_ui = mo.ui.dropdown({"1e-5": 1e-5, "3e-5": 3e-5, "5e-5": 5e-5, "1e-4": 1e-4, "3e-4": 3e-4},
                           value="5e-5", label="learning rate")
    addestra_btn = mo.ui.run_button(label="🧠 Addestra con la sala", kind="success")
    mo.hstack([passi_ui, lr_ui, addestra_btn], justify="start", align="center", gap=2)
    return addestra_btn, lr_ui, passi_ui


@app.cell
def _(
    DEVICE,
    IN_NOTEBOOK,
    addestra,
    addestra_btn,
    copy,
    esempi,
    gc,
    grafico_loss,
    lr_ui,
    mo,
    model,
    passi_ui,
    torch,
):
    mo.stop(IN_NOTEBOOK and not addestra_btn.value, mo.md("*Premi **Addestra con la sala** quando sei pronto.*"))
    gc.collect()
    if DEVICE == "mps":
        torch.mps.empty_cache()
    model_sala = copy.deepcopy(model)  # il modello originale resta intatto
    perdite = addestra(model_sala, esempi, passi=passi_ui.value, lr=lr_ui.value)
    grafico_loss(perdite)
    return model_sala, perdite


@app.cell
def _(
    PROMPT,
    VOTI_SALA,
    accordo,
    confronta,
    distribuzione,
    il_modello_vota,
    leggi_voti,
    mo,
    model,
    model_sala,
    perdite,
):
    mo.stop(not VOTI_SALA, mo.md("*Nessun voto dall'Atto 1 da confrontare.*"))
    PROMPT_TEST = PROMPT if PROMPT in VOTI_SALA else next(iter(VOTI_SALA))
    _sala = distribuzione(leggi_voti(VOTI_SALA[PROMPT_TEST]))
    _prima = distribuzione(il_modello_vota(model, PROMPT_TEST))
    _dopo = distribuzione(il_modello_vota(model_sala, PROMPT_TEST))
    mo.vstack([
        confronta({"Sala": _sala, "Modello prima": _prima, "Modello dopo": _dopo},
                  f"Dopo {len(perdite)} passi: «{PROMPT_TEST}…»", top=8),
        mo.md(f"## Accordo con la sala: {accordo(_sala, _prima):.0%} → **{accordo(_sala, _dopo):.0%}**"),
    ])
    return (PROMPT_TEST,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Come scrive adesso?

    Proviamo un prompt che conosce e uno che non ha mai visto.
    """)
    return


@app.cell
def _(PROMPT_TEST, mo, model_sala, pappagallo_smemorato):
    _righe = []
    for _inizio in (PROMPT_TEST, "Ieri sera al pub, il mio capo"):
        for _ in range(2):
            _righe.append(f"→ {pappagallo_smemorato(model_sala, _inizio, memoria=None, n_parole=18)}")
    mo.md("\n\n".join(_righe))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Epilogo

    - Il modello sceglie la prossima parola **da una distribuzione di probabilità**, come avete fatto voi. Nel singolo passo non c'è nessuna magia.
    - La differenza fra voi-a-n-grammi e il transformer sta soprattutto nel **contesto**: con memoria 1 il modello è un pappagallo smemorato quanto voi.
    - Cambiare il comportamento costa poco: una miscela di distribuzioni ($\lambda$) oppure 20 passi di gradiente. È per questo che i dati contano più di tutto il resto.

    🍺 Grazie!
    """)
    return


@app.cell
def _():
    # 📦 Dati di esempio: li usa il notebook quando il sito è spento (prova generale senza telefoni).
    DEMO_VOTI = {
        "A Roma, quando piove, il traffico": {
            "impazzisce": 12, "si blocca": 8, "aumenta": 7, "va in tilt": 5, "è un incubo": 4,
            "peggiora": 3, "si ferma": 2,
        },
        "Il codice funzionava ieri sera, ma stamattina": {
            "non funziona più": 11, "non parte": 8, "è esploso": 5, "dà errore": 4, "pandas è cambiato": 3,
        },
        "La cosa più bella di Python è": {
            "la sintassi": 9, "la community": 7, "la semplicità": 6, "l'indentazione": 4, "pandas": 3,
            "che è gratis": 3, "il pip install": 2,
        },
    }
    _catene = [
        (1, "traffico impazzisce la mamma di Guido mangia sempre il gelato al pistacchio di Bronte"),
        (2, "traffico impazzisce sempre quando piove a dirotto e io resto a casa con il gatto"),
        (1, "traffico intenso come il caffè della macchinetta rotta da tre anni luce spenta"),
        (2, "traffico di Roma è una cosa seria ma non troppo per un lunedì mattina"),
        (1, "traffico romano antico come il Colosseo è pieno di turisti tedeschi che bevono birra"),
        (2, "traffico sul raccordo anulare non finisce mai di stupirmi quando guido la Panda di mia zia"),
        (1, "traffico telefonico dei dati personali non si toccano mai le mani in pasta fresca"),
        (2, "traffico aumenta perché tutti escono di casa alle otto per andare in ufficio"),
    ]
    DEMO_CATENE = [{"id": _i, "memoria": _m, "lunghezza": len(_f.split()), "parole": _f.split()}
                   for _i, (_m, _f) in enumerate(_catene)]
    # Termine di paragone per la perplessità: frasi scritte da qualcuno che vedeva tutta la frase.
    FRASI_NORMALI = [
        "A Roma, quando piove, il traffico diventa un incubo e tutti arrivano tardi al lavoro.",
        "Il codice funzionava ieri sera, ma stamattina i test non passano più.",
        "Dopo la terza birra, ogni data scientist giura che il suo modello non è in overfitting.",
    ]
    return DEMO_CATENE, DEMO_VOTI, FRASI_NORMALI


if __name__ == "__main__":
    app.run()
