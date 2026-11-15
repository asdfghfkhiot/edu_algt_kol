#!/usr/bin/env python3
"""
Konwersja szablonu HTML (src/rozwiazania.template.html) na dokument PDF.

Podejście: drzewo HTML -> flowables ReportLab. Szablon jest nasz własny i semantyczny
(h2.part / h3 / h4 / p / div.box / table / figure / ol / ul), więc konwersja jest
deterministyczna i nie potrzebuje ogólnego silnika CSS.

Kluczowa zasada: kolejne elementy liniowe (tekst, <em>, <strong>, wzory) w jednym
kontenerze tworzą JEDEN akapit; elementy blokowe (lista, tabela, rysunek, dowód)
przerywają akapit.
"""

import re
from html.parser import HTMLParser
from pathlib import Path

import resvg_py
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, HRFlowable,
                                Image, PageBreak, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from .style import (BODY_SIZE, BOX_THEMES, INK, LEADING, LINE, MUTED, PAGE, TEXT_WIDTH,
                    style)

ROOT = Path(__file__).resolve().parents[2]
VOID = {"br", "hr", "img", "meta", "link", "input"}

# znaczniki, które przerywają akapit (reszta jest traktowana jako treść liniowa)
BLOKI = {"p", "h2", "h3", "h4", "ul", "ol", "table", "figure", "hr", "div", "header",
         "nav", "footer", "blockquote"}


# --------------------------------------------------------------------- drzewo
class Node:
    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.children = []

    @property
    def cls(self):
        return self.attrs.get("class", "")

    def ma_klase(self, nazwa):
        return nazwa in self.cls.split()

    def text(self):
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def find_all(self, tag=None, cls=None):
        res = []
        for c in self.children:
            if isinstance(c, str):
                continue
            if (tag is None or c.tag == tag) and (cls is None or c.ma_klase(cls)):
                res.append(c)
            res.extend(c.find_all(tag, cls))
        return res


