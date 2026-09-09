#!/usr/bin/env python3
"""Génère le site de révision, les fiches imprimables et les exports flashcards.

Source unique : content/<langue>/course.yaml + content/<langue>/units/*.yaml
Sorties       : site/ (web), print/ (HTML prêt à imprimer), exports/ (CSV Anki)

Aucune dépendance hors PyYAML. Ajouter une langue = ajouter un dossier content/<code>/.
"""
from __future__ import annotations

import csv
import html
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
SITE = ROOT / "site"
PRINT = ROOT / "print"
EXPORTS = ROOT / "exports"
PDF = ROOT / "pdf"

E = lambda s: html.escape(str(s), quote=True)


# --------------------------------------------------------------------------- #
# Chargement
# --------------------------------------------------------------------------- #
def read_yaml(path: Path) -> dict:
    """Lit un fichier de contenu en signalant clairement où est le problème.

    Le contenu est écrit à la main par des non-développeurs : une trace Python
    ne leur dit rien, le nom du fichier et la ligne fautive si.
    """
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"Impossible de lire {rel} : {exc}")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise SystemExit(f"YAML invalide dans {rel} :\n{exc}")
    if data is None:
        raise SystemExit(f"{rel} est vide. Supprimez le fichier ou complétez-le "
                         f"(voir content/_template/).")
    if not isinstance(data, dict):
        raise SystemExit(f"{rel} doit contenir une liste de champs "
                         f"(id, title, vocab...), pas un {type(data).__name__}.")
    return data


def load_language(code_dir: Path) -> dict:
    course = read_yaml(code_dir / "course.yaml")
    for field in ("code", "name_fr", "speech_lang"):
        if field not in course:
            raise SystemExit(f"Champ « {field} » manquant dans "
                             f"{(code_dir / 'course.yaml').relative_to(ROOT)}.")
    units = []
    for f in sorted((code_dir / "units").glob("*.yaml")):
        unit = read_yaml(f)
        if "id" not in unit:
            raise SystemExit(f"Champ « id » manquant dans {f.relative_to(ROOT)}.")
        unit.setdefault("vocab", [])
        unit.setdefault("phrases", [])
        unit.setdefault("notes_fr", [])
        unit.setdefault("activities", [])
        units.append(unit)
    units.sort(key=lambda u: u.get("order", 999))
    course["units"] = units
    return course


def load_all() -> list[dict]:
    langs = []
    for d in sorted(CONTENT.iterdir()):
        if d.name.startswith("_"):
            continue  # gabarits (content/_template)
        if d.is_dir() and (d / "course.yaml").exists():
            langs.append(load_language(d))
    return langs


def entries(unit: dict) -> list[dict]:
    """Vocabulaire + phrases, à plat."""
    return list(unit["vocab"]) + list(unit["phrases"])


def level_label(course: dict, level_id: str) -> str:
    for lv in course.get("levels", []):
        if lv["id"] == level_id:
            return lv["label_fr"]
    return level_id


