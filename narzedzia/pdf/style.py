#!/usr/bin/env python3
"""
Styl dokumentu PDF: czcionki, kolory, akapity, ramki, tabele, wzory.

Moduł jest „bliźniakiem” arkusza CSS z src/rozwiazania.template.html —
te same kolory, ta sama hierarchia nagłówków i te same rodzaje ramek.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[2]
FONTY = ROOT / "src" / "fonty"

# ---------------------------------------------------------------- strony
PAGE = (210 * mm, 297 * mm)          # A4
MARGIN_X = 25.5 * mm
MARGIN_TOP = 19 * mm
MARGIN_BOTTOM = 20 * mm
TEXT_WIDTH = PAGE[0] - 2 * MARGIN_X  # ~159 mm

BODY_SIZE = 10.5
LEADING = 16.3

# ---------------------------------------------------------------- kolory
INK = colors.HexColor("#1f2328")
INK_SOFT = colors.HexColor("#3c434c")
MUTED = colors.HexColor("#6f6a60")
FAINT = colors.HexColor("#8a8578")
LINE = colors.HexColor("#ddd8cd")
PAPER = colors.HexColor("#fdfcfa")
BLUE = colors.HexColor("#1d4ed8")
GREEN = colors.HexColor("#0f766e")
AMBER = colors.HexColor("#92400e")
VIOLET = colors.HexColor("#5b21b6")
RED = colors.HexColor("#b42318")

BOX_THEMES = {
    "box--teoria": dict(left=BLUE, line=colors.HexColor("#dbe3fb"), bg=colors.HexColor("#f2f5ff"), label=BLUE),
    "box--rozw": dict(left=colors.HexColor("#333a42"), line=LINE, bg=colors.white, label=INK),
    "box--kom": dict(left=GREEN, line=colors.HexColor("#cdeee4"), bg=colors.HexColor("#f0fdf8"), label=GREEN),
    "box--uwaga": dict(left=AMBER, line=colors.HexColor("#f3e3bb"), bg=colors.HexColor("#fffdf3"), label=AMBER),
    "box--blad": dict(left=RED, line=colors.HexColor("#f6d9d6"), bg=colors.HexColor("#fff7f6"), label=RED),
    "box--odp": dict(left=VIOLET, line=colors.HexColor("#e2dbfb"), bg=colors.HexColor("#f8f6ff"), label=VIOLET),
}


def zarejestruj_czcionki():
    """Rejestruje rodzinę szeryfową (tekst) i bezszeryfową (etykiety)."""
    pliki = {
        "SS4": "SS4.ttf", "SS4-B": "SS4-B.ttf", "SS4-I": "SS4-It.ttf", "SS4-BI": "SS4-BIt.ttf",
        "SS4-Sb": "SS4-Sb.ttf",
        "SS3": "SS3.ttf", "SS3-B": "SS3-B.ttf", "SS3-Sb": "SS3-Sb.ttf",
    }
    for nazwa, plik in pliki.items():
        pdfmetrics.registerFont(TTFont(nazwa, str(FONTY / plik)))
    pdfmetrics.registerFontFamily("SS4", normal="SS4", bold="SS4-B", italic="SS4-I", boldItalic="SS4-BI")
    pdfmetrics.registerFontFamily("SS3", normal="SS3", bold="SS3-B", italic="SS3", boldItalic="SS3-B")
    return pliki


SERIF_EX_RATIO = 0.465  # wysokość x w Source Serif 4 (sxHeight/upem ~ 0.465)


def style():
    """Słownik stylów akapitowych."""
    baza = dict(fontName="SS4", fontSize=BODY_SIZE, leading=LEADING, textColor=INK,
                hyphenationLang="pl_PL", embeddedHyphenation=1, uriWasteReduce=0.3,
                spaceShrinkage=0.08, allowWidows=0)
    s = {}
    s["body"] = ParagraphStyle("body", alignment=TA_JUSTIFY, spaceAfter=6.2, **baza)
    s["body_first"] = ParagraphStyle("body_first", parent=s["body"], spaceBefore=0)
    s["lead"] = ParagraphStyle("lead", parent=s["body"], fontSize=11.3, leading=17.6,
                               textColor=INK_SOFT, spaceAfter=10)
    s["kicker"] = ParagraphStyle("kicker", fontName="SS3-B", fontSize=7.2, leading=9.4,
                                 textColor=MUTED, spaceAfter=5)
    s["title"] = ParagraphStyle("title", fontName="SS4-B", fontSize=23, leading=26.4,
                                textColor=INK, spaceAfter=6)
    s["subtitle"] = ParagraphStyle("subtitle", fontName="SS4-I", fontSize=11.4, leading=16,
                                   textColor=MUTED, spaceAfter=8)
    s["meta"] = ParagraphStyle("meta", fontName="SS3", fontSize=7.8, leading=11,
                               textColor=MUTED, spaceAfter=2)
    s["h2tag"] = ParagraphStyle("h2tag", fontName="SS3-B", fontSize=7.6, leading=9.6,
                                textColor=MUTED, spaceAfter=2.5, spaceBefore=0)
    s["h2"] = ParagraphStyle("h2", fontName="SS4-B", fontSize=16.5, leading=19.5,
                             textColor=INK, spaceBefore=0, spaceAfter=7)
    s["h3"] = ParagraphStyle("h3", fontName="SS4-B", fontSize=13.2, leading=16.4,
                             textColor=INK, spaceBefore=15, spaceAfter=5.5)
    s["h4"] = ParagraphStyle("h4", fontName="SS4-B", fontSize=10.7, leading=14,
                             textColor=INK, spaceBefore=9.5, spaceAfter=2.4)
    s["label"] = ParagraphStyle("label", fontName="SS3-B", fontSize=7.1, leading=9.2,
                                textColor=MUTED, spaceAfter=3.4)
    s["caption"] = ParagraphStyle("caption", fontName="SS3", fontSize=8.15, leading=11.6,
                                  textColor=MUTED, alignment=TA_CENTER, spaceBefore=5,
                                  spaceAfter=2)
    s["th"] = ParagraphStyle("th", fontName="SS3-B", fontSize=8.2, leading=10.8, textColor=INK)
    s["td"] = ParagraphStyle("td", fontName="SS4", fontSize=9.1, leading=12.6, textColor=INK)
    s["td_c"] = ParagraphStyle("td_c", parent=s["td"], alignment=TA_CENTER)
    s["bullet"] = ParagraphStyle("bullet", parent=s["body"], leftIndent=13, bulletIndent=2.5,
                                 spaceAfter=3.2)
    s["bullet2"] = ParagraphStyle("bullet2", parent=s["bullet"], leftIndent=26, bulletIndent=15,
                                  spaceAfter=2.4, fontSize=BODY_SIZE - 0.3)
    s["li"] = ParagraphStyle("li", parent=s["body"], leftIndent=0, spaceAfter=3.6)
    s["li2"] = ParagraphStyle("li2", parent=s["li"], spaceAfter=2.6, fontSize=BODY_SIZE - 0.4,
                              leading=LEADING - 0.8)
    s["proof"] = ParagraphStyle("proof", parent=s["body"], leftIndent=10, spaceAfter=4,
                                textColor=INK_SOFT)
    s["proof_label"] = ParagraphStyle("proof_label", fontName="SS4-I", fontSize=9.4, leading=12,
                                      textColor=MUTED, leftIndent=10, spaceBefore=2, spaceAfter=1.5)
    s["note"] = ParagraphStyle("note", fontName="SS3", fontSize=8.4, leading=11.6,
                               textColor=MUTED)
    s["footer"] = ParagraphStyle("footer", fontName="SS3", fontSize=8.1, leading=12,
                                 textColor=MUTED, alignment=TA_LEFT, spaceAfter=5)
    s["toc0"] = ParagraphStyle("toc0", fontName="SS4-B", fontSize=10.4, leading=15.4,
                               textColor=INK, spaceBefore=6)
    s["toc1"] = ParagraphStyle("toc1", fontName="SS4", fontSize=9.9, leading=14,
                               textColor=INK_SOFT, leftIndent=14, firstLineIndent=-0)
    s["toc_title"] = ParagraphStyle("toc_title", fontName="SS3-B", fontSize=7.6, leading=10,
                                    textColor=MUTED, spaceAfter=6)
    return s
