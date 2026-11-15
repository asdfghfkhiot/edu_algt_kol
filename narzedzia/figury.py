#!/usr/bin/env python3
"""
Rysunki SVG do dokumentu z rozwiązaniami (zadania 3 i 5).

Każdy rysunek jest generowany w układzie współrzędnych matematycznych
i zapisywany jako samodzielny plik SVG w src/figury/ (bez zależności
zewnętrznych, więc można go wkleić bezpośrednio do HTML).

Uruchomienie:  python3 narzedzia/figury.py
"""

import math
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "figury")

INK = "#22272e"
AXIS = "#8b949e"
BLUE = "#1d4ed8"
RED = "#b42318"
GREEN = "#0f766e"
FONT = "Georgia, 'Times New Roman', 'DejaVu Serif', serif"


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Fig:
    """Prosta kanwa: współrzędne matematyczne -> piksele."""

    def __init__(self, xmin, xmax, ymin, ymax, scale, pad=18, background="none"):
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax
        self.s = scale
        self.pad = pad
        self.w = (xmax - xmin) * scale + 2 * pad
        self.h = (ymax - ymin) * scale + 2 * pad
        self.bg = background
        self.parts = []
        self._markers = set()

    # --- przekształcenia ---
    def px(self, x):
        return self.pad + (x - self.xmin) * self.s

    def py(self, y):
        return self.pad + (self.ymax - y) * self.s

    def pt(self, x, y):
        return f"{self.px(x):.2f},{self.py(y):.2f}"

    # --- elementy ---
    def raw(self, s):
        self.parts.append(s)

    def polygon(self, pts, fill="none", stroke="none", sw=1.4, dash=None, opacity=1.0,
                linejoin="round"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p = " ".join(self.pt(x, y) for x, y in pts)
        self.raw(
            f'<polygon points="{p}" fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d} stroke-linejoin="{linejoin}"/>'
        )

    def polyline(self, pts, stroke=INK, sw=1.4, dash=None, opacity=1.0, cap="round"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p = " ".join(self.pt(x, y) for x, y in pts)
        self.raw(
            f'<polyline points="{p}" fill="none" stroke="{stroke}" stroke-width="{sw}"'
            f'{d} stroke-opacity="{opacity}" stroke-linecap="{cap}" stroke-linejoin="round"/>'
        )

    def segment(self, x1, y1, x2, y2, **kw):
        self.polyline([(x1, y1), (x2, y2)], **kw)

    def circle(self, x, y, r, fill="none", stroke=INK, sw=1.4, dash=None, opacity=1.0):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.raw(
            f'<circle cx="{self.px(x):.2f}" cy="{self.py(y):.2f}" r="{r * self.s:.2f}" '
            f'fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" stroke-width="{sw}"{d}/>'
        )

    def dot(self, x, y, r=4.2, fill=INK, stroke="#ffffff", sw=1.4):
        self.raw(
            f'<circle cx="{self.px(x):.2f}" cy="{self.py(y):.2f}" r="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>'
        )

    def hole(self, x, y, r=4.2, stroke=INK, sw=1.6):
        self.raw(
            f'<circle cx="{self.px(x):.2f}" cy="{self.py(y):.2f}" r="{r}" fill="#ffffff" '
            f'stroke="{stroke}" stroke-width="{sw}"/>'
        )

    def arrow(self, x1, y1, x2, y2, stroke=INK, sw=1.4, dash=None, head=7, opacity=1.0):
        """Strzałka od (x1,y1) do (x2,y2) ze grotem w punkcie końcowym."""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        X1, Y1, X2, Y2 = self.px(x1), self.py(y1), self.px(x2), self.py(y2)
        self.raw(
            f'<line x1="{X1:.2f}" y1="{Y1:.2f}" x2="{X2:.2f}" y2="{Y2:.2f}" stroke="{stroke}" '
            f'stroke-width="{sw}"{d} stroke-opacity="{opacity}" stroke-linecap="round" '
            f'marker-end="url(#arrow-{stroke.lstrip("#")}-{head})"/>'
        )
        self._markers.add((stroke, head))

    def axis_arrow(self, x1, y1, x2, y2, stroke=AXIS, sw=1.2):
        X1, Y1, X2, Y2 = self.px(x1), self.py(y1), self.px(x2), self.py(y2)
        self.raw(
            f'<line x1="{X1:.2f}" y1="{Y1:.2f}" x2="{X2:.2f}" y2="{Y2:.2f}" stroke="{stroke}" '
            f'stroke-width="{sw}" marker-end="url(#axisarrow)"/>'
        )

    def text(self, x, y, s, size=13, fill=INK, anchor="start", weight="normal",
             italic=False, dy=0.0, dx=0.0, opacity=1.0, bg=None):
        style = f'font-family:{FONT};font-size:{size}px;font-weight:{weight}'
        if italic:
            style += ";font-style:italic"
        X, Y = self.px(x) + dx, self.py(y) + dy
        if bg:
            w = 0.56 * size * len(s) + 6
            h = size + 5
            ox = {"start": 0, "middle": w / 2, "end": w}[anchor]
            self.raw(
                f'<rect x="{X - ox:.1f}" y="{Y - size * 0.82:.1f}" width="{w:.1f}" height="{h:.1f}" '
                f'fill="{bg}" rx="3" opacity="0.92"/>'
            )
        self.raw(
            f'<text x="{X:.2f}" y="{Y:.2f}" style="{style}" fill="{fill}" '
            f'text-anchor="{anchor}" opacity="{opacity}">{esc(s)}</text>'
        )

    def arc(self, cx, cy, r, a1, a2, stroke=RED, sw=1.3, dash=None):
        """Łuk okręgu (kąty w stopniach, przeciwnie do ruchu wskazówek zegara)."""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        a1r, a2r = math.radians(a1), math.radians(a2)
        x1, y1 = cx + r * math.cos(a1r), cy + r * math.sin(a1r)
        x2, y2 = cx + r * math.cos(a2r), cy + r * math.sin(a2r)
        large = 1 if (a2 - a1) % 360 > 180 else 0
        R = r * self.s
        self.raw(
            f'<path d="M {self.px(x1):.2f} {self.py(y1):.2f} A {R:.2f} {R:.2f} 0 {large} 0 '
            f'{self.px(x2):.2f} {self.py(y2):.2f}" fill="none" stroke="{stroke}" '
            f'stroke-width="{sw}"{d}/>'
        )

    def svg(self, label):
        markers = ""
        for c, hd in sorted(self._markers):
            markers += (
                f'<marker id="arrow-{c.lstrip("#")}-{hd}" viewBox="0 0 10 10" refX="8.8" refY="5" '
                f'markerWidth="{hd}" markerHeight="{hd}" orient="auto">'
                f'<path d="M 0 0.8 L 9.6 5 L 0 9.2 z" fill="{c}"/></marker>'
            )
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w:.1f} {self.h:.1f}" '
            f'width="100%" role="img" aria-label="{esc(label)}" style="max-width:100%;height:auto">'
            f"<defs>"
            f'<marker id="axisarrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" '
            f'markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M 0 1 L 9 5 L 0 9 z" fill="{AXIS}"/></marker>'
            f"{markers}</defs>"
        )
        if self.bg != "none":
            head += f'<rect x="0" y="0" width="{self.w:.1f}" height="{self.h:.1f}" fill="{self.bg}"/>'
        return head + "".join(self.parts) + "</svg>"


