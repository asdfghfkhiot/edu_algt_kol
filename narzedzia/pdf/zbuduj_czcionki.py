#!/usr/bin/env python3
"""
Buduje pełne pliki TTF (Source Serif 4 / Source Sans 3) z subsetów @fontsource.

Fontsource dzieli fonty na subset "latin" (ASCII) i "latin-ext" (m.in. polskie znaki),
a ReportLab potrzebuje jednego pliku z pełnym zestawem znaków. Skrypt pobiera paczki
z npm (albo korzysta z rozpakowanych katalogów), scala subsetty i zapisuje TTF-y
do src/fonty/.

Uruchamiany rzadko (raz, przy zmianie fontów); wynik jest commitowany, więc
zwykłe budowanie PDF-a nie wymaga sieci:

    python3 narzedzia/pdf/zbuduj_czcionki.py [--pobierz]
"""

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from fontTools.merge import Merger
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "src" / "fonty"

PAKIETY = {
    "@fontsource/source-serif-4": {
        "prefiks": "source-serif-4",
        "nazwa": "Source Serif 4",
        "style": {
            "400-normal": ("SS4", "Regular"),
            "400-italic": ("SS4-It", "Italic"),
            "600-normal": ("SS4-Sb", "SemiBold"),
            "700-normal": ("SS4-B", "Bold"),
            "700-italic": ("SS4-BIt", "Bold Italic"),
        },
    },
    "@fontsource/source-sans-3": {
        "prefiks": "source-sans-3",
        "nazwa": "Source Sans 3",
        "style": {
            "400-normal": ("SS3", "Regular"),
            "600-normal": ("SS3-Sb", "SemiBold"),
            "700-normal": ("SS3-B", "Bold"),
        },
    },
}


def pobierz(pakiet, katalog):
    """npm pack <pakiet> i rozpakowanie do katalogu."""
    tar = os.path.join(katalog, "p.tgz")
    subprocess.run(["npm", "pack", pakiet, "--silent", "--pack-destination", katalog],
                   check=True, stdout=subprocess.DEVNULL, cwd=katalog)
    pliki = [f for f in os.listdir(katalog) if f.endswith(".tgz")]
    if not pliki:
        raise SystemExit(f"nie udało się pobrać {pakiet}")
    with tarfile.open(os.path.join(katalog, pliki[0])) as t:
        t.extractall(katalog, filter="data")


def scal(pliki, cel):
    font = Merger().merge(pliki)
    font.save(cel)
    ok = TTFont(cel).getBestCmap()
    for znak in "AZaz09ąćęłńóśźżĄĆĘŁŃÓŚŹŻ–—„”…":
        if ord(znak) not in ok:
            raise SystemExit(f"{cel}: brak znaku {znak!r} po scaleniu")
    return len(ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pobierz", action="store_true", help="pobierz paczki z npm (domyślnie: użyj katalogu roboczego)")
    ap.add_argument("--zrodlo", default="/tmp/fontsource", help="katalog z rozpakowanymi paczkami")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    zrodlo = Path(args.zrodlo)
    zrodlo.mkdir(parents=True, exist_ok=True)

    for pakiet, opis in PAKIETY.items():
        katalog = zrodlo / opis["prefiks"]
        if args.pobierz or not katalog.exists():
            katalog.mkdir(parents=True, exist_ok=True)
            if not any(katalog.iterdir()):
                print(f"pobieram {pakiet} ...")
                pobierz(pakiet, str(katalog))
        for styl, (nazwa, podtytul) in opis["style"].items():
            pliki = [
                katalog / "files" / f"{opis['prefiks']}-latin-{styl}.woff",
                katalog / "files" / f"{opis['prefiks']}-latin-ext-{styl}.woff",
            ]
            braki = [str(p) for p in pliki if not p.exists()]
            if braki:
                raise SystemExit(f"brak plików: {braki}")
            cel = OUT / f"{nazwa}.ttf"
            liczba = scal([str(p) for p in pliki], str(cel))
            print(f"{cel.name:12s} {opis['nazwa']} {podtytul:12s} glifów: {liczba}")

    print("gotowe ->", OUT)


if __name__ == "__main__":
    sys.exit(main())
