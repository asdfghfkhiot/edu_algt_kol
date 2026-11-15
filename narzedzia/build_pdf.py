#!/usr/bin/env python3
"""
Buduje PDF z szablonu: src/rozwiazania.template.html -> rozwiazania.pdf

Potok:
  1. drzewo HTML z szablonu,
  2. wszystkie wzory TeX -> SVG (MathJax w Node), wzory w linii dodatkowo -> PNG (resvg),
  3. konwersja na flowables ReportLaba (narzedzia/pdf/convert.py),
  4. dwukrotne złożenie dokumentu (drugie przejście wypełnia numery stron w spisie treści).

Uruchomienie:
    python3 narzedzia/build_pdf.py [--podglad 3,4,5] [--dpi 110]

Wymaga: reportlab, pillow, resvg-py, svglib, pymupdf (podgląd), node + mathjax-full.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reportlab.platypus import PageBreak, Spacer  # noqa: E402

from narzedzia.pdf.convert import Converter, Dokument, Tree, spis_tresci  # noqa: E402
from narzedzia.pdf.mathrender import MathRenderer  # noqa: E402
from narzedzia.pdf.style import BODY_SIZE, SERIF_EX_RATIO, TEXT_WIDTH, style, zarejestruj_czcionki  # noqa: E402

TEMPLATE = ROOT / "src" / "rozwiazania.template.html"
WYJSCIE = ROOT / "rozwiazania.pdf"


def zbierz_wzory(tekst):
    """Wszystkie wzory w kolejności: najpierw blokowe, potem w linii."""
    wzory = []
    bez_blokowych = re.sub(r"\$\$(.+?)\$\$", lambda m: " " * len(m.group(0)), tekst, flags=re.S)
    for m in re.finditer(r"\$\$(.+?)\$\$", tekst, re.S):
        wzory.append((re.sub(r"\s+", " ", m.group(1)).strip(), True))
    for m in re.finditer(r"\$([^$\n]+?)\$", bez_blokowych):
        wzory.append((re.sub(r"\s+", " ", m.group(1)).strip(), False))
    return wzory


class Zbieracz:
    """Atrapa renderera: pierwsze przejście zbiera dokładnie te wzory, których chce konwerter."""

    def __init__(self):
        self.zebrane = []
        self.ex_pt = 6.0

    def img_tag(self, tex, scale=1.0):
        self.zebrane.append((tex, False))
        return ""

    def meta(self, tex, display=False):
        self.zebrane.append((tex, bool(display)))
        return {"tex": tex, "display": bool(display), "w_ex": 1, "h_ex": 1, "d_ex": 0,
                "w_pt": 8.0, "h_pt": 4.0, "d_pt": 0.0, "png": "", "svg": ""}

    def drawing(self, tex, display=True):
        return None

    def png(self, tex, display=False):
        return ""


def zbuduj(podglad=None, dpi=110):
    zarejestruj_czcionki()
    S = style()

    html = TEMPLATE.read_text(encoding="utf-8")
    drzewo = Tree.parsuj(html)
    body = drzewo.root.find_all("body")
    body = body[0] if body else drzewo.root

    # 1. przejście: zbieramy dokładnie te wzory, o które poprosi konwerter
    zbieracz = Zbieracz()
    _zbuduj_story(Converter(zbieracz), body, S)
    wzory = list(dict.fromkeys(zbieracz.zebrane))

    r = MathRenderer(font_size_pt=BODY_SIZE, ex_ratio=SERIF_EX_RATIO)
    print(f"wzory: {len(wzory)} unikalnych — renderuję ...")
    r.prepare(wzory)

    # 2. przejście: prawdziwy dokument
    story = _zbuduj_story(Converter(r), body, S)

    doc = Dokument(str(WYJSCIE))
    doc.multiBuild(story)
    print(f"gotowe: {WYJSCIE} ({WYJSCIE.stat().st_size / 1e6:.2f} MB)")

    kontrola_tekstu(WYJSCIE)

    if podglad:
        podglad_stron(WYJSCIE, podglad, dpi)
    return WYJSCIE


def kontrola_tekstu(pdf):
    """Szybka kontrola: w warstwie tekstowej nie powinno być resztek TeX-a ani encji HTML."""
    import pymupdf

    wzorce = (r"\\[A-Za-z]+", r"\$", r"&[a-z]+;", r"&lt;|&gt;")
    problemy = []
    doc = pymupdf.open(str(pdf))
    for i, strona in enumerate(doc, 1):
        tekst = strona.get_text()
        for w in wzorce:
            for m in re.finditer(w, tekst):
                problemy.append((i, tekst[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")))
    if problemy:
        print(f"UWAGA: {len(problemy)} resztek w warstwie tekstowej, np.:")
        for strona, fragment in problemy[:6]:
            print(f"  s. {strona}: …{fragment}…")
    else:
        print("kontrola tekstu: OK (brak resztek TeX-a i encji)")
    return problemy


def _zbuduj_story(conv, body, S):
    story = []
    for dziecko in body.children:
        if hasattr(dziecko, "tag") and dziecko.tag == "nav":
            continue
        story.extend(conv.blocks(_opakuj(dziecko)))
    # spis treści wstawiamy po wstępie (za pierwszą ramką „Konwencje i oznaczenia”)
    idx = next((i + 1 for i, f in enumerate(story) if type(f).__name__ == "Ramka"), 5)
    # strona tytułowa (hero + wstęp + konwencje) | strona ze spisem treści | Część I
    story.insert(idx, PageBreak())
    story.insert(idx + 1, _tytul_spisu(S))
    story.insert(idx + 2, spis_tresci(S))
    story.insert(idx + 3, Spacer(1, 6))
    story[idx + 4:idx + 4] = _przypis_spisu(S)
    return sklej_wzory(story)


def sklej_wzory(story):
    """Akapit wprowadzający + wzór blokowy trzymamy razem (unikamy osieroconego wzoru)."""
    from reportlab.platypus import KeepTogether, Paragraph

    z, i = [], 0
    while i < len(story):
        f = story[i]
        if (i + 1 < len(story) and isinstance(f, Paragraph)
                and type(story[i + 1]).__name__ == "MathBlock"
                and len(getattr(f, "text", "") or "") < 300):
            z.append(KeepTogether([f, story[i + 1]]))
            i += 2
            continue
        z.append(f)
        i += 1
    return z


def _opakuj(dziecko):
    from narzedzia.pdf.convert import Node
    if isinstance(dziecko, str):
        n = Node("div")
        n.children.append(dziecko)
        return n
    return dziecko


def _indeks_spisu(story):
    """Wstawiamy spis treści po: hero (4 elementy), lead, ramce konwencji."""
    return min(6, len(story))


def _przypis_spisu(S):
    from reportlab.lib import colors
    from reportlab.platypus import HRFlowable, Paragraph

    return [
        Spacer(1, 16),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#ddd8cd"),
                   spaceBefore=2, spaceAfter=8),
        Paragraph("Numery po prawej stronie to strony tego pliku PDF. Każda część zaczyna się "
                  "na nowej stronie, a zadania 3, 4 i 5 mają osobne nagłówki — można drukować "
                  "pojedyncze strony albo cały dokument dwustronnie.",
                  S["note"]),
    ]


def _tytul_spisu(S):
    from reportlab.platypus import HRFlowable, Paragraph, Spacer
    return Paragraph("SPIS TREŚCI", S["toc_title"])


def podglad_stron(pdf, strony, dpi):
    import pymupdf

    doc = pymupdf.open(str(pdf))
    katalog = Path("/tmp/edu_algt_pdf/podglad")
    katalog.mkdir(parents=True, exist_ok=True)
    for s in strony:
        if s < 1 or s > doc.page_count:
            continue
        pix = doc[s - 1].get_pixmap(dpi=dpi)
        plik = katalog / f"strona-{s:02d}.png"
        pix.save(str(plik))
        print("podgląd:", plik)
    print("stron w PDF:", doc.page_count)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--podglad", default="", help="numery stron do wyrenderowania, np. 1,2,5")
    ap.add_argument("--dpi", type=int, default=110)
    args = ap.parse_args()
    strony = [int(x) for x in args.podglad.split(",") if x.strip()] if args.podglad else []
    zbuduj(strony, args.dpi)