def md_bold(text: str) -> str:
    """Convertit les **gras** des notes en HTML, le reste est échappé."""
    out, bold = [], False
    for i, part in enumerate(E(text).split("**")):
        if i:
            out.append("</strong>" if bold else "<strong>")
            bold = not bold
        out.append(part)
    if bold:
        out.append("</strong>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# Gabarits
# --------------------------------------------------------------------------- #
def page(title: str, body: str, css: str, extra_head: str = "", script: str = "") -> str:
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
{extra_head}
<style>{css}</style>
</head>
<body>
{body}
{f'<script>{script}</script>' if script else ''}
</body>
</html>
"""


SITE_CSS = """
:root{
  --bg:#fdfaf5; --card:#fff; --ink:#2c2a28; --muted:#6b6560; --line:#e6ded2;
  --accent:#c8452b; --accent2:#2f6f4f; --accent3:#2b5d8c; --radius:14px;
}
:root:not([data-theme=light]){}
@media (prefers-color-scheme:dark){
  :root:not([data-theme=light]){
    --bg:#181614; --card:#232019; --ink:#f2ece3; --muted:#a89f93; --line:#3a3229;
    --accent:#f2795b; --accent2:#6ec191; --accent3:#7bb0e0;
  }
}
:root[data-theme=dark]{
  --bg:#181614; --card:#232019; --ink:#f2ece3; --muted:#a89f93; --line:#3a3229;
  --accent:#f2795b; --accent2:#6ec191; --accent3:#7bb0e0;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:17px/1.6 "Iowan Old Style",Georgia,"Times New Roman",serif;}
.wrap{max-width:900px;margin:0 auto;padding-inline:18px;padding-block:28px 64px}
a{color:var(--accent3)}
h1{font-size:clamp(1.7rem,5vw,2.6rem);margin:.2em 0 .1em;line-height:1.15}
h2{font-size:1.35rem;margin:2em 0 .6em;border-bottom:2px solid var(--line);padding-bottom:.3em}
.sub{color:var(--muted);margin:0 0 1.4em}
.crumb{font-size:.9rem;color:var(--muted);margin-bottom:1.2em}
.goal{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--accent2);
  border-radius:var(--radius);padding:14px 18px;margin:1.4em 0}
.goal ul{margin:.4em 0 0;padding-left:1.2em}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(230px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:14px 16px;text-decoration:none;color:inherit;display:block}
.card:hover{border-color:var(--accent)}
.dl ul{padding-left:1.2em}
.dl li{margin:.35em 0}
.card .n{font-size:.8rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.card .t{font-size:1.25rem;font-weight:600;margin:.15em 0}
.card .f{color:var(--muted);font-size:.95rem}
table{width:100%;border-collapse:collapse;margin:.6em 0}
.tablewrap{overflow-x:auto}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600}
.term{font-weight:700;font-size:1.12rem}
.phon{color:var(--muted);font-style:italic;white-space:nowrap}
.rtl .term{direction:rtl;unicode-bidi:isolate;font-size:1.4rem}
button.say{background:none;border:1px solid var(--line);border-radius:9px;cursor:pointer;
  font-size:1rem;padding:3px 9px;color:inherit;line-height:1.4}
button.say:hover{border-color:var(--accent);color:var(--accent)}
.note{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--accent);
  border-radius:var(--radius);padding:12px 16px;margin:.7em 0}
.act{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:14px 18px;margin:.8em 0}
.act h3{margin:.1em 0 .5em;font-size:1.1rem}
.tag{display:inline-block;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;
  border:1px solid var(--line);border-radius:999px;padding:2px 9px;color:var(--muted);margin-right:6px}
.tag.petits{border-color:var(--accent2);color:var(--accent2)}
.tag.grands{border-color:var(--accent3);color:var(--accent3)}
.flash{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:34px 20px;text-align:center;margin:1em 0;min-height:170px;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;cursor:pointer}
.flash .big{font-size:2rem;font-weight:700}
.flash .ans{font-size:1.3rem;color:var(--accent2)}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:.8em 0}
.btn{background:var(--accent);color:#fff;border:none;border-radius:10px;padding:9px 16px;
  font:inherit;font-size:.95rem;cursor:pointer}
.btn.ghost{background:none;color:var(--ink);border:1px solid var(--line)}
.nav{display:flex;justify-content:space-between;gap:12px;margin-top:2.5em;
  border-top:1px solid var(--line);padding-top:1em;font-size:.95rem}
