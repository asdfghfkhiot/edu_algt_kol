#!/usr/bin/env python3
"""
Renderowanie wzorów TeX: MathJax (Node) -> SVG -> PNG (resvg) / obiekt wektorowy.

Dwa tryby:
  * wzór w linii  -> PNG w wysokiej rozdzielczości (ReportLab potrafi wstawić obraz
                     do akapitu przez <img .../> i wyrównać go do linii bazowej),
  * wzór blokowy  -> obiekt wektorowy (svglib) rysowany bezpośrednio na stronie,
                     więc duże ułamki i pierwiastki pozostają ostre przy każdym zbliżeniu.

Wymiary: MathJax podaje szerokość/wysokość/głębokość w jednostkach „ex”.
Przeliczamy je na punkty:  w_pt = w_ex * ex_pt,  gdzie ex_pt = EX_RATIO * rozmiar_pisma.
"""

import hashlib
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import resvg_py
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SKRYPT = ROOT / "narzedzia" / "pdf" / "mathjax.mjs"
CACHE = Path("/tmp/edu_algt_pdf/math")

DPI = 620.0          # rozdzielczość wzorów w linii
EM_UNIT = 400.0      # em/ex podawane MathJaxowi (px robocze)
EX_UNIT = 180.0      # -> ex/em = 0.45; wymiary wracają w „ex”, przeliczamy na pt


class MathRenderer:
    def __init__(self, font_size_pt, ex_ratio=0.465, cache_dir=CACHE):
        self.font_size = font_size_pt
        self.ex_pt = ex_ratio * font_size_pt
        self.dir = Path(cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.info = {}                      # (tex, display) -> dict
        self._drawings = {}
        self._svglib = None
        self.liczba_png = 0

    # ------------------------------------------------------------ klucz
    def _key(self, tex, display):
        # Wersja chroni przed użyciem PNG z poprzedniej konfiguracji renderowania.
        h = hashlib.sha1(f"v2|{self.ex_pt}|{int(display)}|{tex}".encode()).hexdigest()[:16]
        return h

    # -------------------------------------------------------- przygotowanie
    def prepare(self, formulas):
        """formulas: iterable (tex, display). Jedno wywołanie Node dla wszystkich nowych."""
        brakujace = []
        seen = set()
        for tex, display in formulas:
            k = (tex, bool(display))
            if k in self.info or k in seen:
                continue
            seen.add(k)
            if not self._z_cache(k):
                brakujace.append(k)

        if brakujace:
            self._policz(brakujace)

    def _z_cache(self, key):
        tex, display = key
        h = self._key(tex, display)
        meta_path = self.dir / f"{h}.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("tex") == tex and meta.get("display") == display:
                # cache jest ważny tylko wtedy, gdy pliki naprawdę istnieją
                if not Path(meta.get("svg", "")).is_file():
                    return False
                if not display and not Path(meta.get("png", "")).is_file():
                    return False
                self.info[key] = meta
                return True
        return False

    def _policz(self, keys):
        zadanie = {
            "em": EM_UNIT,
            "ex": EX_UNIT,
            "items": [
                {"id": self._key(tex, d), "tex": tex, "display": bool(d)}
                for tex, d in keys
            ],
        }
        wej = self.dir / "_in.json"
        wyj = self.dir / "_out.json"
        wej.write_text(json.dumps(zadanie, ensure_ascii=False), encoding="utf-8")
        wynik = subprocess.run(
            ["node", str(SKRYPT), str(wej), str(wyj)],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        if wynik.returncode != 0:
            sys.stderr.write(wynik.stdout + wynik.stderr)
            raise SystemExit("MathJax nie poradził sobie z częścią wzorów")

        dane = json.loads(wyj.read_text(encoding="utf-8"))
        by_id = {self._key(tex, d): (tex, bool(d)) for tex, d in keys}
        for ident, item in dane["items"].items():
            tex, display = by_id[ident]
            meta = {
                "tex": tex,
                "display": display,
                "w_ex": item["width_ex"],
                "h_ex": item["height_ex"],
                "d_ex": item["depth_ex"],
                "w_pt": item["width_ex"] * self.ex_pt,
                "h_pt": item["height_ex"] * self.ex_pt,
                "d_pt": item["depth_ex"] * self.ex_pt,
            }
            svg_path = self.dir / f"{ident}.svg"
            svg_path.write_text(item["svg"], encoding="utf-8")
            meta["svg"] = str(svg_path)
            if not display:
                self._png(svg_path, self.dir / f"{ident}.png", meta["w_pt"])
                meta["png"] = str(self.dir / f"{ident}.png")
            (self.dir / f"{ident}.json").write_text(json.dumps(meta, ensure_ascii=False),
                                                    encoding="utf-8")
            self.info[(tex, display)] = meta

    def _png(self, svg_path, png_path, w_pt):
        if png_path.exists():
            return
        px = max(8, int(round(w_pt / 72.0 * DPI)))
        # wzory z \text{...} mają w SVG prawdziwy tekst — potrzebna czcionka z polskimi znakami
        raw = bytes(resvg_py.svg_to_bytes(svg_path=str(svg_path), width=px,
                                         font_files=[str(ROOT / "src/fonty/SS4.ttf")],
                                         serif_family="Source Serif 4"))
        img = Image.open(BytesIO(raw))
        # skala szarości + kanał alfa => małe pliki, dobre odwzorowanie czerni
        img = img.convert("LA")
        img.save(png_path, optimize=True)
        self.liczba_png += 1

    # ------------------------------------------------------------- dostęp
    def meta(self, tex, display=False):
        return self.info[(tex, bool(display))]

    def img_tag(self, tex, scale=1.0):
        """Znacznik <img> do wstawienia w akapit (wzór w linii)."""
        m = self.meta(tex, False)
        w = m["w_pt"] * scale
        h = m["h_pt"] * scale
        d = m["d_pt"] * scale
        return f'<img src="{m["png"]}" width="{w:.2f}" height="{h:.2f}" valign="{-d:.2f}"/>'

    def png(self, tex, display=False):
        """Ścieżka do PNG wzoru (dowolny tryb). Używana, gdy SVG zawiera tekst."""
        m = self.meta(tex, display)
        sciezka = Path(m["svg"]).with_suffix(".png")
        if not sciezka.exists():
            self._png(Path(m["svg"]), sciezka, m["w_pt"])
        return str(sciezka)

    def drawing(self, tex, display=True):
        """Obiekt wektorowy (svglib) dla wzoru blokowego."""
        k = (tex, bool(display))
        if k in self._drawings:
            return self._drawings[k]
        if self._svglib is None:
            from svglib.svglib import svg2rlg
            self._svglib = svg2rlg
        m = self.meta(tex, display)
        d = self._svglib(m["svg"])
        self._drawings[k] = d
        return d