class Tree(HTMLParser):
    """Drzewo HTML z szablonu.

    Przed parsowaniem zamieniamy na &lt; te znaki '<', które nie rozpoczynają znacznika
    (np. nierówność p^2-4q < 0 wewnątrz wzoru) — inaczej parser HTML potraktowałby je
    jako początek taga i urwał treść. '<' przed literą wewnątrz wzoru jest błędem
    w szablonie (patrz kontrola w narzedzia/build.mjs).
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]

    @classmethod
    def parsuj(cls, html):
        t = cls()
        t.feed(re.sub(r"<(?![A-Za-z/!?])", "&lt;", html))
        t.close()
        return t

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, dict(attrs)))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def akapit(markup, st):
    """Paragraph, który nie pozwala, by wysoki wzór (ułamek, suma) wchodził w linię wyżej.

    ReportLab liczy interlinię ze stylu; obrazek wyższy od niej wystawałby ponad wiersz,
    dlatego dla akapitu z takim wzorem podnosimy interlinię do wysokości obrazka.
    """
    potrzebne = najszerszy = 0.0
    for m in re.finditer(r'<img [^>]*width="([\d.]+)"[^>]*height="([\d.]+)"[^>]*valign="(-?[\d.]+)"',
                         markup):
        w, h, v = float(m.group(1)), float(m.group(2)), float(m.group(3))
        potrzebne = max(potrzebne, h + max(0.0, -v))
        najszerszy = max(najszerszy, w)
    if potrzebne > st.leading:
        # lekko podnosimy interlinię, ale bez rozrzedzania całego akapitu:
        # pełne dostosowanie tylko wtedy, gdy wzór naprawdę wystaje znacznie
        if potrzebne > st.leading * 1.5:
            nowa = potrzebne + 0.9
        else:
            nowa = max(st.leading, min(potrzebne + 0.9, st.leading * 1.30))
        st = ParagraphStyle(f"{st.name}~{nowa:.1f}", parent=st, leading=nowa)
    if najszerszy > 0.30 * TEXT_WIDTH and st.alignment == TA_JUSTIFY:
        # bardzo szeroki wzór w linii nie zostawia miejsca na równe odstępy —
        # wtedy wyrównujemy do lewej, żeby nie robić „ dziur” między wyrazami
        st = ParagraphStyle(f"{st.name}~LR", parent=st, alignment=TA_LEFT)
    return Paragraph(markup, st)


def _opakuj(node):
    kontener = Node("div")
    kontener.children.append(node)
    return kontener


# ------------------------------------------------------------------ wzory blokowe
class MathBlock(Flowable):
    """Wzór blokowy rysowany wektorowo, wyśrodkowany, z poprawną głębokością."""

    def __init__(self, renderer, tex, space_before=6.0, space_after=7.5, unit=6.0):
        super().__init__()
        self.tex = tex
        self.r = renderer
        m = renderer.meta(tex, True)
        self.w, self.h, self.d = m["w_pt"], m["h_pt"], m["d_pt"]
        self.sb, self.sa = space_before, space_after
        self.unit = unit
        # wzory z \text{...} zawierają w SVG prawdziwy tekst; svglib rysuje go czcionką
        # standardową (bez polskich znaków), więc takie wzory rasteryzujemy
        self.png = None
        plik_svg = m.get("svg") or ""
        if plik_svg and "<text" in Path(plik_svg).read_text(encoding="utf-8"):
            self.png = renderer.png(tex, True)
            self.drawing = None
        else:
            self.drawing = renderer.drawing(tex, True)
        self.avail = TEXT_WIDTH
        self.scale = 1.0

    def wrap(self, availWidth, availHeight):
        self.avail = availWidth
        self.scale = min(1.0, (availWidth - 2) / self.w) if self.w > 0 else 1.0
        # h to pełna wysokość SVG, a d jest jej częścią poniżej linii bazowej.
        return availWidth, self.h * self.scale + self.sb + self.sa

    def draw(self):
        c = self.canv
        s = self.scale * (self.r.ex_pt / self.unit)
        x = (self.avail - self.w * self.scale) / 2.0
        c.saveState()
        if self.png:
            c.translate(x, self.sa)
            c.drawImage(self.png, 0, 0, width=self.w * self.scale,
                        height=self.h * self.scale, mask="auto")
        else:
            c.translate(x, self.sa)
            c.scale(s, s)
            renderPDF.draw(self.drawing, c, 0, 0)
        c.restoreState()


class Ramka(Flowable):
    """Opakowanie tabelki, żeby mogła się dzielić między stronami."""

    def __init__(self, tabela, space_before=6.0, space_after=6.0):
        super().__init__()
        self.t = tabela
        self.spaceBefore = space_before
        self.spaceAfter = space_after

    def wrap(self, aw, ah):
        self.w, self.h = self.t.wrap(aw, ah)
        return self.w, self.h

    def split(self, aw, ah):
        return self.t.split(aw, ah) or []

    def draw(self):
        self.t.drawOn(self.canv, 0, 0)


# ---------------------------------------------------------------------- konwerter
class Converter:
    def __init__(self, renderer):
        self.r = renderer
        self.S = style()

    # ---------------------------------------------------------------- inline
    def inline(self, node, size=BODY_SIZE, wielkie=False):
        """Zamienia dzieci węzła na znaczniki akapitu ReportLaba."""
        out = []
        for child in node.children if isinstance(node, Node) else node:
            if isinstance(child, str):
                out.append(self._tekst(child, size, wielkie))
                continue
            t, cls = child.tag, child.cls
            if t in ("em", "i"):
                out.append(f"<i>{self.inline(child, size, wielkie)}</i>")
            elif t in ("strong", "b"):
                out.append(f"<b>{self.inline(child, size, wielkie)}</b>")
            elif t == "a":
                out.append(self.inline(child, size, wielkie))
            elif t == "br":
                out.append("<br/>")
            elif t == "code":
                out.append('<font name="SS3" size="%.1f" backColor="#f4f1ea">%s</font>'
                           % (size - 1.1, self._escape(child.text())))
            elif t == "span":
                out.append(self._span(child, size, wielkie))
            else:
                out.append(self.inline(child, size, wielkie))
        return "".join(out)

    def _span(self, node, size, wielkie=False):
        cls = node.cls
        inner = self.inline(node, size, wielkie)
        if "num" in cls.split():
            return f'<font name="SS4" color="#8a8578" size="{size:.1f}">' + inner + "</font>&nbsp;"
        if "note-inline" in cls.split():
            return f'<font name="SS3" size="{size - 1.4:.1f}" color="#6f6a60">' + inner + "</font>"
        if "fig-num" in cls.split():
            return f'<b><font name="SS3-B" size="{size - 2.3:.1f}" color="#3c434c">' + inner + "</font></b>&nbsp;"
        if "pts" in cls.split():
            return f'<font name="SS3-B" size="{size - 1.9:.1f}" color="#5b21b6"> &nbsp;(' + inner + ")</font>"
        if "label" in cls.split():
            return f'<font name="SS3-B" size="7.1" color="#6f6a60">' + inner.upper() + "</font>"
        return inner

    @staticmethod
    def _escape(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _tekst(self, s, size=BODY_SIZE, wielkie=False):
        """Tekst z wzorami w linii -> znaczniki akapitu (wzory jako obrazki).

        Wzory blokowe ($$...$$) zostawiamy nietknięte — inaczej para dolarów
        z „$$” zostałaby dopasowana jako wzór w linii i rozjechała resztę akapitu.
        """
        out = []
        for blok in re.split(r"(\$\$.+?\$\$)", s, flags=re.S):
            if not blok:
                continue
            if blok.startswith("$$") and blok.endswith("$$") and len(blok) > 4:
                out.append(blok)
                continue
            for kawalek in re.split(r"(\$[^$]+\$)", blok):
                if not kawalek:
                    continue
                if kawalek.startswith("$") and kawalek.endswith("$") and len(kawalek) > 2:
                    out.append(self.r.img_tag(kawalek[1:-1].strip(), scale=size / BODY_SIZE))
                else:
                    kawalek = re.sub(r"\s+", " ", kawalek)
                    # Font tekstowy nie zawiera ✓; ten znak renderujemy jako wzór,
                    # tak aby uniknąć zastępczego, pustego kwadratu w PDF.
                    for i, czesc in enumerate(kawalek.split("✓")):
                        if i:
                            out.append(self.r.img_tag(r"\checkmark", scale=size / BODY_SIZE))
                        out.append(self._escape(czesc.upper() if wielkie else czesc))
        return "".join(out)

    def _plain(self, node):
        """Czysty tekst (do spisu treści)."""
        txt = node.text() if isinstance(node, Node) else str(node)
        return re.sub(r"\s+", " ", re.sub(r"\$+", "", txt)).strip()

    # ----------------------------------------------------------------- bloki
    def blocks(self, node, avail=TEXT_WIDTH, depth=0):
        story = []
        for child in node.children:
            if isinstance(child, str):
                story.extend(self._mieszane(node, avail, tylko_ten=child))
                continue
            story.extend(self._blok(child, avail, depth))
        return story

    def _blok(self, node, avail, depth=0):
        t, cls = node.tag, node.cls
        if node.ma_klase("box"):
            return [self.ramka(node, avail, depth)]
        if t == "header":
            return self.hero(node, avail)
        if t == "nav":
            return []                                   # spis treści budujemy sami
        if t == "h2" and node.ma_klase("part"):
            return self.tytul_czesci(node, avail)
        if t == "h3":
            p = akapit(self.inline(node, self.S["h3"].fontSize), self.S["h3"])
            p._toc = (1, self._toc_h3(node))
            # nagłówek nie może zostać sam na dole strony — ale bez „sklejania” z całą ramką,
            # żeby długa ramka mogła się dzielić
            return [CondPageBreak(118), p]
        if t == "h4":
            return [CondPageBreak(135), akapit(self.inline(node, self.S["h4"].fontSize), self.S["h4"])]
        if t == "p":
            markup = self.inline(node, BODY_SIZE).strip()
            if not markup:
                return []
            if markup.startswith("$$") and markup.endswith("$$") and markup.count("$$") == 2:
                return [MathBlock(self.r, markup.strip("$").strip())]
            return [akapit(markup, self.S["body"])]
        if t in ("ul", "ol"):
            return [self.lista(node, avail, depth)]
        if t == "table":
            return [self.tabela(node, avail)]
        if t == "figure":
            return [self.rysunek(node, avail)]
        if t == "hr":
            return [HRFlowable(width="100%", thickness=0.5, color=LINE, spaceBefore=6, spaceAfter=6)]
        if node.ma_klase("proof"):
            return [self.dowod(node, avail, depth)]
        if t == "footer":
            return self.stopka(node, avail)
        return self.blocks(node, avail, depth)

    def _mieszane(self, node, avail, tylko_ten=None, styl=None):
        """Treść liniowa + ewentualne bloki: łączy sąsiednie elementy liniowe w akapity."""
        st = styl or self.S["body"]
        out, buf = [], []

        def oproznij():
            if not buf:
                return
            markup = "".join(buf).strip()
            del buf[:]
            for czesc in re.split(r"(\$\$.+?\$\$)", markup, flags=re.S):
                kawalek = czesc.strip()
                if not kawalek:
                    continue
                m = re.fullmatch(r"\$\$(.+)\$\$", kawalek, re.S)
                if m:
                    out.append(MathBlock(self.r, m.group(1).strip()))
                else:
                    out.append(akapit(kawalek, st))

        for c in [tylko_ten] if tylko_ten is not None else node.children:
            if isinstance(c, str):
                wykryty = re.fullmatch(r"\s*(\$\$.+?\$\$)\s*", c, re.S)
                if wykryty:
                    oproznij()
                    out.append(MathBlock(self.r, wykryty.group(1)[2:-2].strip()))
                else:
                    buf.append(self._tekst(c))
            elif c.tag in BLOKI or c.ma_klase("proof"):
                oproznij()
                out.extend(self._blok(c, avail))
            else:
                buf.append(self.inline(c))
        oproznij()
        return out

    # --------------------------------------------------------------- elementy
    def hero(self, node, avail):
        story = []
        for c in node.children:
            if isinstance(c, str):
                continue
            if c.tag == "p" and c.ma_klase("kicker"):
                story.append(akapit(self._plain(c).upper(), self.S["kicker"]))
            elif c.tag == "h1":
                story.append(akapit(self.inline(c, self.S["title"].fontSize), self.S["title"]))
            elif c.tag == "p" and c.ma_klase("sub"):
                story.append(akapit(self.inline(c, self.S["subtitle"].fontSize), self.S["subtitle"]))
            elif c.tag == "div" and c.ma_klase("meta"):
                pozycje = [self.inline(sp, 7.8) for sp in c.find_all("span")]
                story.append(akapit('<font color="#c9c4b8"> &nbsp;•&nbsp; </font>'.join(pozycje),
                                       self.S["meta"]))
        story.append(HRFlowable(width="100%", thickness=1.1, color=INK, spaceBefore=7, spaceAfter=17))
        return story

    def tytul_czesci(self, node, avail):
        tag = ""
        reszta = Node("h2")
        for c in node.children:
            if isinstance(c, str):
                reszta.children.append(c)
            elif c.ma_klase("tag"):
                tag = self._plain(c)
            else:
                reszta.children.append(c)
        p = akapit(self.inline(reszta, self.S["h2"].fontSize), self.S["h2"])
        p._toc = (0, f"{tag} — {self._plain(reszta)}" if tag else self._plain(reszta))
        # każda część zaczyna się na nowej stronie (wygodne przy druku i przy pracy z plikiem)
        story = [PageBreak()]
        story.append(akapit(tag.upper(), self.S["h2tag"]))
        story.append(p)
        story.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=1, spaceAfter=11))
        return story

    def _toc_h3(self, node):
        czesci = []
        for c in node.children:
            if isinstance(c, str):
                czesci.append(re.sub(r"\s+", " ", re.sub(r"\$+", "", c)))
            elif c.ma_klase("pts"):
                czesci.append(f" — {self._plain(c)}")
            else:
                czesci.append(re.sub(r"\s+", " ", re.sub(r"\$+", "", c.text())))
        return re.sub(r"\s{2,}", " ", "".join(czesci)).strip()

    def ramka(self, node, avail, depth):
        motyw = BOX_THEMES["box--rozw"]
        for k in node.cls.split():
            if k in BOX_THEMES:
                motyw = BOX_THEMES[k]
        tresc = []
        for c in node.children:
            if isinstance(c, str):
                if not c.strip():
                    continue
                tresc.extend(self._mieszane(_opakuj(c), avail - 24))
            elif c.ma_klase("label"):
                tresc.append(self.etykieta(c, motyw["label"], 5.0))
            else:
                tresc.extend(self._mieszane(_opakuj(c), avail - 24))
        if not tresc:
            return Spacer(1, 2)
        # jeden wiersz = jeden element treści: ramka może się wtedy dzielić między stronami
        # (po podziale każda część dostaje własną obwódkę i pasek z lewej)
        wiersze = [[x] for x in tresc]
        if len(wiersze) > 1 and tresc[0].style.name.startswith("etyk"):
            # etykieta w jednym wierszu z pierwszą treścią — nie zostanie sama na końcu strony
            wiersze = [[[tresc[0], tresc[1]]]] + wiersze[2:]
        t = Table(wiersze, colWidths=[avail])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), motyw["bg"]),
            ("BOX", (0, 0), (-1, -1), 0.5, motyw["line"]),
            ("LINEBEFORE", (0, 0), (0, -1), 2.6, motyw["left"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ]))
        return Ramka(t, space_before=7.0, space_after=7.0)

    def etykieta(self, node, kolor, space_after=4.0, kursywa=False):
        """Mała etykieta ramki (bezszeryfowa, wersaliki) — także z matematyką."""
        size = 7.1
        st = ParagraphStyle(
            f"etyk{id(node)}",
            fontName="SS4-I" if kursywa else "SS3-B",
            fontSize=size if not kursywa else 9.4,
            leading=(size + 2.4) if not kursywa else 12.2,
            textColor=kolor, spaceAfter=space_after, spaceBefore=1 if kursywa else 0)
        return akapit(self.inline(node, size if not kursywa else 9.4, wielkie=True),
                         st)

    def dowod(self, node, avail, depth):
        tresc = []
        for c in node.children:
            if isinstance(c, str):
                if not c.strip():
                    continue
                tresc.extend(self._mieszane(_opakuj(c), avail - 16, styl=self.S["proof"]))
            elif c.ma_klase("label"):
                tresc.append(self.etykieta(c, MUTED, 1.5, kursywa=True))
            else:
                tresc.extend(self._mieszane(_opakuj(c), avail - 16, styl=self.S["proof"]))
        t = Table([[x] for x in tresc], colWidths=[avail])
        t.setStyle(TableStyle([
            ("LINEBEFORE", (0, 0), (0, -1), 1.0, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return Ramka(t, space_before=2.0, space_after=3.0)

    def lista(self, node, avail, depth):
        up = node.tag == "ol"
        wieszak = 19 if depth == 0 else 22
        st_li = self.S["li"] if depth == 0 else self.S["li2"]
        pozycje = [c for c in node.children if isinstance(c, Node) and c.tag == "li"]
        wiersze = []
        for i, li in enumerate(pozycje, start=1):
            tresc = self._mieszane(li, avail - wieszak, styl=st_li)
            if not tresc:
                continue
            if up:
                znak = f"{i}." if depth == 0 else f"{i})"
            else:
                znak = "•" if depth == 0 else "–"
            st_b = ParagraphStyle(f"b{depth}_{i}_{id(li)}", fontName="SS4", fontSize=BODY_SIZE,
                                  leading=LEADING, textColor=MUTED if up else INK,
                                  alignment=TA_RIGHT if up else TA_LEFT)
            wiersze.append([akapit(znak, st_b), tresc])
        if not wiersze:
            return Spacer(1, 2)
        t = Table(wiersze, colWidths=[wieszak - 5, avail - (wieszak - 5)])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, -1), 5),
            ("LEFTPADDING", (1, 0), (1, -1), 0),
            ("RIGHTPADDING", (1, 0), (1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2.0 if depth == 0 else 1.4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.0 if depth == 0 else 1.4),
        ]))
        return Ramka(t)

    def tabela(self, node, avail):
        wiersze, naglowki = [], []
        for tr in node.find_all("tr"):
            komorki = [c for c in tr.children if isinstance(c, Node) and c.tag in ("th", "td")]
            if not komorki:
                continue
            naglowki.append(all(c.tag == "th" for c in komorki))
            wiersze.append(komorki)
        if not wiersze:
            return Spacer(1, 2)
        n = max(len(w) for w in wiersze)
        dane, naturalne = [], [6.0] * n
        for w in wiersze:
            wiersz = []
            for j in range(n):
                c = w[j] if j < len(w) else None
                st = self.S["th"] if (c is not None and c.tag == "th") else self.S["td"]
                markup = self.inline(c, st.fontSize) if c is not None else ""
                p = akapit(markup, st)
                try:
                    p.wrap(3000, 3000)
                    naturalne[j] = max(naturalne[j], min(p.width, avail * 0.68))
                except Exception:
                    pass
                wiersz.append(p)
            dane.append(wiersz)
        wagi = [max(x + 14, avail * 0.12) for x in naturalne]
        skala = avail / sum(wagi)
        t = Table(dane, colWidths=[x * skala for x in wagi],
                  repeatRows=1 if naglowki and naglowki[0] else 0)
        cmds = [
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5.5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5.5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ]
        for i, naglowek in enumerate(naglowki):
            if naglowek:
                cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f6f4ef")))
            elif i % 2 == 0:
                cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fbfaf8")))
        t.setStyle(TableStyle(cmds))
        return Ramka(t)

    def rysunek(self, node, avail):
        m = re.search(r"\{\{include:([^}]+)\}\}", node.text())
        if not m:
            return Spacer(1, 2)
        sciezka = ROOT / m.group(1).strip()
        svg = sciezka.read_text(encoding="utf-8")
        vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
        w0, h0 = (float(vb.group(1)), float(vb.group(2))) if vb else (600.0, 400.0)
        szer_pt = min(avail - 14, TEXT_WIDTH - 14)
        wys_pt = h0 * (szer_pt / w0)
        # rysunek nie może zjeść całej strony — inaczej zostawia nad sobą wielką lukę
        maks_h = 0.52 * (PAGE[1] - 39 * mm)
        if wys_pt > maks_h:
            szer_pt *= maks_h / wys_pt
            wys_pt = maks_h
        px = int(round(szer_pt / 72.0 * 420))
        png = Path("/tmp/edu_algt_pdf/fig") / f"{sciezka.stem}-{px}.png"
        png.parent.mkdir(parents=True, exist_ok=True)
        if not png.exists():
            png.write_bytes(bytes(resvg_py.svg_to_bytes(svg_string=svg, width=px,
                                                        serif_family="DejaVu Serif")))
        img = Image(str(png), width=szer_pt, height=wys_pt)
        img.hAlign = "CENTER"
        wewn = [img]
        cap = node.find_all("figcaption")
        if cap:
            wewn.append(akapit(self.inline(cap[0], self.S["caption"].fontSize),
                                  self.S["caption"]))
        t = Table([[wewn]], colWidths=[avail])
        t.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, LINE),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return Ramka(t)

    def stopka(self, node, avail):
        story = [HRFlowable(width="100%", thickness=0.5, color=LINE, spaceBefore=20, spaceAfter=9)]
        for p in node.find_all("p"):
            tekst = p.text()
            if "HTML" in tekst:
                tekst = ("Wersja PDF: te same treści co wersja HTML, złożona z tego samego szablonu "
                         "(narzedzia/build_pdf.py) — wzory blokowe głównie wektorowe, wzory w linii "
                         "w rozdzielczości 620 dpi, czcionki wbudowane w plik.")
                story.append(akapit('<font name="SS3" size="8.1" color="#6f6a60">%s</font>'
                                    % self._escape(tekst), self.S["footer"]))
                continue
            story.append(akapit(self.inline(p, self.S["footer"].fontSize), self.S["footer"]))
        return story


# ---------------------------------------------------------------- szablon dokumentu
class Dokument(BaseDocTemplate):
    def __init__(self, nazwa, **kw):
        BaseDocTemplate.__init__(
            self, nazwa, pagesize=PAGE,
            leftMargin=25.5 * mm, rightMargin=25.5 * mm,
            topMargin=19 * mm, bottomMargin=20 * mm,
            title="Kolokwium 1 — ALGT 2025Z, grupa T2 — zadania 3, 4, 5",
            subject="pierwiastki liczb zespolonych, ułamki proste, rodziny zbiorów",
            author="opracowanie", **kw)
        ramka = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="tresc")
        self.addPageTemplates([PageTemplate(id="strona", frames=[ramka],
                                            onPage=self._stopka_strony)])

    def _stopka_strony(self, canv, doc):
        canv.saveState()
        canv.setFont("SS3", 8.2)
        canv.setFillColor(MUTED)
        canv.drawCentredString(PAGE[0] / 2.0, 11 * mm, str(doc.page))
        canv.setFont("SS3", 7.2)
        canv.setFillColor(colors.HexColor("#a8a29e"))
        canv.drawString(25.5 * mm, 11 * mm, "ALGT 2025Z · grupa T2 · zadania 3–5")
        canv.restoreState()

    def afterFlowable(self, flowable):
        toc = getattr(flowable, "_toc", None)
        if toc:
            self.notify("TOCEntry", (toc[0], toc[1], self.page))


def spis_tresci(S):
    toc = TableOfContents()
    toc.levelStyles = [S["toc0"], S["toc1"]]
    toc.dotsMinLevel = 0
    return toc