def save(name, svg):
    path = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("<!-- wygenerowane przez narzedzia/figury.py -->\n" + svg + "\n")
    print("zapisano", os.path.relpath(path, os.path.dirname(OUT)))


# ======================================================================
# Rysunek 1: zadanie 3 - pierwiastki 64j i rozwiązania (z+2j)^3 = 64j
# ======================================================================
def rysunek_zad3():
    S = 33.0
    f = Fig(-8.7, 7.6, -9.6, 5.5, S, pad=16, background="#ffffff")
    r3 = math.sqrt(3)

    # osie
    f.axis_arrow(f.xmin + 0.4, 0, f.xmax - 0.3, 0)
    f.axis_arrow(0, f.ymin + 0.4, 0, f.ymax - 0.3)
    f.text(f.xmax - 0.3, 0, "Re", size=13, fill=AXIS, anchor="end", dy=17)
    f.text(0, f.ymax - 0.35, "Im", size=13, fill=AXIS, anchor="start", dx=8, dy=4)

    # okrąg pierwiastków w_k z 64j: środek 0, promień 4
    f.circle(0, 0, 4, stroke=BLUE, sw=1.2, dash="5 4", opacity=0.55)
    # okrąg rozwiązań z: środek -2j, promień 4
    f.circle(0, -2, 4, stroke=BLUE, sw=1.9, opacity=0.9)
    f.text(2.45, 3.42, "|w| = 4", size=12.5, fill=BLUE, anchor="start", opacity=0.95)
    f.text(-4.35, -3.25, "|z + 2j| = 4", size=12.5, fill=BLUE, anchor="end", opacity=0.95)

    # ramiona kąta 2π/3 w środku (0,-2)
    for ang in (30, 150, 270):
        f.segment(0, -2, 4 * math.cos(math.radians(ang)), -2 + 4 * math.sin(math.radians(ang)),
                  stroke=RED, sw=0.9, opacity=0.35)
    f.arc(0, -2, 1.25, 30, 150, stroke=RED, sw=1.4)
    f.text(0.02, -0.66, "2π/3", size=12.5, fill=RED, anchor="middle")

    # trójkąt foremny łączący rozwiązania
    zs = [(2 * r3, 0), (-2 * r3, 0), (0, -6)]
    f.polygon(zs, fill=BLUE, stroke=BLUE, sw=1.1, opacity=0.07)

    # pierwiastki w_k (punkty pomocnicze, puste kółka)
    ws = [(2 * r3, 2), (-2 * r3, 2), (0, -4)]
    for (x, y) in ws:
        f.hole(x, y, r=4.0, stroke=BLUE, sw=1.5)
    f.text(2 * r3 + 0.2, 2.42, "w₀ = 2√3 + 2j", size=12.5, fill=BLUE, anchor="start")
    f.text(-2 * r3 - 0.2, 2.42, "w₁ = −2√3 + 2j", size=12.5, fill=BLUE, anchor="end")
    f.text(-1.25, -4.34, "w₂ = −4j", size=12.5, fill=BLUE, anchor="end")

    # przesunięcie o -2j
    for (x, y) in ws:
        f.arrow(x, y, x, y - 2, stroke=GREEN, sw=1.3, dash="4 3", opacity=0.9)

    # rozwiązania z_k
    for (x, y) in zs:
        f.dot(x, y, r=5.0, fill=RED)
    f.text(3.95, -0.02, "z₀ = 2√3", size=13.5, fill=RED, anchor="start",
           dy=11, weight="bold")
    f.text(-3.95, -0.02, "z₁ = −2√3", size=13.5, fill=RED, anchor="end",
           dy=11, weight="bold")
    f.text(0.22, -6.06, "z₂ = −6j", size=13.5, fill=RED, anchor="start", dy=16, weight="bold")

    # środek okręgu rozwiązań
    f.dot(0, -2, r=3.4, fill=INK)
    f.text(-0.18, -2.02, "−2j", size=12.5, fill=INK, anchor="end", dy=5)

    # legenda
    lx, tx = -8.35, -7.85
    f.hole(lx + 0.16, 4.62, r=4.0, stroke=BLUE, sw=1.5)
    f.text(tx, 4.62, "w₀, w₁, w₂ — pierwiastki 64j", size=12, fill=BLUE)
    f.dot(lx + 0.16, 3.78, r=4.6, fill=RED)
    f.text(tx, 3.78, "z₀, z₁, z₂ — rozwiązania", size=12, fill=RED)
    f.arrow(lx - 0.06, 2.94, lx + 0.34, 2.94, stroke=GREEN, sw=1.3, dash="4 3")
    f.text(tx, 2.94, "przesunięcie o −2j", size=12, fill=GREEN)
    return f.svg("Płaszczyzna zespolona: pierwiastki trzeciego stopnia z 64j oraz rozwiązania równania (z+2j)^3 = 64j")


