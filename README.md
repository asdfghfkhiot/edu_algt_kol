# Kolokwium 1 — ALGT 2025Z, grupa T2 — zadania 3, 4 i 5

Opracowanie zadań **3, 4 i 5** z kolokwium (plik `ALGT_K1_25Z_T2.pdf`) wraz z rozszerzoną teorią
do poruszanej tematyki.

**Główny plik: [`rozwiazania.html`](rozwiazania.html)** — samodzielny dokument (wzory wyrenderowane,
czcionki wbudowane, działa offline, można wydrukować przez Ctrl/Cmd + P).

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
rozwiazania.html            <- gotowy dokument (deliverable)
src/rozwiazania.template.html  <- źródło treści (HTML + LaTeX w $...$ / $$...$$)
src/figury/*.svg            <- rysunki (generowane)
narzedzia/figury.py         <- generator rysunków SVG
narzedzia/build.mjs         <- generator dokumentu (KaTeX -> HTML, jeden samodzielny plik)
package.json                <- zależność: katex 0.16.11 (tylko do budowania)
```

## Ponowne zbudowanie

```bash
npm install          # KaTeX (tylko narzędzie budowania)
npm run figury       # python3 narzedzia/figury.py  -> src/figury/*.svg
npm run build        # node narzedzia/build.mjs      -> rozwiazania.html
```

Wzory w szablonie zapisujemy w jednej linii (`$...$` lub `$$...$$`); skrypt budujący zgłasza błąd,
jeśli któryś wzór nie został przetworzony albo ma błąd składni LaTeX-a.

Wszystkie wyniki zostały niezależnie sprawdzone: podstawieniem i wzorami Viète'a (zadanie 3),
rachunkiem symbolicznym (zadanie 4) oraz numerycznym testem przynależności punktów do zbiorów (zadanie 5).
