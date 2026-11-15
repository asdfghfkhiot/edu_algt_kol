# Kolokwium 1 — ALGT 2025Z, grupa T2 — zadania 3, 4 i 5

Opracowanie zadań **3, 4 i 5** z kolokwium (plik `ALGT_K1_25Z_T2.pdf`) wraz z rozszerzoną teorią
do poruszanej tematyki.

**Gotowe dokumenty:** [`rozwiazania.pdf`](rozwiazania.pdf) — wersja do druku;
[`rozwiazania.html`](rozwiazania.html) — samodzielna wersja do przeglądarki, działająca offline.

## Co jest w środku

| Część | Zawartość |
|---|---|
| I. Teoria | liczby zespolone (postać trygonometryczna, de Moivre, pierwiastki $n$-tego stopnia, równanie $(z-z_0)^n=w$) · funkcje wymierne i rozkład na ułamki proste nad $\mathbb R$ i $\mathbb C$ · zbiory na płaszczyźnie, sumy i iloczyny rodzin zbiorów |
| II. Rozwiązania | zadanie 3 (pierwiastki, rysunek, sprawdzenia), zadanie 4 (oba rozkłady + kompletność parametrów), zadanie 5 (oba zbiory z rysunkami i analizą konwencji $\mathbb R_+$, $\mathbb N$) |
| III. Ściąga | zestaw wzorów i algorytmów, gotowe odpowiedzi, lista kontrolna przed oddaniem pracy |

## Odpowiedzi w skrócie

- **Zadanie 3.** $(z+2j)^3 = 64j \iff z \in \{\,2\sqrt3,\ -2\sqrt3,\ -6j\,\}$ — wierzchołki trójkąta foremnego
  o środku $-2j$ i promieniu $4$.
- **Zadanie 4.**
  nad $\mathbb R$: $\dfrac{A}{x}+\dfrac{B}{x^2}+\dfrac{C}{x-3}+\dfrac{D}{(x-3)^2}+\dfrac{Ex+F}{x^2+4x+29}$;
  nad $\mathbb C$: dodatkowo $x^2+4x+29=(x+2-5j)(x+2+5j)$, czyli zamiast ostatniego składnika
  $\dfrac{E'}{x+2-5j}+\dfrac{F'}{x+2+5j}$ (z $F'=\overline{E'}$).
- **Zadanie 5.** $\bigcup_{t\in\mathbb R_+}\nabla_t = [-1,1]\times[0,+\infty)$ (domknięty pas);
  $\bigcap_{t\in\mathbb N}\nabla_t = \{0\}\times[0,1]$ (odcinek na osi $Oy$).

## Struktura repozytorium

```
rozwiazania.pdf             <- gotowy dokument do druku
rozwiazania.html            <- samodzielny dokument do przeglądarki
src/rozwiazania.template.html  <- źródło treści (HTML + LaTeX w $...$ / $$...$$)
src/figury/*.svg            <- rysunki (generowane)
narzedzia/figury.py         <- generator rysunków SVG
narzedzia/build.mjs         <- generator HTML (KaTeX)
narzedzia/build_pdf.py      <- generator PDF
narzedzia/pdf/              <- renderowanie wzorów i skład PDF
src/fonty/                  <- fonty i ich licencje
requirements-pdf.txt        <- zależności Pythona do budowy PDF
package.json                <- zależności Node do budowania
```

## Ponowne zbudowanie

```bash
npm install          # zależności Node do budowania
npm run figury       # python3 narzedzia/figury.py  -> src/figury/*.svg
npm run build        # node narzedzia/build.mjs      -> rozwiazania.html
```

## PDF

Gotowy [`rozwiazania.pdf`](rozwiazania.pdf) zawiera te same treści co HTML, spis treści
z numerami stron oraz rysunki. Format to A4; czcionki są osadzone. Większość wzorów
blokowych jest wektorowa, natomiast wzory w tekście są obrazami o wysokiej rozdzielczości
(nie są więc w pełni wyszukiwalne jako tekst).

Aby wygenerować PDF ze wspólnego szablonu, potrzebne są Node.js, npm i Python 3:

```bash
npm install
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-pdf.txt
npm run pdf                         # -> rozwiazania.pdf
python3 narzedzia/build_pdf.py --podglad 1,2,3 --dpi 110
```

Podglądy są zapisywane w `/tmp/edu_algt_pdf/podglad/`, a cache wzorów i rysunków
w `/tmp/edu_algt_pdf/`. Generator używa MathJax, ReportLab, svglib i resvg; wzory
blokowe zawierające tekst niewystępujący w czcionce matematycznej są rasteryzowane.

Wzory w szablonie zapisujemy w jednej linii (`$...$` lub `$$...$$`); skrypt budujący zgłasza błąd,
jeśli któryś wzór nie został przetworzony albo ma błąd składni LaTeX-a. Nierówność
zapisuj jako `\lt` zamiast `<` bezpośrednio przed literą, aby nie przypominała znacznika HTML.

Wszystkie wyniki zostały niezależnie sprawdzone: podstawieniem i wzorami Viète'a (zadanie 3),
rachunkiem symbolicznym (zadanie 4) oraz numerycznym testem przynależności punktów do zbiorów (zadanie 5).