# ======================================================================
# Rysunki 2-4: zadanie 5 - rodzina trójkątów
# ======================================================================
def _osie_zad5(f):
    f.axis_arrow(f.xmin + 0.15, 0, f.xmax - 0.05, 0)
    f.axis_arrow(0, f.ymin + 0.15, 0, f.ymax - 0.02)
    f.text(f.xmax - 0.05, 0, "x", size=12.5, fill=AXIS, anchor="start", dx=-6, dy=16)
    f.text(0, f.ymax - 0.02, "y", size=12.5, fill=AXIS, anchor="start", dx=7, dy=10)


def _trojkat(f, t, fill=BLUE, stroke=BLUE, sw=1.5, opacity=0.0):
    f.polygon([(0, 0), (1, t), (-1, t)], fill=fill, stroke=stroke, sw=sw, opacity=opacity)
    f.segment(-1, t, 1, t, stroke=stroke, sw=sw)
    f.polyline([(0, 0), (1, t)], stroke=stroke, sw=sw)
    f.polyline([(0, 0), (-1, t)], stroke=stroke, sw=sw)


CANVAS5 = dict(xmin=-4.5, xmax=3.35, ymin=-0.62, ymax=3.18, scale=54.0, pad=16)


def rysunek_zad5_trojkaty():
    f = Fig(background="#ffffff", **CANVAS5)
    _osie_zad5(f)

    for t, col, sw, op in [
        (0.6, "#9aa7b8", 1.2, 0.0),
        (1.2, "#9aa7b8", 1.2, 0.0),
        (2.4, BLUE, 1.9, 0.10),
    ]:
        _trojkat(f, t, fill=col, stroke=col, sw=sw, opacity=op)

    # podpisy trójkątów (lewy margines, żeby nie kolidowały z wierzchołkami)
    f.text(1.14, 0.6, "∇₀,₆", size=12.5, fill="#64748b", anchor="start", dy=5)
    f.text(1.14, 1.2, "∇₁,₂", size=12.5, fill="#64748b", anchor="start", dy=5)
    f.text(1.14, 2.4, "∇₂,₄", size=13, fill=BLUE, anchor="start", dy=8)

    # wierzchołki trójkąta ∇t
    t = 2.4
    for (x, y) in [(0, 0), (1, t), (-1, t)]:
        f.dot(x, y, r=4.0, fill=INK)
    f.text(0, 0, "A = (0, 0)", size=12.5, anchor="end", dx=-9, dy=19)
    f.text(1, t, "Bₜ = (1, t)", size=12.5, anchor="start", dx=5, dy=-16)
    f.text(-1, t, "Cₜ = (−1, t)", size=12.5, anchor="end", dx=-5, dy=-9)

    # przekrój poziomy + jego opis po lewej
    yd = 1.7
    f.segment(-yd / t, yd, yd / t, yd, stroke=RED, sw=2.2)
    f.text(-yd / t - 0.12, yd, "przekrój poziomy:  |x| ⩽ y/t", size=12, fill=RED,
           anchor="end", dy=4)
    return f.svg(
        "Rodzina trójkątów wypełnionych o wierzchołkach A=(0,0), B=(1,t), C=(-1,t) dla t = 0,6; 1,2; 2,4"
    )


