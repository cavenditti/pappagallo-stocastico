# 🦜 Il pappagallo stoca**ico

La sala contro il modello: un gioco in tre atti per un meetup di PyData Roma Capitale.

1. **Indovina il prossimo token.** La sala vota la parola successiva dal telefono, poi un piccolo LLM aperto "vota" 300 volte campionando dalla sua distribuzione.
2. **Catena di Markov umana.** Ognuno vede solo l'ultima parola (o le ultime due) e aggiunge la successiva: un modello a n-grammi fatto di persone.
3. **La sala addestra il modello.** Le regole e le frasi della sala cambiano il modello, prima per interpolazione (λ) e poi con un mini-batch di backpropagation.

Tutto gira offline su un portatile: un notebook [marimo](https://marimo.io) da proiettare, un piccolo sito FastAPI per i telefoni e [Qwen3-0.6B-Base](https://huggingface.co/Qwen/Qwen3-0.6B-Base) come modello.

## Avvio rapido

```bash
uv sync
uv run hf download Qwen/Qwen3-0.6B-Base
uv run python server.py                            # il sito per i telefoni
HF_HUB_OFFLINE=1 uv run marimo edit pappagallo.py  # il notebook da proiettare
uv run python simula_sala.py                       # (prova) 30 telefoni finti
```

La guida completa per chi conduce, con la rete, la scaletta e cosa fare se qualcosa va storto, è in [GUIDA.md](GUIDA.md).

## File

| File | |
|---|---|
| `pappagallo.py` | il notebook marimo: palco e pannello di controllo |
| `server.py`, `sito/index.html` | il sito per i telefoni (voti e catene) |
| `sala.py` | il collegamento fra notebook e sito, i QR (Wi-Fi e gioco) e il controllo dell’indirizzo |
| `qr/` | i QR delle slide; si rigenerano con `uv run python sala.py` |
| `aiuti.py` | grafici e utilità di testo |
| `simula_sala.py` | una sala finta per le prove |