footer{color:var(--muted);font-size:.85rem;margin-top:3em}
@media (max-width:520px){ .phon{white-space:normal} }
"""

SAY_JS = """
function say(text, lang){
  if(!window.speechSynthesis){ alert("La lecture vocale n'est pas disponible sur ce navigateur."); return; }
  speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance(text);
  u.lang = lang; u.rate = 0.85;
  var v = speechSynthesis.getVoices().find(function(v){ return v.lang && v.lang.replace('_','-') === lang; });
  if(v) u.voice = v;
  speechSynthesis.speak(u);
}
document.addEventListener('click', function(e){
  var b = e.target.closest('button.say');
  if(b) say(b.dataset.text, b.dataset.lang);
});
"""


def say_button(text: str, lang: str) -> str:
    return f'<button class="say" data-text="{E(text)}" data-lang="{E(lang)}" aria-label="Écouter">🔊</button>'


def vocab_table(unit_entries: list[dict], course: dict, with_audio: bool = True) -> str:
    rtl = course.get("direction") == "rtl"
    translit = course.get("has_transliteration")
    rows = []
    for v in unit_entries:
        cells = [f'<td class="term">{E(v["term"])}</td>']
        if translit:
            cells.append(f'<td class="phon">{E(v.get("translit", ""))}</td>')
        cells.append(f'<td class="phon">{E(v.get("phon", ""))}</td>')
        cells.append(f'<td>{E(v.get("fr", ""))}</td>')
        if with_audio:
            cells.append(f'<td>{say_button(v["term"], course["speech_lang"])}</td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')
    heads = ["Mot"] + (["Translittération"] if translit else []) + ["Se prononce", "Français"]
    if with_audio:
        heads.append("")
    th = "".join(f"<th>{h}</th>" for h in heads)
    cls = ' class="rtl"' if rtl else ""
    return f'<div class="tablewrap"><table{cls}><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


# --------------------------------------------------------------------------- #
# Site
# --------------------------------------------------------------------------- #
def build_unit_page(course: dict, unit: dict, prev_u, next_u) -> str:
    lang = course["code"]
    parts = [
        '<div class="wrap">',
        f'<div class="crumb"><a href="index.html">← {E(course["name_fr"])}</a></div>',
        f'<h1>{E(unit["title"])}</h1>',
        f'<p class="sub">{E(unit["title_fr"])} · unité {unit.get("order", "")} · '
        f'{unit.get("duration_min", 15)} min</p>',
    ]
    if unit.get("can_do_fr"):
        items = "".join(f"<li>{E(c)}</li>" for c in unit["can_do_fr"])
        parts.append(f'<div class="goal"><strong>À la fin de cette unité :</strong><ul>{items}</ul></div>')

    if unit["vocab"]:
        parts.append("<h2>Le vocabulaire</h2>")
        parts.append(vocab_table(unit["vocab"], course))
    if unit["phrases"]:
        parts.append("<h2>Les phrases</h2>")
        parts.append(vocab_table(unit["phrases"], course))

    for n in unit["notes_fr"]:
        parts.append(f'<div class="note">{md_bold(n)}</div>')

    if unit["activities"]:
        parts.append("<h2>Les activités</h2>")
        for a in unit["activities"]:
            lv = a.get("level", "")
            steps = "".join(f"<li>{md_bold(s)}</li>" for s in a.get("steps_fr", []))
            parts.append(
                f'<div class="act"><span class="tag {E(lv)}">{E(level_label(course, lv))}</span>'
                f'<span class="tag">{E(a.get("type", ""))}</span>'
                f'<h3>{E(a.get("title_fr", ""))}</h3><ol>{steps}</ol></div>'
            )

    # Une unité en cours d'écriture peut n'avoir aucun mot : pas de flashcards à
    # proposer, et surtout pas de bloc interactif vide qui tournerait à vide.
    cards = [{"t": v["term"], "f": v.get("fr", "")} for v in entries(unit)]
    if cards:
        parts.append("<h2>Les flashcards</h2>")
        parts.append('<div class="flash" id="flash"><div class="big" id="fq">Clique pour commencer</div>'
                     '<div class="ans" id="fa"></div></div>'
                     '<div class="row"><button class="btn" id="fnext">Carte suivante</button>'
                     '<button class="btn ghost" id="fflip">Sens inverse</button>'
                     '<span class="phon" id="fcount"></span></div>')

    nav = []
    if prev_u:
        nav.append(f'<a href="{E(prev_u["id"])}.html">← {E(prev_u["title"])}</a>')
    else:
        nav.append("<span></span>")
    if next_u:
        nav.append(f'<a href="{E(next_u["id"])}.html">{E(next_u["title"])} →</a>')
    else:
        nav.append("<span></span>")
    parts.append(f'<div class="nav">{"".join(nav)}</div>')
    parts.append("</div>")

    import json

    if not cards:
        return page(f'{unit["title"]} — {course["name_fr"]}', "\n".join(parts), SITE_CSS,
                    script=SAY_JS)

    script = SAY_JS + f"""
var CARDS = {json.dumps(cards, ensure_ascii=False)};
var LANG = {json.dumps(course["speech_lang"])};
var order = [], i = -1, reversed = false, revealed = false;
function shuffle(){{ order = CARDS.map(function(_,k){{return k}}); 
  for(var k=order.length-1;k>0;k--){{var j=Math.floor(Math.random()*(k+1));var t=order[k];order[k]=order[j];order[j]=t;}} }}
