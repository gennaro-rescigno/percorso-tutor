"""
nuovo_invito.py — crea un invito nuovo in un comando.

Fa tre cose:
  1. genera due indirizzi impossibili da indovinare (uno per gli ospiti,
     uno per la festeggiata) che non si assomigliano fra loro;
  2. costruisce le due pagine e il config di questa festa;
  3. scrive tutto nel registro privato e ti stampa la riga da incollare
     nel foglio Google.

Uso:
    python3 strumenti/nuovo_invito.py
e rispondi alle domande. Oppure tutto in una riga:
    python3 strumenti/nuovo_invito.py --nome Marta --eta 18 \
        --quando 2027-08-04T20:00 --luogo "Villa dei Fiori" --tema cipria
"""

import argparse
import json
import re
import secrets
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MODELLI = BASE / "modelli"
PUBBLICO = BASE / "pubblico"
REGISTRO = BASE / "registro.md"
IMPOSTAZIONI = BASE / "impostazioni.json"

TEMI = ["cipria", "discoteca", "neve", "spazio", "casino", "calcio"]

# niente lettere che si confondono: via O/0, I/l/1
ALFABETO = "abcdefghjkmnpqrstuvwxyz23456789"
ALFABETO_CODICE = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def pezzo_a_caso(quanti=12):
    """La parte impossibile da indovinare dell'indirizzo."""
    return "".join(secrets.choice(ALFABETO) for _ in range(quanti))


def codice_a_caso(quanti=6):
    """Il codice che la festeggiata digita per vedere i suoi messaggi."""
    return "".join(secrets.choice(ALFABETO_CODICE) for _ in range(quanti))


def semplifica(testo):
    """Marta D'Angiò -> marta-dangio"""
    t = unicodedata.normalize("NFD", str(testo))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t or "invito"


def chiedi(domanda, predefinito=""):
    suffisso = f" [{predefinito}]" if predefinito else ""
    risposta = input(f"{domanda}{suffisso}: ").strip()
    return risposta or predefinito


def data_in_italiano(quando):
    d = datetime.fromisoformat(quando)
    return f"{d.day} {MESI[d.month - 1].capitalize()} {d.year}", d.strftime("%H:%M"), d


def riempi(modello, valori):
    testo = modello
    for chiave, valore in valori.items():
        testo = testo.replace("{{" + chiave + "}}", str(valore))
        # ora dell'evento e ora nel programma sono la stessa cosa
    return testo


