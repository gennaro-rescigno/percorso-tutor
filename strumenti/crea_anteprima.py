"""
crea_anteprima.py — mette invito, stile e codice dentro un unico file HTML.

Serve per due cose:
  1. avere un'anteprima che si apre con un doppio clic, senza server;
  2. poter mandare l'invito come singolo file a chi te lo chiede.

Uso, da dentro la cartella del progetto:
    python3 strumenti/crea_anteprima.py
"""

from pathlib import Path
import re

# La cartella del progetto: due livelli sopra questo file
BASE = Path(__file__).resolve().parent.parent
SITO = BASE / "invito-digitale"


def leggi(percorso_relativo):
    """Legge un file del sito e restituisce il suo contenuto come testo."""
    return (SITO / percorso_relativo).read_text(encoding="utf-8")


def incorpora(html):
    """Sostituisce i collegamenti a CSS e JS con il codice vero e proprio."""

    def sostituisci_css(trovato):
        file_css = trovato.group(1)
        return "<style>\n" + leggi(file_css) + "\n</style>"

    def sostituisci_js(trovato):
        file_js = trovato.group(1)
        return "<script>\n" + leggi(file_js) + "\n</script>"

    # I fogli di stile locali (quelli di Google Fonts restano collegati)
    html = re.sub(r'<link rel="stylesheet" href="((?!http)[^"]+)">', sostituisci_css, html)

    # Gli script locali
    html = re.sub(r'<script src="((?!http)[^"]+)"></script>', sostituisci_js, html)

    return html


def main():
    for pagina, destinazione in [("index.html", "anteprima.html"),
                                 ("messaggi.html", "anteprima-messaggi.html")]:
        completo = incorpora(leggi(pagina))
        uscita = BASE / destinazione
        uscita.write_text(completo, encoding="utf-8")
        peso = len(completo.encode("utf-8")) / 1024
        print(f"{destinazione} creato — {peso:.0f} KB")


if __name__ == "__main__":
    main()
