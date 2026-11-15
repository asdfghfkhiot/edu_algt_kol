/**
 * Konwersja wzorów TeX -> SVG (MathJax 3, bez przeglądarki).
 *
 * Wejście:  JSON { "items": [ { "id": "m1", "tex": "\\frac{a}{b}", "display": false }, ... ],
 *                    "em": 42.8, "ex": 18.9 }
 * Wyjście: JSON { "m1": { "svg": "<svg ...", "width_ex": 3.1, "height_ex": 1.2,
 *                         "depth_ex": 0.35, "viewbox": "0 -750 4306 1102" }, ... }
 *
 * em/ex podajemy w pikselach „roboczych” – dzięki temu MathJax zwraca wymiary,
 * które można dokładnie przeliczyć na punkty typograficzne (patrz narzedzia/pdf/math.py).
 */

import fs from "node:fs";
import { mathjax } from "mathjax-full/js/mathjax.js";
import { TeX } from "mathjax-full/js/input/tex.js";
import { SVG } from "mathjax-full/js/output/svg.js";
import { liteAdaptor } from "mathjax-full/js/adaptors/liteAdaptor.js";
import { RegisterHTMLHandler } from "mathjax-full/js/handlers/html.js";
import { AllPackages } from "mathjax-full/js/input/tex/AllPackages.js";

const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const em = input.em || 42.8;
const ex = input.ex || 18.9;

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);

const macros = {
  jj: "\\mathrm{j}",
  R: "\\mathbb{R}",
  C: "\\mathbb{C}",
  N: "\\mathbb{N}",
  Z: "\\mathbb{Z}",
  cis: "\\operatorname{cis}",
};

const tex = new TeX({ packages: AllPackages, macros, formatError: (jax, err) => { throw err; } });
const svg = new SVG({ fontCache: "none" });
const doc = mathjax.document("", { InputJax: tex, OutputJax: svg });

const out = {};
const errors = [];

for (const item of input.items) {
  try {
    const node = doc.convert(item.tex, {
      display: !!item.display,
      em,
      ex,
      containerWidth: 80 * em,
    });
    const html = adaptor.innerHTML(node); // samo <svg>...</svg>
    const svgMatch = html.match(/<svg([^>]*)>/);
    const attrs = svgMatch ? svgMatch[1] : "";
    const num = (name) => {
      const m = attrs.match(new RegExp(`${name}="([-0-9.]+)ex"`));
      return m ? parseFloat(m[1]) : 0;
    };
    // głębokość: style="vertical-align: -1.577ex;"
    const va = attrs.match(/vertical-align:\s*([-0-9.]+)ex/);
    const viewBox = (attrs.match(/viewBox="([^"]+)"/) || [])[1] || "";
    out[item.id] = {
      svg: html,
      width_ex: num("width"),
      height_ex: num("height"),
      depth_ex: va ? -parseFloat(va[1]) : 0,
      viewbox: viewBox,
    };
  } catch (err) {
    errors.push({ id: item.id, tex: item.tex, message: String(err && err.message ? err.message : err) });
  }
}

fs.writeFileSync(process.argv[3], JSON.stringify({ items: out, errors }, null, 0));
if (errors.length) {
  console.error(`BŁĘDY MathJax (${errors.length}):`);
  for (const e of errors.slice(0, 10)) console.error(` - ${e.id}: ${e.message}\n   ${e.tex.slice(0, 120)}`);
  process.exit(1);
}
console.log(`MathJax: ${Object.keys(out).length} wzorów OK`);