def main():
    p = argparse.ArgumentParser(description="Crea un invito nuovo")
    p.add_argument("--nome")
    p.add_argument("--eta", type=int)
    p.add_argument("--quando", help="2027-08-04T20:00")
    p.add_argument("--luogo")
    p.add_argument("--indirizzo", default="")
    p.add_argument("--mappa", default="")
    p.add_argument("--tema", choices=TEMI)
    p.add_argument("--whatsapp", default="")
    p.add_argument("--dresscode", default="Elegante")
    p.add_argument("--scadenza", default="")
    a = p.parse_args()

    # Se hai passato --nome vuol dire che sai già tutto: niente domande,
    # i campi che non hai messo restano vuoti e li riempi dopo a mano.
    interattivo = a.nome is None

    def campo(valore, domanda, predefinito=""):
        if valore:
            return valore
        return chiedi(domanda, predefinito) if interattivo else predefinito

    print("\n=== INVITO NUOVO ===\n")
    nome = campo(a.nome, "Nome della festeggiata")
    eta = a.eta or (int(chiedi("Quanti anni compie", "18")) if interattivo else 18)
    quando = campo(a.quando, "Quando (anno-mese-giornoTora:minuti)", "2027-08-04T20:00")
    luogo = campo(a.luogo, "Dove si fa")
    indirizzo = campo(a.indirizzo, "Indirizzo del posto")
    mappa = campo(a.mappa, "Link di Google Maps")
    tema = campo(a.tema, f"Tema ({', '.join(TEMI)})", "cipria")
    whatsapp = campo(a.whatsapp, "Link del gruppo WhatsApp (puoi metterlo dopo)")

    if not nome:
        raise SystemExit("\nServe almeno il nome della festeggiata.")

    if tema not in TEMI:
        raise SystemExit(f"\nTema sconosciuto: {tema}. Scegli fra: {', '.join(TEMI)}")

    data_testo, ora_testo, quando_data = data_in_italiano(quando)
    # la scadenza si può scrivere sia "1 agosto" sia 2027-08-01: nel secondo
    # caso la traduco, perché sull'invito deve leggersi come una data vera
    scadenza = a.scadenza.strip()
    iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", scadenza)
    if iso:
        scadenza = f"{int(iso.group(3))} {MESI[int(iso.group(2)) - 1]}"
    elif not scadenza:
        scadenza = f"{max(1, quando_data.day - 15)} {MESI[quando_data.month - 1]}"

    impostazioni = json.loads(IMPOSTAZIONI.read_text(encoding="utf-8")) if IMPOSTAZIONI.exists() else {}
    backend = impostazioni.get("backend", "")
    sito = impostazioni.get("sito", "").rstrip("/")

    # --- i due indirizzi, indipendenti l'uno dall'altro ----------------
    base = semplifica(nome)
    id_invito = f"{base}-{eta}-{pezzo_a_caso(6)}"
    via_ospiti = f"{base}-{eta}-{pezzo_a_caso(12)}"
    via_festeggiata = f"{base}-{pezzo_a_caso(12)}"
    codice = codice_a_caso()

    valori = {
        "ID": id_invito, "TEMA": tema, "NOME": nome, "ETA": eta,
        "INIZIALI": "".join(w[0] for w in nome.split()[:2]).upper() or nome[:2].upper(),
        "QUANDO": quando + ":00" if len(quando) == 16 else quando,
        "DATA": data_testo, "ORA": ora_testo, "LUOGO": luogo,
        "INDIRIZZO": indirizzo, "MAPPA": mappa, "DRESSCODE": a.dresscode,
        "SCADENZA": scadenza, "WHATSAPP": whatsapp, "BACKEND": backend,
    }

    cartella_ospiti = PUBBLICO / "i" / via_ospiti
    cartella_festa = PUBBLICO / "c" / via_festeggiata
    for c in (cartella_ospiti, cartella_festa):
        if c.exists():
            raise SystemExit(f"\nEsiste già {c}. Rilancia: gli indirizzi si tirano a sorte.")
        c.mkdir(parents=True)

    config = riempi((MODELLI / "config.js").read_text(encoding="utf-8"), valori)
    (cartella_ospiti / "config.js").write_text(config, encoding="utf-8")
    (cartella_festa / "config.js").write_text(config, encoding="utf-8")

    (cartella_ospiti / "index.html").write_text(
        riempi((MODELLI / "invito.html").read_text(encoding="utf-8"), valori), encoding="utf-8")
    (cartella_festa / "index.html").write_text(
        riempi((MODELLI / "conferme.html").read_text(encoding="utf-8"), valori), encoding="utf-8")

    link_ospiti = f"{sito}/i/{via_ospiti}/" if sito else f"/i/{via_ospiti}/"
    link_festa = f"{sito}/c/{via_festeggiata}/" if sito else f"/c/{via_festeggiata}/"

    # --- il registro privato: NON finisce online ------------------------
    if not REGISTRO.exists():
        REGISTRO.write_text(
            "# Registro degli inviti\n\n"
            "**Questo file non va mai online.** Resta solo nel repo privato.\n\n",
            encoding="utf-8")
    with REGISTRO.open("a", encoding="utf-8") as f:
        f.write(f"\n## {nome} — {eta} anni — {data_testo}\n\n"
                f"- Tema: `{tema}`\n"
                f"- Identificativo: `{id_invito}`\n"
                f"- Codice della festeggiata: **{codice}**\n"
                f"- Link per gli invitati: {link_ospiti}\n"
                f"- Link per la festeggiata: {link_festa}\n"
                f"- Creato il: {datetime.now().strftime('%d/%m/%Y')}\n")

    print("\n" + "=" * 62)
    print(f"  FATTO — {nome}, {eta} anni, {data_testo}")
    print("=" * 62)
    print("\n1) INCOLLA QUESTA RIGA nella scheda 'Registro' del foglio Google:\n")
    print(f"   {id_invito}\t{nome}\t{codice}\t\t{datetime.now().strftime('%d/%m/%Y')}")
    print("\n   (le colonne sono: invito | festeggiata | codice | apertura | creato)")
    print("   La colonna 'apertura' lasciala vuota, oppure metti una data tipo")
    print("   2027-08-04T20:00 se vuoi che i messaggi restino chiusi fino alla festa.\n")
    print("2) MANDA AGLI INVITATI:")
    print(f"   {link_ospiti}\n")
    print("3) MANDA SOLO ALLA FESTEGGIATA:")
    print(f"   {link_festa}")
    print(f"   con il suo codice: {codice}\n")
    if not backend:
        print("   ATTENZIONE: in impostazioni.json manca l'indirizzo del foglio Google,")
        print("   quindi per ora questo invito gira in modo prova.\n")
    if not sito:
        print("   ATTENZIONE: in impostazioni.json manca l'indirizzo del sito,")
        print("   quindi i link qui sopra sono senza la parte iniziale.\n")
    print("Tutto è finito anche in registro.md (che non va mai online).\n")


if __name__ == "__main__":
    main()