def rysunek_zad5_suma():
    f = Fig(background="#ffffff", **CANVAS5)
    _osie_zad5(f)

    # pas [-1,1] x [0, +inf)
    f.polygon([(-1, 0), (1, 0), (1, 3.1), (-1, 3.1)], fill=GREEN, stroke="none", opacity=0.15)
    f.segment(-1, 0, 1, 0, stroke=GREEN, sw=2.2)
    for x in (-1, 1):
        f.segment(x, 0, x, 2.98, stroke=GREEN, sw=2.2)
        f.arrow(x, 2.9, x, 3.12, stroke=GREEN, sw=2.2, head=5)
    f.text(-1, 0, "−1", size=12, fill=GREEN, anchor="middle", dy=17)
    f.text(1, 0, "1", size=12, fill=GREEN, anchor="middle", dy=17)

    # trójkąty rodziny (cienkie) - widać, że "wypełniają" pas
    for t in (0.75, 1.5, 2.25, 3.0):
        f.polygon([(0, 0), (1, t), (-1, t)], fill="none", stroke=BLUE, sw=1.0, opacity=0.4)

    f.arrow(1.62, 0.1, 1.62, 3.0, stroke=GREEN, sw=1.2, head=7)
    f.text(1.72, 1.6, "y → +∞", size=11.5, fill=GREEN, anchor="start", dy=4)
    f.text(-1.2, 2.6, "suma:  −1 ⩽ x ⩽ 1,  y ⩾ 0", size=13, fill=GREEN, anchor="end",
           weight="bold")
    return f.svg("Suma rodziny trójkątów: domknięty pas pionowy -1 <= x <= 1, y >= 0")


def rysunek_zad5_iloczyn():
    f = Fig(background="#ffffff", **CANVAS5)
    _osie_zad5(f)

    for t, lab in ((1.0, "∇₁"), (1.9, "∇₂"), (2.9, "∇₃")):
        f.polygon([(0, 0), (1, t), (-1, t)], fill="none", stroke=BLUE, sw=1.0, opacity=0.42)
        f.text(1.06, t, lab, size=12, fill=BLUE, anchor="start", dy=4, opacity=0.9)

    # część wspólna: odcinek na osi Oy od 0 do 1
    f.segment(0, 0, 0, 1, stroke=GREEN, sw=3.6)
    f.dot(0, 1, r=4.4, fill=GREEN)
    f.text(-1.35, -0.4, "część wspólna:  x = 0,  0 ⩽ y ⩽ 1", size=12.5, fill=GREEN,
           anchor="middle", weight="bold")
    return f.svg("Część wspólna trójkątów dla t naturalnych: odcinek od (0,0) do (0,1) na osi Oy")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    save("zad3_plaszczyzna.svg", rysunek_zad3())
    save("zad5_trojkaty.svg", rysunek_zad5_trojkaty())
    save("zad5_suma.svg", rysunek_zad5_suma())
    save("zad5_iloczyn.svg", rysunek_zad5_iloczyn())