function draw(){{
  if(i >= order.length-1){{ shuffle(); i = -1; }}
  i++; revealed = false;
  var c = CARDS[order[i]];
  document.getElementById('fq').textContent = reversed ? c.f : c.t;
  document.getElementById('fa').textContent = '';
  document.getElementById('fcount').textContent = (i+1) + ' / ' + order.length;
  if(!reversed) say(c.t, LANG);
}}
function reveal(){{
  if(i < 0){{ draw(); return; }}
  var c = CARDS[order[i]];
  if(!revealed){{ document.getElementById('fa').textContent = reversed ? c.t : c.f; revealed = true;
    if(reversed) say(c.t, LANG); }}
  else draw();
}}
document.getElementById('flash').addEventListener('click', reveal);
document.getElementById('fnext').addEventListener('click', function(e){{ e.stopPropagation(); draw(); }});
document.getElementById('fflip').addEventListener('click', function(e){{
  e.stopPropagation(); reversed = !reversed; i = -1; order = []; draw(); }});
shuffle();
"""
    return page(f'{unit["title"]} — {course["name_fr"]}', "\n".join(parts), SITE_CSS, script=script)


def build_lang_index(course: dict) -> str:
    cards = []
    for u in course["units"]:
        cards.append(
            f'<a class="card" href="{E(u["id"])}.html">'
            f'<div class="n">Unité {E(u.get("order",""))}</div>'
            f'<div class="t">{E(u["title"])}</div>'
            f'<div class="f">{E(u["title_fr"])} — {E(u.get("goal_fr",""))}</div></a>'
        )
    levels = "".join(
        f'<li><strong>{E(lv["label_fr"])}</strong> — {E(lv["desc_fr"])}</li>'
        for lv in course.get("levels", [])
    )
    n_vocab = sum(len(entries(u)) for u in course["units"])
    code = course["code"]
    has_pdf = (PDF / code / "cahier-complet.pdf").exists()

    dl = ['<p>Chaque unité donne trois feuilles A4 : la fiche de cours, les activités '
          'et les cartes de vocabulaire à découper.</p><ul>']
    cahier = f'<a href="../print/{E(code)}/cahier-complet.html">Le cahier complet (HTML, Ctrl+P pour imprimer)</a>'
    if has_pdf:
        cahier += f' · <a href="../pdf/{E(code)}/cahier-complet.pdf">PDF</a>'
    dl.append(f"<li><strong>{cahier}</strong></li>")
    for u in course["units"]:
        line = (f'Unité {E(u.get("order",""))} — {E(u["title"])} : '
                f'<a href="../print/{E(code)}/{E(u["id"])}.html">HTML</a>')
        if has_pdf:
            line += f' · <a href="../pdf/{E(code)}/{E(u["id"])}.pdf">PDF</a>'
        dl.append(f"<li>{line}</li>")
    dl.append(f'<li>Flashcards pour Anki : '
              f'<a href="../exports/anki-{E(code)}.csv" download>anki-{E(code)}.csv</a> '
              f'(séparateur « ; », colonnes Recto / Verso / Tags)</li>')
    dl.append("</ul>")
    downloads = "".join(dl)

    body = f"""<div class="wrap">
<div class="crumb"><a href="../index.html">← Toutes les langues</a></div>
<h1>{E(course["name_fr"])}</h1>
<p class="sub">{E(course.get("variant_fr",""))} · {len(course["units"])} unités · {n_vocab} mots et phrases</p>
<div class="goal"><strong>Deux niveaux dans chaque unité :</strong><ul>{levels}</ul></div>
<h2>Les unités</h2>
<div class="grid">{"".join(cards)}</div>
<h2>À imprimer et à emporter</h2>
<div class="dl">{downloads}</div>
<footer><p>{E(course.get("note_fr",""))}</p></footer>
</div>"""
    return page(course["name_fr"], body, SITE_CSS)


def build_home(langs: list[dict]) -> str:
    cards = []
    for c in langs:
        cards.append(
            f'<a class="card" href="{E(c["code"])}/index.html">'
            f'<div class="n">{E(c.get("variant_fr", ""))}</div>'
            f'<div class="t">{E(c["name"])}</div>'
            f'<div class="f">{E(c["name_fr"])} — {len(c["units"])} unités</div></a>'
        )
    body = f"""<div class="wrap">
