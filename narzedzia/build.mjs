#!/usr/bin/env node
/**
 * Generator dokumentu: src/rozwiazania.template.html -> rozwiazania.html
 *
 * Co robi:
 *  1. wstawia w miejsca {{include:sciezka}} zawartosc plikow (np. rysunki SVG),
 *  2. renderuje wzory LaTeX ($...$ oraz $$...$$) do HTML za pomoca KaTeX (po stronie Node,
 *     wiec w przegladarce nie jest potrzebny zaden JavaScript ani internet),
 *  3. wkleja arkusz stylow KaTeX z czcionkami zakodowanymi w base64,
 *     dzieki czemu wynik to JEDEN samodzielny plik HTML.
 *
 * Uzycie:  npm run figury && npm run build   (albo: node narzedzia/build.mjs)
 */

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";
import katex from "katex";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const TEMPLATE = resolve(ROOT, "src/rozwiazania.template.html");
const OUTPUT = resolve(ROOT, "rozwiazania.html");

let stats = { display: 0, inline: 0, includes: 0 };

/* ------------------------------------------------------------------ */
/* 1. Dolaczanie plikow ({{include:...}})                              */
/* ------------------------------------------------------------------ */
function resolveIncludes(src) {
  const re = /\{\{include:([^}]+)\}\}/g;
  return src.replace(re, (_m, rel) => {
    stats.includes += 1;
    return readFileSync(resolve(ROOT, rel.trim()), "utf8").trim();
  });
}

/* ------------------------------------------------------------------ */
/* 2. Renderowanie wzorow                                              */
/* ------------------------------------------------------------------ */
const KATEX_OPTS = {
  throwOnError: true,
  strict: "ignore",
  trust: false,
  macros: {
    "\\jj": "\\mathrm{j}",
    "\\R": "\\mathbb{R}",
    "\\C": "\\mathbb{C}",
    "\\N": "\\mathbb{N}",
    "\\Z": "\\mathbb{Z}",
    "\\cis": "\\operatorname{cis}",
    "\\Arg": "\\operatorname{Arg}",
    "\\arg": "\\operatorname{arg}",
    "\\Re": "\\operatorname{Re}",
    "\\Im": "\\operatorname{Im}",
  },
};

function renderMath(src) {
  // $$ ... $$  (wzory blokowe)
  src = src.replace(/\$\$([\s\S]+?)\$\$/g, (_m, tex) => {
    stats.display += 1;
    try {
      return katex.renderToString(tex.trim(), { ...KATEX_OPTS, displayMode: true });
    } catch (err) {
      throw new Error(`Blad KaTeX w trybie blokowym:\n${tex.trim()}\n\n${err.message}`);
    }
  });
  // $ ... $  (wzory w linii) - nie lapie resztek $$
  src = src.replace(/(^|[^\\$])\$([^$\n]+?)\$(?!\$)/g, (_m, pre, tex) => {
    stats.inline += 1;
    try {
      const html = katex.renderToString(tex.trim(), { ...KATEX_OPTS, displayMode: false });
      return pre + html;
    } catch (err) {
      throw new Error(`Blad KaTeX w trybie liniowym:\n${tex.trim()}\n\n${err.message}`);
    }
  });
  return src;
}

/* ------------------------------------------------------------------ */
/* 3. Arkusz KaTeX z czcionkami w base64                              */
/* ------------------------------------------------------------------ */
function katexCss() {
  const cssPath = resolve(ROOT, "node_modules/katex/dist/katex.min.css");
  let css = readFileSync(cssPath, "utf8");

  // zostaw tylko format woff2 (najmniejszy, wystarczajacy dla wspolczesnych przegladarek)
  css = css.replace(
    /,url\(fonts\/[^)]*\.woff\) format\("woff"\),url\(fonts\/[^)]*\.ttf\) format\("truetype"\)/g,
    "",
  );

  css = css.replace(/url\(fonts\/([^)]+\.woff2)\)/g, (_m, name) => {
    const b64 = readFileSync(resolve(ROOT, "node_modules/katex/dist/fonts", name)).toString("base64");
    return `url(data:font/woff2;base64,${b64})`;
  });

  if (/url\(fonts\//.test(css)) throw new Error("Nie udalo sie wkleic wszystkich czcionek KaTeX.");
  return css;
}

/* ------------------------------------------------------------------ */
/* 4. Budowa                                                          */
/* ------------------------------------------------------------------ */
const template = readFileSync(TEMPLATE, "utf8");
let html = resolveIncludes(template);
html = renderMath(html);
html = html.replace("/*{{KATEX_CSS}}*/", () => katexCss());

// kontrola: zaden wzor nie moze zostac nieprzetworzony (np. $...$ rozciagniety na dwie linie)
const stray = html.indexOf("$", html.indexOf("<body>"));
if (stray !== -1) {
  const ctx = html.slice(stray - 70, stray + 70).replace(/\s+/g, " ");
  throw new Error(`Nieprzetworzony znak $ w tresci (wzory musza byc w jednej linii): ...${ctx}...`);
}

writeFileSync(OUTPUT, html, "utf8");

const kb = (Buffer.byteLength(html, "utf8") / 1024).toFixed(0);
console.log(
  `OK -> ${relative(ROOT, OUTPUT)}  (${kb} kB, wzory: ${stats.display} blokowych + ${stats.inline} w linii, ` +
    `dolaczone pliki: ${stats.includes})`,
);