<h1>Les langues à la maison</h1>
<p class="sub">Cours, fiches et flashcards pour apprendre en famille.</p>
<div class="grid">{"".join(cards)}</div>
<footer>Site généré depuis <code>content/</code> par <code>scripts/build.py</code>.</footer>
</div>"""
    return page("Les langues à la maison", body, SITE_CSS)


# --------------------------------------------------------------------------- #
# Fiches imprimables
# --------------------------------------------------------------------------- #
PRINT_CSS = """
@page{size:A4;margin:15mm}
body{font:12pt/1.5 Georgia,"Times New Roman",serif;color:#111;background:#fff;margin:0}
.sheet{padding:0 0 10mm}
.sheet + .sheet{page-break-before:always}
h1{font-size:22pt;margin:0 0 2mm}
.sub{color:#555;margin:0 0 5mm;font-size:11pt}
h2{font-size:13pt;margin:6mm 0 2mm;border-bottom:1.5pt solid #111;padding-bottom:1mm}
table{width:100%;border-collapse:collapse}
th,td{border-bottom:.5pt solid #bbb;padding:2.4mm 2mm;text-align:left;vertical-align:top}
th{font-size:8.5pt;text-transform:uppercase;letter-spacing:.05em;color:#555}
.term{font-weight:700;font-size:12.5pt}
.phon{font-style:italic;color:#555}
.rtl .term{direction:rtl;unicode-bidi:isolate;font-size:16pt}
.note{border:.5pt solid #999;border-left:2.5pt solid #111;padding:2.5mm 3mm;margin:3mm 0;font-size:10.5pt}
.act{border:.5pt solid #999;border-radius:2mm;padding:3mm 4mm;margin:3mm 0}
.act h3{margin:0 0 1.5mm;font-size:11.5pt}
.tag{font-size:8pt;text-transform:uppercase;letter-spacing:.05em;border:.5pt solid #666;
  border-radius:10pt;padding:.4mm 2mm;margin-right:2mm;color:#444}
ol,ul{margin:1mm 0;padding-left:5mm}
.write{border-bottom:.5pt solid #999;display:inline-block;min-width:35mm}
.cutgrid{display:grid;grid-template-columns:1fr 1fr;gap:0}
.cut{border:.4pt dashed #888;height:38mm;display:flex;flex-direction:column;
  align-items:center;justify-content:center;text-align:center;padding:3mm}
.cut .t{font-size:15pt;font-weight:700}
.cut .p{font-size:9.5pt;font-style:italic;color:#555;margin-top:1.5mm}
.cut .f{font-size:11pt;color:#333;margin-top:1.5mm}
footer{margin-top:6mm;font-size:8.5pt;color:#666;border-top:.5pt solid #bbb;padding-top:2mm}
@media screen{ body{background:#eee} .sheet{background:#fff;max-width:210mm;margin:6mm auto;
  padding:15mm;box-shadow:0 1px 6px rgba(0,0,0,.2)} }
"""


def build_print_unit(course: dict, unit: dict) -> str:
    sheets = []

    # Feuille 1 : la fiche de cours
    p = [f'<div class="sheet"><h1>{E(unit["title"])}</h1>',
         f'<p class="sub">{E(course["name_fr"])} · unité {unit.get("order","")} — {E(unit["title_fr"])}</p>']
    if unit.get("can_do_fr"):
        p.append('<div class="note"><strong>Objectif :</strong><ul>'
                 + "".join(f"<li>{E(c)}</li>" for c in unit["can_do_fr"]) + "</ul></div>")
    if unit["vocab"]:
        p.append("<h2>Vocabulaire</h2>" + vocab_table(unit["vocab"], course, with_audio=False))
    if unit["phrases"]:
        p.append("<h2>Phrases</h2>" + vocab_table(unit["phrases"], course, with_audio=False))
    for n in unit["notes_fr"]:
        p.append(f'<div class="note">{md_bold(n)}</div>')
    p.append(f'<footer>{E(course["name_fr"])} — {E(unit["title"])} — fiche de cours</footer></div>')
    sheets.append("".join(p))

    # Feuille 2 : les activités
    if unit["activities"]:
        a_parts = [f'<div class="sheet"><h1>{E(unit["title"])} — activités</h1>']
        for a in unit["activities"]:
            steps = "".join(f"<li>{md_bold(s)}</li>" for s in a.get("steps_fr", []))
            a_parts.append(
                f'<div class="act"><span class="tag">{E(level_label(course, a.get("level","")))}</span>'
                f'<span class="tag">{E(a.get("type",""))}</span>'
                f'<h3>{E(a.get("title_fr",""))}</h3><ol>{steps}</ol></div>'
            )
        a_parts.append(f'<footer>{E(course["name_fr"])} — {E(unit["title"])} — activités</footer></div>')
        sheets.append("".join(a_parts))

    # Feuille 3 : les cartes à découper
    cells = []
    for v in entries(unit):
        cells.append(
            f'<div class="cut"><div class="t">{E(v["term"])}</div>'
            f'<div class="p">{E(v.get("phon",""))}</div>'
            f'<div class="f">{E(v.get("fr",""))}</div></div>'
        )
    if cells:
        sheets.append(
            f'<div class="sheet"><h1>{E(unit["title"])} — cartes à découper</h1>'
            f'<p class="sub">Découper le long des pointillés. Plier ou masquer le français pour réviser.</p>'
            f'<div class="cutgrid">{"".join(cells)}</div>'
            f'<footer>{E(course["name_fr"])} — {E(unit["title"])} — cartes</footer></div>'
        )
    return page(f'{unit["title"]} — à imprimer', "\n".join(sheets), PRINT_CSS)


def build_print_all(course: dict) -> str:
    body = []
    for u in course["units"]:
        inner = build_print_unit(course, u)
        body.append(inner.split("<body>\n", 1)[1].rsplit("\n", 3)[0])
    return page(f'{course["name_fr"]} — cahier complet', "\n".join(body), PRINT_CSS)


# --------------------------------------------------------------------------- #
# Exports flashcards
# --------------------------------------------------------------------------- #
def build_exports(course: dict) -> None:
    EXPORTS.mkdir(parents=True, exist_ok=True)
    anki = EXPORTS / f'anki-{course["code"]}.csv'
    with anki.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["Recto", "Verso", "Tags"])
        for u in course["units"]:
            tag = f'{course["code"]}::{u["id"]}'
            for v in entries(u):
                recto = v["term"]
                verso = v.get("fr", "")
                extra = " / ".join(x for x in (v.get("translit"), v.get("phon")) if x)
                if extra:
                    verso = f"{verso}<br><i>{extra}</i>"
                w.writerow([recto, verso, tag])
    print(f"  exports/{anki.name}")


# --------------------------------------------------------------------------- #
def main() -> None:
    langs = load_all()
    if not langs:
        raise SystemExit("Aucune langue trouvée dans content/")

    for d in (SITE, PRINT):
        if d.exists():
            shutil.rmtree(d)

    SITE.mkdir(parents=True)
    (SITE / "index.html").write_text(build_home(langs), encoding="utf-8")
    print("site/index.html")

    for course in langs:
        code = course["code"]
        sdir = SITE / code
        pdir = PRINT / code
        sdir.mkdir(parents=True)
        pdir.mkdir(parents=True)

        (sdir / "index.html").write_text(build_lang_index(course), encoding="utf-8")
        units = course["units"]
        for i, u in enumerate(units):
            prev_u = units[i - 1] if i else None
            next_u = units[i + 1] if i + 1 < len(units) else None
            (sdir / f'{u["id"]}.html').write_text(
                build_unit_page(course, u, prev_u, next_u), encoding="utf-8")
            (pdir / f'{u["id"]}.html').write_text(build_print_unit(course, u), encoding="utf-8")
        (pdir / "cahier-complet.html").write_text(build_print_all(course), encoding="utf-8")

        print(f'{course["name_fr"]} : {len(units)} unités → site/{code}/ et print/{code}/')
        build_exports(course)

    # Le site publié embarque les fiches, les PDF (s'ils ont été produits) et les exports,
    # pour qu'un seul dossier suffise à tout distribuer.
    shutil.copytree(PRINT, SITE / "print")
    shutil.copytree(EXPORTS, SITE / "exports")
    if PDF.exists():
        shutil.copytree(PDF, SITE / "pdf")
        print("pdf/ inclus dans le site")

    print("\nOK. Ouvrir site/index.html — imprimer depuis print/<langue>/cahier-complet.html")


if __name__ == "__main__":
    main()
