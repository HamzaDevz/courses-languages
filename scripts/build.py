#!/usr/bin/env python3
"""Génère le site de révision, les fiches imprimables et les exports flashcards.

Source unique : content/<langue>/course.yaml + program.yaml + units/*.yaml
Sorties       : site/ (web), print/ (HTML prêt à imprimer), exports/ (CSV Anki)

Aucune dépendance hors PyYAML. Ajouter une langue = ajouter un dossier content/<code>/.
"""
from __future__ import annotations

import csv
import html
import re
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
SITE = ROOT / "site"
PRINT = ROOT / "print"
EXPORTS = ROOT / "exports"
PDF = ROOT / "pdf"
AUDIO = ROOT / "assets" / "audio"

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
        # Tout ce qui sert à tenir une conversation. Une unité peut en manquer
        # (elle reste valide), la section correspondante n'est alors pas rendue.
        unit.setdefault("dialogue", None)
        unit.setdefault("comprehension", [])
        unit.setdefault("qa", [])
        unit.setdefault("reemploi_fr", [])
        unit.setdefault("culture_fr", "")
        unit.setdefault("year", 1)
        units.append(unit)
    units.sort(key=lambda u: (u.get("year", 1), u.get("order", 999)))
    course["units"] = units
    course["program"] = load_program(code_dir, units)
    course["audio_index"] = load_audio_index(course["code"])
    course["culture"] = load_side_file(code_dir, "culture", "escales")
    course["resources"] = load_side_file(code_dir, "resources", "groups")
    course["toolkit"] = course.get("toolkit", [])
    return course


def load_audio_index(code: str) -> dict:
    """Le manifeste des enregistrements réels produits par scripts/audio.py.

    Absent = pas d'enregistrement : le site retombe sur la voix de synthèse du
    navigateur, mais uniquement si elle parle vraiment la langue (voir SAY_JS).
    """
    path = AUDIO / code / "index.json"
    if not path.exists():
        return {}
    import json
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("clips", {})
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Manifeste audio illisible ({path.relative_to(ROOT)}) : {exc}\n"
                         f"Supprimez le dossier assets/audio/{code}/ et relancez « make audio ».")


def audio_src(course: dict, text: str, voice: str = "f", depth: int = 1) -> str:
    """Chemin relatif du fichier son d'une phrase, ou "" s'il n'a pas été produit."""
    clip = (course.get("audio_index") or {}).get(text)
    if not clip:
        return ""
    name = clip.get(voice) or clip.get("f") or clip.get("m")
    if not name:
        return ""
    return f'{"../" * depth}audio/{course["code"]}/{name}'


def load_program(code_dir: Path, units: list[dict]) -> dict | None:
    """Le programme de l'année : périodes, semaines, unités, bilans.

    Sans program.yaml la langue reste utilisable — on perd seulement le plan
    annuel, pas les unités.
    """
    path = code_dir / "program.yaml"
    if not path.exists():
        return None
    prog = read_yaml(path)
    known = {u["id"] for u in units}
    for track in program_tracks(prog):
        for year in track.get("years", []):
            for period in year.get("periods", []):
                for uid in period.get("units", []):
                    if uid not in known:
                        raise SystemExit(
                            f"{path.relative_to(ROOT)} : « {track.get('label_fr', '')} », "
                            f"période « {period.get('label_fr','')} » cite l'unité "
                            f"« {uid} », qui n'existe pas dans "
                            f"{(code_dir / 'units').relative_to(ROOT)}/.")
    return prog


def program_tracks(prog: dict) -> list[dict]:
    """Les parcours du programme.

    Un parcours = un âge, avec son rythme, ses objectifs et son niveau visé.
    Un programme écrit à l'ancienne (une seule liste `years`) reste valide :
    il devient un parcours unique.
    """
    tracks = prog.get("tracks")
    if tracks:
        return tracks
    if prog.get("years"):
        return [{"id": "unique", "label_fr": "Le programme", "years": prog["years"]}]
    return []


def spine_track(prog: dict) -> dict:
    """Le parcours qui sert de référence pour numéroter les unités.

    Les deux parcours parcourent les mêmes unités à des vitesses différentes :
    il en faut un pour donner les titres d'années affichés sur la liste des
    unités, sinon l'enfant de 4 ans et celui de 9 ans ne lisent pas la même
    chose au même endroit.
    """
    tracks = program_tracks(prog)
    for t in tracks:
        if t.get("spine"):
            return t
    return tracks[0] if tracks else {}


def load_side_file(code_dir: Path, name: str, key: str) -> dict:
    """Un fichier de contenu facultatif (culture.yaml, resources.yaml).

    Un fichier présent mais sans contenu utile est traité comme absent : sinon
    le site afficherait une carte qui mène à une page blanche.
    """
    path = code_dir / f"{name}.yaml"
    if not path.exists():
        return {}
    data = read_yaml(path)
    return data if data.get(key) else {}


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


def qa_pairs(unit: dict) -> list[tuple[dict, dict]]:
    """Les couples (question, première réponse) de l'unité.

    C'est le matériau de la conversation : savoir un mot ne sert à rien si
    l'enfant ne sait pas quoi répondre quand on le lui demande.
    """
    out = []
    for item in unit.get("qa") or []:
        q = item.get("question")
        answers = item.get("answers") or []
        if q and answers:
            out.append((q, answers[0]))
    return out


def dialogue_lines(unit: dict) -> list[dict]:
    d = unit.get("dialogue") or {}
    return list(d.get("lines") or [])


def units_by_year(course: dict) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}
    for u in course["units"]:
        grouped.setdefault(u.get("year", 1), []).append(u)
    return grouped


def year_label(course: dict, year: int) -> str:
    for y in (spine_track(course.get("program") or {}).get("years") or []):
        if y.get("year") == year:
            return y.get("label_fr", f"Année {year}")
    return f"Année {year}"


def year_entry(course: dict, year: int) -> dict:
    for y in (spine_track(course.get("program") or {}).get("years") or []):
        if y.get("year") == year:
            return y
    return {}


def level_label(course: dict, level_id: str) -> str:
    for lv in course.get("levels", []):
        if lv["id"] == level_id:
            return lv["label_fr"]
    return level_id


def shorten(text: str, limit: int) -> str:
    """Coupe un texte proprement, avant échappement HTML.

    Tronquer après échappement couperait une entité en deux (« l&#x » au lieu
    de « l' ») et abîmerait la page.
    """
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.S)
ITALIC_RE = re.compile(r"\*(.+?)\*", re.S)


def md_bold(text: str) -> str:
    """Convertit les **gras** et les *italiques* des notes ; le reste est échappé.

    Le contenu est écrit en markdown léger par des non-développeurs, et les mots
    de la langue enseignée sont notés *entre étoiles* dans tout le cours : les
    afficher avec leurs astérisques serait une faute d'impression à chaque page.
    Le gras est traité en premier, ce qui permet à un italique d'en contenir.
    Une étoile isolée (« 3 * 4 ») reste telle quelle.
    """
    out = BOLD_RE.sub(r"<strong>\1</strong>", E(text))
    return ITALIC_RE.sub(r"<em>\1</em>", out)


def plain(text: str) -> str:
    """Le même texte sans ses marques de markdown, pour les endroits sans HTML."""
    return ITALIC_RE.sub(r"\1", BOLD_RE.sub(r"\1", str(text)))


# --------------------------------------------------------------------------- #
# Gabarits
# --------------------------------------------------------------------------- #
def page(title: str, body: str, css: str, extra_head: str = "", script: str = "") -> str:
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='88'%3E%F0%9F%97%A3%3C/text%3E%3C/svg%3E">
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
/* Dialogue : la réplique doit se lire d'un coup d'œil, langue d'abord. */
.dial{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:8px 16px 14px;margin:.8em 0}
.dline{display:flex;gap:10px;padding:9px 0;border-bottom:1px solid var(--line);align-items:baseline}
.dline:last-child{border-bottom:none}
.who{flex:0 0 auto;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;
  color:#fff;background:var(--accent3);border-radius:999px;padding:3px 9px;min-width:74px;text-align:center}
.dline[data-role="1"] .who{background:var(--accent2)}
.dtext{flex:1 1 auto;min-width:0}
.dtext .term{display:inline;margin-right:6px}
.dfr{display:block;color:var(--muted);font-size:.95rem}
.dline.hidden-fr .dfr{visibility:hidden}
.dline.masked .term,.dline.masked .phon{filter:blur(6px);cursor:pointer;user-select:none}
.dline.masked .say{opacity:.35}
.ctx{color:var(--muted);font-style:italic;margin:.2em 0 .8em}
/* Questions / réponses : ce qu'on me demande, ce que je peux répondre. */
.qa{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--accent3);
  border-radius:var(--radius);padding:12px 16px;margin:.7em 0}
.qa .q{font-weight:700;font-size:1.1rem}
.qa .qfr{color:var(--muted);font-size:.95rem;margin-bottom:.5em}
.qa ul{list-style:none;margin:.2em 0 0;padding:0}
.qa li{padding:5px 0 5px 18px;border-left:2px solid var(--line);margin-left:2px}
.qa li .a{font-weight:600}
.qa li .afr{color:var(--muted);font-size:.92rem;display:block}
details.comp{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:10px 16px;margin:.5em 0}
details.comp summary{cursor:pointer;font-weight:600}
details.comp p{margin:.5em 0 0;color:var(--accent2)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:.8em 0}
.chip{border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:.9rem;
  color:var(--muted);background:var(--card)}
.plan table{background:var(--card)}
.plan td .u{display:block}
.week{white-space:nowrap;color:var(--muted);font-size:.9rem}
.yearhead{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--accent);
  border-radius:var(--radius);padding:14px 18px;margin:1.6em 0 1em}
.yearhead h2{margin-top:0;border:none;padding:0}
.yearhead h3{margin:0 0 .3em;font-size:1.15rem}
.escale{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:14px 18px;margin:1em 0}
.escale .n{font-size:.78rem;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}
.escale h3{margin:.15em 0 .5em;font-size:1.3rem}
ul.esc{list-style:none;padding-left:0;margin:.4em 0}
ul.esc li{padding:5px 0 5px 14px;border-left:2px solid var(--line);margin:.2em 0}
.mission{border:1px dashed var(--accent);border-radius:var(--radius);
  padding:10px 14px;margin:.8em 0 .2em}
h3{font-size:1.15rem;margin:1.4em 0 .4em}
@media (max-width:520px){ .phon{white-space:normal} .dline{flex-direction:column;gap:2px} }
"""

SAY_JS = """
/* Le son, dans cet ordre :
     1. l'enregistrement réel produit par scripts/audio.py (vraie voix de la
        langue enseignée) ;
     2. à défaut la synthèse du navigateur, mais UNIQUEMENT si l'appareil a une
        voix de cette langue. Faire lire du portugais par une voix française
        donne une prononciation fausse : on préfère ne rien jouer et le dire. */
var SLOW_KEY = 'audio-lent';
function isSlow(){ try{ return localStorage.getItem(SLOW_KEY) === '1'; }catch(e){ return false; } }
function setSlow(v){ try{ localStorage.setItem(SLOW_KEY, v ? '1' : '0'); }catch(e){} }

function normLang(l){ return String(l || '').replace('_','-').toLowerCase(); }
function rootLang(l){ return normLang(l).split('-')[0]; }

var voiceCache = null;   /* null = pas encore su, false = aucune voix utilisable */
function scoreVoice(v, want){
  var n = (v.name || '').toLowerCase(), s = 0;
  if(normLang(v.lang) === want) s += 10;                       /* bonne variante */
  if(/(neural|premium|enhanced|natural|siri)/.test(n)) s += 5; /* voix soignée */
  if(/(joana|catarina|duarte|raquel|fernanda|ines|helia|google)/.test(n)) s += 4;
  if(/compact/.test(n)) s -= 6;                                /* voix robotique */
  return s;
}
function pickVoice(){
  if(voiceCache !== null) return voiceCache;
  if(!window.speechSynthesis) return (voiceCache = false);
  var vs = speechSynthesis.getVoices() || [];
  if(!vs.length) return null;            /* chargement asynchrone : on retentera */
  var want = normLang(VOICE_LANG), root = rootLang(VOICE_LANG);
  var pool = vs.filter(function(v){ return rootLang(v.lang) === root; });
  if(!pool.length) return (voiceCache = false);
  pool.sort(function(a, b){ return scoreVoice(b, want) - scoreVoice(a, want); });
  voiceCache = pool[0];
  return voiceCache;
}
function hasRecordings(){
  for(var k in AUDIO_MAP){ if(AUDIO_MAP[k]) return true; }
  return false;
}
var voiceTries = 0;
function voiceNotice(){
  var el = document.getElementById('voicewarn');
  if(!el) return;
  if(hasRecordings()){
    el.textContent = '';
    return;
  }
  var v = pickVoice();
  if(v === null){
    /* les voix arrivent de façon asynchrone ; au bout de ~2,5 s sans rien,
       c'est qu'il n'y a aucun moteur de synthèse sur l'appareil */
    if(voiceTries++ < 8){ setTimeout(voiceNotice, 300); return; }
    v = false;
  }
  if(v === false){
    el.innerHTML = 'Aucune voix en ' + LANG_NAME.toLowerCase() + ' installée sur cet appareil : ' +
      'la lecture est coupée pour ne pas apprendre une mauvaise prononciation. ' +
      '<a href="../voix.html">Comment en installer une</a>.';
  } else if(normLang(v.lang) !== normLang(VOICE_LANG)){
    el.innerHTML = 'Voix « ' + v.name + ' » (' + v.lang + ') : ce n\\'est pas la variante ' +
      'enseignée, l\\'accent sera différent. <a href="../voix.html">Installer la bonne voix</a>.';
  } else {
    el.textContent = 'Voix du système : « ' + v.name + ' ».';
  }
}
if(window.speechSynthesis && speechSynthesis.addEventListener){
  speechSynthesis.addEventListener('voiceschanged', function(){ voiceCache = null; voiceNotice(); });
}

var currentAudio = null;
function stopAll(){
  if(currentAudio){ currentAudio.pause(); currentAudio = null; }
  if(window.speechSynthesis) speechSynthesis.cancel();
}
function ttsSpeak(text, done, retried){
  var v = pickVoice();
  if(v === null && !retried){ setTimeout(function(){ ttsSpeak(text, done, true); }, 250); return; }
  if(!v){ voiceNotice(); if(done) done(); return; }
  var u = new SpeechSynthesisUtterance(text);
  u.voice = v; u.lang = v.lang; u.rate = isSlow() ? 0.6 : 0.9;
  if(done){ u.onend = done; u.onerror = done; }
  speechSynthesis.speak(u);
}
function playItem(item, done){
  if(item.src){
    var a = new Audio(item.src);
    a.playbackRate = isSlow() ? 0.7 : 1;
    a.onended = done || null;
    /* fichier manquant ou lecture refusée : on retombe sur la synthèse */
    a.onerror = function(){ ttsSpeak(item.text, done); };
    currentAudio = a;
    var pr = a.play();
    if(pr && pr.catch) pr.catch(function(){ ttsSpeak(item.text, done); });
    return;
  }
  ttsSpeak(item.text, done);
}
function playSeq(items){
  stopAll();
  var i = 0;
  (function next(){
    if(i >= items.length) return;
    var it = items[i++];
    playItem(it, function(){ setTimeout(next, 350); });
  })();
}
function say(text, lang, src){
  playSeq([{ text: text, src: src || AUDIO_MAP[text] || '' }]);
}
document.addEventListener('click', function(e){
  var b = e.target.closest('button.say');
  if(b) say(b.dataset.text, b.dataset.lang, b.dataset.src);
});
document.addEventListener('DOMContentLoaded', function(){
  voiceNotice();
  var sl = document.querySelector('button[data-act=slow]');
  if(sl && isSlow()){ sl.setAttribute('aria-pressed','true'); sl.textContent = '🐢 Lecture lente'; }
});
"""


DIALOG_JS = """
/* Joue la scène en entier, réplique après réplique, en surlignant celle qui
   parle : c'est ce qui apprend à suivre une discussion, pas un mot isolé. */
function playDialogue(box){
  var lines = [].slice.call(box.querySelectorAll('.dline'));
  stopAll();
  var i = 0;
  (function next(){
    lines.forEach(function(o){ o.style.background = ''; });
    if(i >= lines.length) return;
    var el = lines[i++];
    el.style.background = 'rgba(127,127,127,.12)';
    playItem({ text: el.dataset.text, src: el.dataset.src }, function(){ setTimeout(next, 420); });
  })();
}
document.addEventListener('click', function(e){
  var line = e.target.closest('.dline.masked');
  if(line){ line.classList.remove('masked'); return; }
  var b = e.target.closest('button[data-act]');
  if(!b) return;
  var act = b.dataset.act;
  if(act === 'slow'){
    var slow = !isSlow();
    setSlow(slow);
    b.setAttribute('aria-pressed', slow ? 'true' : 'false');
    b.textContent = slow ? '🐢 Lecture lente' : '🐢 Lire lentement';
    return;
  }
  var box = b.closest('.convbox');
  if(!box) return;
  if(act === 'play'){ playDialogue(box); }
  if(act === 'fr'){
    var on = box.classList.toggle('nofr');
    box.querySelectorAll('.dline').forEach(function(el){ el.classList.toggle('hidden-fr', on); });
    b.textContent = on ? 'Montrer le français' : 'Cacher le français';
  }
  if(act === 'role'){
    var role = b.dataset.role;
    var already = b.getAttribute('aria-pressed') === 'true';
    box.querySelectorAll('button[data-act=role]').forEach(function(o){
      o.setAttribute('aria-pressed','false'); });
    box.querySelectorAll('.dline').forEach(function(el){
      el.classList.toggle('masked', !already && el.dataset.who === role); });
    b.setAttribute('aria-pressed', already ? 'false' : 'true');
  }
});
"""


def say_button(course: dict, text: str, voice: str = "f") -> str:
    src = audio_src(course, text, voice)
    attr = f' data-src="{E(src)}"' if src else ""
    return (f'<button class="say" data-text="{E(text)}" '
            f'data-lang="{E(course["speech_lang"])}"{attr} aria-label="Écouter">🔊</button>')


def audio_map_js(course: dict, texts: list[str]) -> str:
    """La table « texte → fichier » de la page, pour les flashcards et le dialogue."""
    import json
    mapping = {}
    for t in texts:
        src = audio_src(course, t)
        if src:
            mapping[t] = src
    return (f"var AUDIO_MAP = {json.dumps(mapping, ensure_ascii=False)};\n"
            f"var VOICE_LANG = {json.dumps(course['speech_lang'])};\n"
            f"var LANG_NAME = {json.dumps(course.get('name_fr', ''))};\n")


def vocab_table(unit_entries: list[dict], course: dict, with_audio: bool = True) -> str:
    rtl = course.get("direction") == "rtl"
    translit = course.get("has_transliteration")
    rows = []
    for v in unit_entries:
        # `level` réserve un mot à un âge : le parcours des petits saute ces
        # mots-là. Sans marque visible, le parent n'a aucun moyen de le savoir.
        mark = ""
        if v.get("level"):
            mark = (f'<span class="tag {E(v["level"])}">'
                    f'{E(level_label(course, v["level"]))}</span>')
        cells = [f'<td class="term">{E(v["term"])} {mark}</td>']
        if translit:
            cells.append(f'<td class="phon">{E(v.get("translit", ""))}</td>')
        cells.append(f'<td class="phon">{E(v.get("phon", ""))}</td>')
        cells.append(f'<td>{E(v.get("fr", ""))}</td>')
        if with_audio:
            cells.append(f'<td>{say_button(course, v["term"])}</td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')
    heads = ["Mot"] + (["Translittération"] if translit else []) + ["Se prononce", "Français"]
    if with_audio:
        heads.append("")
    th = "".join(f"<th>{h}</th>" for h in heads)
    cls = ' class="rtl"' if rtl else ""
    return f'<div class="tablewrap"><table{cls}><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


# --------------------------------------------------------------------------- #
# Conversation : dialogue, questions/réponses, compréhension
# --------------------------------------------------------------------------- #
def dialogue_html(course: dict, unit: dict, interactive: bool = True) -> str:
    """Le dialogue de l'unité : c'est là que les mots deviennent une discussion."""
    dlg = unit.get("dialogue") or {}
    lines = dialogue_lines(unit)
    if not lines:
        return ""
    lang = course["speech_lang"]
    roles = []
    for ln in lines:
        who = ln.get("who", "?")
        if who not in roles:
            roles.append(who)

    rendered = []
    for ln in lines:
        who = ln.get("who", "?")
        voice = "f" if roles.index(who) % 2 == 0 else "m"
        src = audio_src(course, ln["term"], voice)
        audio = say_button(course, ln["term"], voice) if interactive else ""
        phon = f'<span class="phon">{E(ln.get("phon", ""))}</span>' if ln.get("phon") else ""
        rendered.append(
            f'<div class="dline" data-role="{roles.index(who) % 2}" data-who="{E(who)}" '
            f'data-text="{E(ln["term"])}" data-lang="{E(lang)}" data-src="{E(src)}">'
            f'<span class="who">{E(who)}</span>'
            f'<span class="dtext"><span class="term">{E(ln["term"])}</span> {phon} {audio}'
            f'<span class="dfr">{E(ln.get("fr", ""))}</span></span></div>'
        )

    ctx = f'<p class="ctx">{E(dlg["context_fr"])}</p>' if dlg.get("context_fr") else ""
    controls = ""
    if interactive:
        role_btns = "".join(
            f'<button class="btn ghost" data-act="role" data-role="{E(r)}" aria-pressed="false">'
            f'Je joue {E(r)}</button>' for r in roles)
        controls = (f'<div class="row"><button class="btn" data-act="play">▶ Écouter le dialogue</button>'
                    f'<button class="btn ghost" data-act="fr">Cacher le français</button>'
                    f'{role_btns}</div>'
                    f'<p class="phon">« Je joue… » masque tes répliques : à toi de les dire. '
                    f'Clique sur une réplique floutée pour vérifier.</p>')
    title = dlg.get("title_fr", "Le dialogue")
    return (f'<div class="convbox"><h2>{E(title)}</h2>{ctx}'
            f'<div class="dial">{"".join(rendered)}</div>{controls}</div>')


def qa_html(course: dict, unit: dict, interactive: bool = True) -> str:
    """« On me demande / je réponds » : le pas qui manque entre comprendre et parler."""
    items = unit.get("qa") or []
    if not items:
        return ""
    lang = course["speech_lang"]
    blocks = []
    for item in items:
        q = item.get("question") or {}
        answers = item.get("answers") or []
        audio_q = say_button(course, q["term"], "m") if interactive else ""
        lis = []
        for a in answers:
            audio_a = say_button(course, a["term"]) if interactive else ""
            phon = f' <span class="phon">{E(a.get("phon", ""))}</span>' if a.get("phon") else ""
            lis.append(f'<li><span class="a">{E(a["term"])}</span>{phon} {audio_a}'
                       f'<span class="afr">{E(a.get("fr", ""))}</span></li>')
        phon_q = f' <span class="phon">{E(q.get("phon", ""))}</span>' if q.get("phon") else ""
        blocks.append(
            f'<div class="qa"><div class="q">{E(q["term"])}{phon_q} {audio_q}</div>'
            f'<div class="qfr">{E(q.get("fr", ""))}</div>'
            f'<ul>{"".join(lis)}</ul></div>')
    return ("<h2>On me demande, je réponds</h2>"
            "<p class=\"sub\">Plusieurs réponses sont possibles : l'enfant choisit celle qui est "
            "vraie pour lui. C'est ce qui fait une vraie conversation.</p>" + "".join(blocks))


def comprehension_html(unit: dict) -> str:
    """Vérifie que l'enfant a compris l'ensemble, pas seulement des mots isolés."""
    items = unit.get("comprehension") or []
    if not items:
        return ""
    blocks = [f'<details class="comp"><summary>{md_bold(c["q_fr"])}</summary>'
              f'<p>{md_bold(c.get("a_fr", ""))}</p></details>' for c in items]
    return ("<h2>Est-ce que j'ai compris ?</h2>"
            "<p class=\"sub\">Poser la question en français après avoir écouté le dialogue "
            "deux fois, sans le lire. Cliquer pour voir la réponse.</p>" + "".join(blocks))


def reemploi_html(unit: dict) -> str:
    """La langue ne sert que si elle sort du cours."""
    items = unit.get("reemploi_fr") or []
    if not items:
        return ""
    lis = "".join(f"<li>{md_bold(x)}</li>" for x in items)
    return ('<div class="goal"><strong>Cette semaine, dans la vraie vie :</strong>'
            f"<ul>{lis}</ul></div>")


def toolkit_html(course: dict, interactive: bool = True) -> str:
    """La boîte à outils : ce qu'on dit quand on ne sait plus quoi dire.

    C'est ce qui permet à un enfant de rester dans la conversation au lieu de
    la quitter dès qu'il bloque.
    """
    groups = course.get("toolkit") or []
    if not groups:
        return ""
    out = []
    for g in groups:
        out.append(f'<h2>{E(g.get("title_fr", ""))}</h2>')
        if g.get("intro_fr"):
            out.append(f'<p class="sub">{E(g["intro_fr"])}</p>')
        out.append(vocab_table(g.get("items", []), course, with_audio=interactive))
    return "".join(out)


# --------------------------------------------------------------------------- #
# Site
# --------------------------------------------------------------------------- #
def audio_bar() -> str:
    """Le réglage de vitesse et, le cas échéant, l'alerte « pas la bonne voix »."""
    return ('<div class="row"><button class="btn ghost" data-act="slow" aria-pressed="false">'
            '🐢 Lire lentement</button>'
            '<span class="phon" id="voicewarn"></span></div>')


def build_unit_page(course: dict, unit: dict, prev_u, next_u) -> str:
    lang = course["code"]
    parts = [
        '<div class="wrap">',
        f'<div class="crumb"><a href="index.html">← {E(course["name_fr"])}</a></div>',
        f'<h1>{E(unit["title"])}</h1>',
        f'<p class="sub">{E(unit["title_fr"])} · unité {unit.get("order", "")} · '
        f'{unit.get("duration_min", 15)} min'
        + (f' · {E(unit["cefr"])}' if unit.get("cefr") else "") + '</p>',
    ]
    if unit.get("can_do_fr"):
        items = "".join(f"<li>{md_bold(c)}</li>" for c in unit["can_do_fr"])
        parts.append(f'<div class="goal"><strong>À la fin de cette unité :</strong><ul>{items}</ul></div>')
    parts.append(audio_bar())

    # L'ordre suit la méthode : on entend une discussion entière d'abord, on
    # vérifie qu'on l'a comprise, et seulement ensuite on démonte les mots.
    parts.append(dialogue_html(course, unit))
    parts.append(comprehension_html(unit))

    if unit["vocab"]:
        parts.append("<h2>Le vocabulaire</h2>")
        parts.append(vocab_table(unit["vocab"], course))
    if unit["phrases"]:
        parts.append("<h2>Les phrases</h2>")
        parts.append(vocab_table(unit["phrases"], course))

    parts.append(qa_html(course, unit))

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

    if unit.get("culture_fr"):
        parts.append('<h2>Un pas de plus dans la culture</h2>')
        parts.append(f'<div class="mission">{md_bold(unit["culture_fr"])}</div>')
    parts.append(reemploi_html(unit))

    # Entraînement à répondre : la question sort en portugais, l'enfant répond
    # à voix haute, puis vérifie. C'est l'exercice le plus proche d'une vraie
    # discussion qu'on puisse faire seul.
    drill = [{"q": q["term"], "qf": q.get("fr", ""),
              "a": [{"t": a["term"], "f": a.get("fr", "")} for a in (item.get("answers") or [])]}
             for item in (unit.get("qa") or [])
             for q in [item.get("question") or {}] if q.get("term") and item.get("answers")]
    if drill:
        parts.append("<h2>Entraînement à répondre</h2>")
        parts.append('<div class="flash" id="drill"><div class="big" id="dq">Clique pour commencer</div>'
                     '<div class="ans" id="da"></div></div>'
                     '<div class="row"><button class="btn" id="dnext">Autre question</button>'
                     '<button class="btn ghost" id="dshow">Voir des réponses</button>'
                     '<span class="phon">Réponds à voix haute avant de regarder.</span></div>')

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

    page_texts = ([v["term"] for v in entries(unit)]
                  + [ln["term"] for ln in dialogue_lines(unit)]
                  + [t for item in (unit.get("qa") or [])
                     for t in ([(item.get("question") or {}).get("term", "")]
                               + [a["term"] for a in (item.get("answers") or [])]) if t])
    base_js = audio_map_js(course, page_texts) + SAY_JS + DIALOG_JS
    if drill:
        base_js += f"""
var DRILL = {json.dumps(drill, ensure_ascii=False)};
var DLANG = {json.dumps(course["speech_lang"])};
var d = -1;
function drillNext(){{
  d = Math.floor(Math.random() * DRILL.length);
  document.getElementById('dq').textContent = DRILL[d].q;
  document.getElementById('da').textContent = DRILL[d].qf;
  say(DRILL[d].q, DLANG);
}}
function drillShow(){{
  if(d < 0){{ drillNext(); return; }}
  document.getElementById('da').textContent =
    DRILL[d].a.map(function(a){{ return a.t; }}).join('  ·  ');
}}
document.getElementById('drill').addEventListener('click', function(){{
  if(d < 0) drillNext(); else drillShow(); }});
document.getElementById('dnext').addEventListener('click', function(e){{
  e.stopPropagation(); drillNext(); }});
document.getElementById('dshow').addEventListener('click', function(e){{
  e.stopPropagation(); drillShow(); }});
"""

    if not cards:
        return page(f'{unit["title"]} — {course["name_fr"]}', "\n".join(parts), SITE_CSS,
                    script=base_js)

    script = base_js + f"""
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


def unit_cards(course: dict, units: list[dict]) -> str:
    cards = []
    for u in units:
        cards.append(
            f'<a class="card" href="{E(u["id"])}.html">'
            f'<div class="n">Unité {E(u.get("order",""))}</div>'
            f'<div class="t">{E(u["title"])}</div>'
            f'<div class="f">{E(u["title_fr"])} — {md_bold(u.get("goal_fr",""))}</div></a>'
        )
    return f'<div class="grid">{"".join(cards)}</div>'


def build_lang_index(course: dict) -> str:
    levels = "".join(
        f'<li><strong>{E(lv["label_fr"])}</strong> — {E(lv["desc_fr"])}</li>'
        for lv in course.get("levels", [])
    )
    n_vocab = sum(len(entries(u)) for u in course["units"])
    n_qa = sum(len(u.get("qa") or []) for u in course["units"])
    n_dial = sum(1 for u in course["units"] if dialogue_lines(u))
    code = course["code"]
    has_pdf = (PDF / code / "cahier-complet.pdf").exists()

    grouped = units_by_year(course)
    n_years = f"{len(grouped)} année" + ("s" if len(grouped) > 1 else "")
    sections = []
    for year in sorted(grouped):
        y = year_entry(course, year)
        head = [f'<div class="yearhead"><h2>{E(year_label(course, year))}</h2>']
        sub = " · ".join(x for x in (y.get("cefr_fr"), y.get("age_fr")) if x)
        if sub:
            head.append(f'<p class="sub">{E(sub)}</p>')
        if y.get("goal_fr"):
            head.append(f'<p class="sub">{md_bold(y["goal_fr"])}</p>')
        if y.get("can_do_fr"):
            head.append('<strong>À la fin de l\'année, l\'enfant sait :</strong><ul>'
                        + "".join(f"<li>{md_bold(c)}</li>" for c in y["can_do_fr"]) + "</ul>")
        anchor = f'{spine_track(course.get("program") or {}).get("id", "x")}-annee-{year}'
        head.append(f'<p><a href="programme.html#{E(anchor)}">'
                    f'Le programme semaine par semaine →</a></p>')
        head.append("</div>")
        sections.append("".join(head) + unit_cards(course, grouped[year]))
    units_html = "".join(sections)

    entry_cards = []
    if course.get("program"):
        n_tracks = len(program_tracks(course["program"]))
        entry_cards.append(
            '<a class="card" href="programme.html">'
            '<div class="n">Le plan</div><div class="t">Le programme</div>'
            f'<div class="f">{n_tracks} parcours selon l\'âge, période par période, avec '
            'le niveau visé et comment savoir si c\'est acquis.</div></a>')
    if course.get("culture"):
        entry_cards.append(
            '<a class="card" href="passeport.html">'
            '<div class="n">Le voyage</div><div class="t">Le passeport culturel</div>'
            '<div class="f">Douze escales : ce qu\'on voit, ce qu\'on goûte, ce qu\'on '
            'écoute — et une mission à faire pour de vrai.</div></a>')
    if course.get("resources"):
        entry_cards.append(
            '<a class="card" href="ressources.html">'
            '<div class="n">Autour du cours</div><div class="t">Livres, chansons et écrans</div>'
            '<div class="f">Ce qui vaut la peine d\'être acheté, emprunté ou écouté, '
            'par âge.</div></a>')
    if course.get("toolkit"):
        entry_cards.append(
            '<a class="card" href="boite-a-outils.html">'
            '<div class="n">Pour tenir la discussion</div><div class="t">La boîte à outils</div>'
            '<div class="f">Ce qu\'on dit quand on n\'a pas compris, qu\'on cherche un mot '
            'ou qu\'on veut gagner du temps.</div></a>')

    dl = ['<p>Chaque unité donne quatre feuilles A4 : la fiche de cours, le dialogue avec '
          'les questions-réponses, les activités et les cartes de vocabulaire à découper.</p><ul>']
    cahier = f'<a href="../print/{E(code)}/cahier-complet.html">Le cahier complet (HTML, Ctrl+P pour imprimer)</a>'
    if has_pdf:
        cahier += f' · <a href="../pdf/{E(code)}/cahier-complet.pdf">PDF</a>'
    dl.append(f"<li><strong>{cahier}</strong></li>")
    if course.get("program"):
        line = (f'Le programme de l\'année (à afficher au mur) : '
                f'<a href="../print/{E(code)}/programme.html">HTML</a>')
        if has_pdf:
            line += f' · <a href="../pdf/{E(code)}/programme.pdf">PDF</a>'
        dl.append(f"<li>{line}</li>")
    for key, name, label in (("toolkit", "boite-a-outils", "La boîte à outils de la discussion"),
                             ("culture", "passeport", "Le passeport culturel (à tamponner)"),
                             ("resources", "ressources", "La liste des livres et des chansons")):
        if not course.get(key):
            continue
        line = f'{label} : <a href="../print/{E(code)}/{name}.html">HTML</a>'
        if has_pdf:
            line += f' · <a href="../pdf/{E(code)}/{name}.pdf">PDF</a>'
        dl.append(f"<li>{line}</li>")
    for u in course["units"]:
        line = (f'Année {u.get("year", 1)} · unité {E(u.get("order",""))} — {E(u["title"])} : '
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
<p class="sub">{E(course.get("variant_fr",""))} · {n_years} · {len(course["units"])} unités · {n_vocab} mots et phrases · {n_dial} dialogues · {n_qa} questions à savoir répondre</p>
<div class="goal"><strong>Deux niveaux dans chaque unité :</strong><ul>{levels}</ul></div>
<h2>Par où commencer</h2>
<div class="grid">{"".join(entry_cards)}</div>
{units_html}
<h2>À imprimer et à emporter</h2>
<div class="dl">{downloads}</div>
<footer><p>{E(course.get("note_fr",""))}</p></footer>
</div>"""
    return page(course["name_fr"], body, SITE_CSS)


def periods_table(course: dict, year: dict, by_id: dict, links: bool) -> str:
    rows = []
    for per in year.get("periods", []):
        names = []
        for uid in per.get("units", []):
            u = by_id.get(uid, {"title": uid, "title_fr": ""})
            label = f'{E(u.get("title", uid))} <span class="phon">{E(u.get("title_fr",""))}</span>'
            names.append(f'<span class="u"><a href="{E(uid)}.html">{label}</a></span>'
                         if links else f'<span class="u">{label}</span>')
        # Une période sans unité neuve est une période de révision : le dire,
        # plutôt que laisser une case vide qui ressemble à un oubli.
        cell = "".join(names) or '<span class="week">révision, pas d\'unité neuve</span>'
        rows.append(
            f'<tr><td><strong>{E(per.get("label_fr",""))}</strong>'
            f'<div class="week">{E(per.get("weeks_fr",""))}</div></td>'
            f'<td>{cell}</td>'
            f'<td>{md_bold(per.get("focus_fr",""))}</td>'
            f'<td>{md_bold(per.get("milestone_fr",""))}</td></tr>')
    if not rows:
        return ""
    return ('<div class="plan tablewrap"><table><thead><tr><th>Période</th>'
            '<th>Unités</th><th>Ce qu\'on travaille</th>'
            '<th>Bilan de la période</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def track_html(course: dict, track: dict, by_id: dict, links: bool) -> str:
    """Un parcours complet : à qui il s'adresse, à quel rythme, jusqu'où."""
    parts = [f'<h2 id="parcours-{E(track.get("id","x"))}">{E(track.get("label_fr",""))}</h2>']

    chips = []
    for key, prefix in (("ages_fr", "Âge"), ("cefr_fr", "Niveau visé"),
                        ("session_fr", "Séance"), ("total_fr", "Durée")):
        if track.get(key):
            chips.append(f'<span class="chip"><strong>{prefix} :</strong> {E(track[key])}</span>')
    if chips:
        parts.append(f'<div class="chips">{"".join(chips)}</div>')
    if track.get("intro_fr"):
        parts.append(f"<p>{md_bold(track['intro_fr'])}</p>")
    if track.get("method_fr"):
        parts.append('<div class="note"><strong>Les règles de ce parcours :</strong><ul>'
                     + "".join(f"<li>{md_bold(x)}</li>" for x in track["method_fr"]) + "</ul></div>")

    if track.get("rhythm_fr"):
        rows = "".join(
            f'<tr><td><strong>{E(r.get("day_fr",""))}</strong></td>'
            f'<td>{md_bold(r.get("what_fr",""))}</td>'
            f'<td class="week">{E(r.get("min",""))} min</td></tr>'
            for r in track["rhythm_fr"])
        parts.append("<h3>La semaine type</h3>"
                     f'<div class="tablewrap"><table><thead><tr><th>Quand</th><th>Quoi</th>'
                     f'<th>Durée</th></tr></thead><tbody>{rows}</tbody></table></div>')

    if track.get("cycle_fr"):
        rows = "".join(
            f'<tr><td><strong>{E(c.get("label_fr",""))}</strong></td>'
            f'<td>{md_bold(c.get("what_fr",""))}</td></tr>'
            for c in track["cycle_fr"])
        parts.append("<h3>Comment on traite une unité</h3>"
                     f'<div class="tablewrap"><table><tbody>{rows}</tbody></table></div>')

    for y in track.get("years", []):
        head = [f'<div class="yearhead" id="{E(track.get("id","x"))}-annee-{y.get("year", 1)}">'
                f'<h3>{E(y.get("label_fr", ""))}</h3>']
        sub = " · ".join(x for x in (y.get("age_fr"), y.get("cefr_fr")) if x)
        if sub:
            head.append(f'<p class="sub">{E(sub)}</p>')
        if y.get("goal_fr"):
            head.append(f"<p>{md_bold(y['goal_fr'])}</p>")
        if y.get("can_do_fr"):
            head.append("<strong>Ce que l\'enfant sait faire à la fin de l\'année :</strong><ul>"
                        + "".join(f"<li>{md_bold(c)}</li>" for c in y["can_do_fr"]) + "</ul>")
        head.append("</div>")
        parts.append("".join(head))
        parts.append(periods_table(course, y, by_id, links))
        if y.get("evaluation_fr"):
            parts.append('<div class="goal"><strong>Comment vérifier, sans faire d\'examen :</strong><ul>'
                         + "".join(f"<li>{md_bold(x)}</li>" for x in y["evaluation_fr"])
                         + "</ul></div>")
    return "".join(parts)


def program_body(course: dict, links: bool = True) -> str:
    """Le corps du programme, partagé par la page web et la feuille à imprimer."""
    prog = course.get("program") or {}
    by_id = {u["id"]: u for u in course["units"]}
    parts = []
    if prog.get("intro_fr"):
        parts.append(f'<p class="sub">{md_bold(prog["intro_fr"])}</p>')
    if prog.get("cefr_fr"):
        parts.append(f'<div class="note">{md_bold(prog["cefr_fr"])}</div>')

    tracks = program_tracks(prog)
    if len(tracks) > 1:
        links_html = " · ".join(
            f'<a href="#parcours-{E(t.get("id","x"))}">{E(t.get("label_fr",""))}</a>'
            for t in tracks)
        parts.append(f'<p class="sub">Deux parcours, un seul contenu : {links_html}</p>')

    for track in tracks:
        parts.append(track_html(course, track, by_id, links))

    if prog.get("bridge_fr"):
        parts.append('<h2>Passer d\'un parcours à l\'autre</h2>'
                     f'<div class="note">{md_bold(prog["bridge_fr"])}</div>')

    if prog.get("practice_fr"):
        parts.append("<h2>La pratique — ce qui fait vraiment la différence</h2>")
        parts.append('<p class="sub">Le programme organise, il ne remplace pas l\'usage. '
                     'Une heure de vraie conversation vaut dix fiches.</p>')
        for item in prog["practice_fr"]:
            steps = "".join(f"<li>{md_bold(x)}</li>" for x in item.get("steps_fr", []))
            parts.append(f'<div class="act"><h3>{E(item.get("title_fr",""))}</h3>'
                         f'<p class="sub">{E(item.get("when_fr",""))}</p><ul>{steps}</ul></div>')
    return "".join(parts)


def culture_body(course: dict, interactive: bool = True) -> str:
    """Le passeport culturel : douze escales dans le monde de la langue.

    Un cours de langue qui ne fait pas voyager reste un cours. Chaque escale
    donne quelque chose à voir, à goûter, à écouter, une histoire — et une
    mission à faire pour de vrai.
    """
    culture = course.get("culture") or {}
    escales = culture.get("escales") or []
    if not escales:
        return ""
    parts = []
    if culture.get("intro_fr"):
        parts.append(f'<p class="sub">{md_bold(culture["intro_fr"])}</p>')
    for i, e in enumerate(escales, 1):
        box = [f'<div class="escale" id="escale-{i}">',
               f'<div class="n">Escale {i}'
               + (f' · {E(e["when_fr"])}' if e.get("when_fr") else "") + "</div>",
               f'<h3>{E(e.get("label_fr", ""))}</h3>']
        if e.get("intro_fr"):
            box.append(f'<p>{md_bold(e["intro_fr"])}</p>')
        rows = []
        for key, label in (("see_fr", "À voir"), ("taste_fr", "À goûter"),
                           ("listen_fr", "À écouter"), ("story_fr", "L\'histoire"),
                           ("know_fr", "À savoir")):
            if e.get(key):
                rows.append(f'<li><strong>{label} :</strong> {md_bold(e[key])}</li>')
        if rows:
            box.append(f'<ul class="esc">{"".join(rows)}</ul>')
        if e.get("words"):
            box.append(vocab_table(e["words"], course, with_audio=interactive))
        if e.get("mission_fr"):
            box.append(f'<div class="mission"><strong>La mission :</strong> '
                       f'{md_bold(e["mission_fr"])}</div>')
        box.append("</div>")
        parts.append("".join(box))
    if culture.get("outro_fr"):
        parts.append(f'<div class="note">{md_bold(culture["outro_fr"])}</div>')
    return "".join(parts)


def build_culture_page(course: dict) -> str:
    culture = course.get("culture") or {}
    title = culture.get("title_fr", "Passeport culturel")
    body = (f'<div class="wrap">'
            f'<div class="crumb"><a href="index.html">← {E(course["name_fr"])}</a></div>'
            f'<h1>{E(title)}</h1>'
            + audio_bar()
            + culture_body(course)
            + '<footer>Une escale par mois, dans l\'ordre qu\'on veut. Le tampon se '
              'gagne quand la mission est faite — pas quand l\'escale est lue.</footer></div>')
    texts = [w["term"] for e in (culture.get("escales") or []) for w in (e.get("words") or [])]
    return page(f'{title} — {course["name_fr"]}', body, SITE_CSS,
                script=audio_map_js(course, texts) + SAY_JS + DIALOG_JS)


def build_print_culture(course: dict) -> str:
    """Le passeport à imprimer : une case à tamponner par escale."""
    culture = course.get("culture") or {}
    escales = culture.get("escales") or []
    cells = "".join(
        f'<div class="cut"><div class="t">{E(e.get("label_fr", ""))}</div>'
        f'<div class="p">{E(e.get("when_fr", ""))}</div>'
        f'<div class="f">{E(shorten(plain(e.get("mission_fr", "")), 90))}</div></div>'
        for e in escales)
    body = (f'<div class="sheet"><h1>{E(course["name_fr"])} — passeport culturel</h1>'
            f'<p class="sub">Une case par escale. On la signe ou on la tamponne quand la '
            f'mission est faite pour de vrai.</p>'
            f'<div class="cutgrid">{cells}</div>'
            f'<footer>{E(course["name_fr"])} — passeport culturel</footer></div>'
            f'<div class="sheet"><h1>Les escales en détail</h1>'
            + culture_body(course, interactive=False)
            + f'<footer>{E(course["name_fr"])} — escales</footer></div>')
    return page(f'{course["name_fr"]} — passeport culturel', body, PRINT_CSS)


def resources_body(course: dict) -> str:
    """Livres, chansons, écrans, dictionnaires : ce qu'on achète ou emprunte."""
    res = course.get("resources") or {}
    groups = res.get("groups") or []
    if not groups:
        return ""
    parts = []
    if res.get("intro_fr"):
        parts.append(f'<p class="sub">{md_bold(res["intro_fr"])}</p>')
    if res.get("warning_fr"):
        parts.append(f'<div class="note">{md_bold(res["warning_fr"])}</div>')
    for g in groups:
        parts.append(f'<h2>{E(g.get("title_fr", ""))}</h2>')
        if g.get("intro_fr"):
            parts.append(f'<p class="sub">{E(g["intro_fr"])}</p>')
        rows = []
        for it in g.get("items", []):
            who = " · ".join(x for x in (it.get("author"), it.get("kind_fr"),
                                         it.get("age_fr")) if x)
            rows.append(
                f'<tr><td><strong>{E(it.get("title", ""))}</strong>'
                + (f'<div class="week">{E(who)}</div>' if who else "")
                + f'</td><td>{md_bold(it.get("why_fr", ""))}</td>'
                + f'<td class="week">{md_bold(it.get("where_fr", ""))}</td></tr>')
        parts.append('<div class="tablewrap"><table><thead><tr><th>Titre</th>'
                     '<th>Pourquoi celui-là</th><th>Où le trouver</th></tr></thead>'
                     f'<tbody>{"".join(rows)}</tbody></table></div>')
    if res.get("outro_fr"):
        parts.append(f'<div class="goal">{md_bold(res["outro_fr"])}</div>')
    return "".join(parts)


def build_resources_page(course: dict) -> str:
    res = course.get("resources") or {}
    title = res.get("title_fr", "Livres, chansons et écrans")
    body = (f'<div class="wrap">'
            f'<div class="crumb"><a href="index.html">← {E(course["name_fr"])}</a></div>'
            f'<h1>{E(title)}</h1>' + resources_body(course)
            + '<footer>Rien ici n\'est obligatoire. Un seul album lu vingt fois vaut '
              'mieux que dix achetés une fois.</footer></div>')
    return page(f'{title} — {course["name_fr"]}', body, SITE_CSS)


def build_print_resources(course: dict) -> str:
    body = (f'<div class="sheet"><h1>{E(course["name_fr"])} — la liste à emporter</h1>'
            + resources_body(course)
            + f'<footer>{E(course["name_fr"])} — livres, chansons et écrans</footer></div>')
    return page(f'{course["name_fr"]} — ressources', body, PRINT_CSS)


def build_program_page(course: dict) -> str:
    body = (f'<div class="wrap">'
            f'<div class="crumb"><a href="index.html">← {E(course["name_fr"])}</a></div>'
            f'<h1>Le programme</h1>'
            + program_body(course)
            + '<footer>Le programme est un cadre, pas une course. Une semaine sautée se '
              'rattrape ; une unité mal tenue se refait.</footer></div>')
    return page(f'Programme — {course["name_fr"]}', body, SITE_CSS)


def build_toolkit_page(course: dict) -> str:
    body = (f'<div class="wrap">'
            f'<div class="crumb"><a href="index.html">← {E(course["name_fr"])}</a></div>'
            f'<h1>La boîte à outils de la discussion</h1>'
            f'<p class="sub">Ces phrases ne s\'apprennent pas dans une unité : elles se '
            f'révisent toute l\'année. Elles servent à <strong>rester dans la conversation</strong> '
            f'quand on ne comprend pas — c\'est exactement ce qui manque quand un enfant se tait.</p>'
            + audio_bar()
            + toolkit_html(course)
            + '<footer>À afficher près de la table. Trois phrases suffisent pour commencer : '
              '« não percebi », « outra vez, por favor », « como se diz… ? »</footer></div>')
    texts = [v["term"] for g in (course.get("toolkit") or []) for v in g.get("items", [])]
    return page(f'Boîte à outils — {course["name_fr"]}', body, SITE_CSS,
                script=audio_map_js(course, texts) + SAY_JS + DIALOG_JS)


def build_voice_help(langs: list[dict]) -> str:
    """Comment obtenir une vraie voix. La page vers laquelle pointe l'alerte du site."""
    rows = "".join(
        f'<tr><td>{E(c["name_fr"])}</td><td><code>{E(c["speech_lang"])}</code></td>'
        f'<td>{E(c.get("variant_fr", ""))}</td></tr>' for c in langs)
    body = f"""<div class="wrap">
<div class="crumb"><a href="index.html">← Toutes les langues</a></div>
<h1>Avoir une vraie voix</h1>
<p class="sub">Une mauvaise voix apprend une mauvaise prononciation. Le site refuse
donc de lire la langue avec une voix qui ne la parle pas.</p>

<h2>1. Les enregistrements du site (le mieux)</h2>
<p>Si le dépôt a été construit avec <code>make audio</code>, chaque mot, chaque
réplique et chaque réponse possède un <strong>enregistrement en voix de synthèse
neuronale de la variante enseignée</strong> (deux voix différentes dans les
dialogues, une par personnage). Rien à installer : le bouton 🔊 joue le fichier.</p>
<p>Pour les produire soi-même :</p>
<pre><code>make audio      # écrit assets/audio/&lt;langue&gt;/*.mp3 puis regénère le site</code></pre>
<p>Pour une voix humaine, remplacer un fichier <code>.mp3</code> par son propre
enregistrement en gardant le même nom : le site le jouera à la place.</p>

<h2>2. Sans enregistrement : la voix du système</h2>
<p>Le navigateur n'utilise que les voix installées sur l'appareil. Il faut donc
en installer une dans la bonne langue :</p>
<ul>
<li><strong>iPhone / iPad</strong> — Réglages → Accessibilité → Contenu énoncé →
Voix → choisir la langue, puis télécharger une voix marquée
<em>Améliorée</em> ou <em>Premium</em> (les voix « compactes » sonnent mal).</li>
<li><strong>Mac</strong> — Réglages Système → Accessibilité → Contenu énoncé →
Voix du système → Gérer les voix.</li>
<li><strong>Android</strong> — Paramètres → Système → Langues → Synthèse vocale →
moteur Google → Installer les données vocales.</li>
<li><strong>Windows</strong> — Paramètres → Heure et langue → Voix → Ajouter des voix.
Edge apporte en plus des voix « Natural » de très bonne qualité.</li>
</ul>
<p>Après installation, fermer complètement le navigateur et rouvrir la page.</p>

<h2>Les codes de voix attendus</h2>
<div class="tablewrap"><table><thead><tr><th>Langue</th><th>Code</th>
<th>Variante enseignée</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="sub">Une voix d'une autre variante (brésilienne pour du portugais du
Portugal, par exemple) reste utilisable : le site l'accepte mais le signale,
car l'accent et certains mots diffèrent.</p>
</div>"""
    return page("Avoir une vraie voix", body, SITE_CSS)


def build_home(langs: list[dict]) -> str:
    cards = []
    for c in langs:
        cards.append(
            f'<a class="card" href="{E(c["code"])}/index.html">'
            f'<div class="n">{E(c.get("variant_fr", ""))}</div>'
            f'<div class="t">{E(c["name"])}</div>'
            f'<div class="f">{E(c["name_fr"])} — {len(c["units"])} unités sur '
            f'{len(units_by_year(c))} années</div></a>'
        )
    body = f"""<div class="wrap">
<h1>Les langues à la maison</h1>
<p class="sub">Un vrai programme sur plusieurs années pour que l'enfant comprenne
une discussion entière et sache y répondre.</p>
<div class="grid">{"".join(cards)}</div>
<h2>Le son</h2>
<p>Les boutons 🔊 jouent de vrais enregistrements dans la langue enseignée quand ils
ont été produits, sinon la voix du système — jamais une voix d'une autre langue.
Si rien ne se lit : <a href="voix.html">avoir une vraie voix</a>.</p>
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
.dial{border:.5pt solid #999;border-radius:2mm;padding:2mm 3mm;margin:2mm 0}
.dline{padding:1.6mm 0;border-bottom:.4pt dotted #bbb}
.dline:last-child{border-bottom:none}
.who{font-size:8.5pt;text-transform:uppercase;letter-spacing:.05em;color:#444;
  border:.5pt solid #666;border-radius:8pt;padding:.3mm 1.6mm;margin-right:2mm}
.dfr{color:#555;font-size:10pt}
.qa{border-left:1.5pt solid #111;padding:1mm 0 1mm 3mm;margin:2.5mm 0}
.qa .q{font-weight:700}
.qa .qfr{color:#555;font-size:10pt;margin-bottom:1mm}
.qa ul{list-style:none;padding-left:0;margin:0}
.qa li{padding:.6mm 0 .6mm 3mm;border-left:.5pt solid #bbb}
.qa .afr{color:#555;font-size:9.5pt}
.plan table{font-size:10pt}
.plan td{vertical-align:top}
.plan .u{display:block}
.week{color:#555;font-size:9pt}
.ctx{font-style:italic;color:#555;margin:1mm 0 2mm}
.escale{border:.5pt solid #999;border-radius:2mm;padding:3mm 4mm;margin:3mm 0}
.escale .n{font-size:8.5pt;text-transform:uppercase;letter-spacing:.05em;color:#555}
.escale h3{margin:1mm 0 2mm;font-size:12pt}
ul.esc{list-style:none;padding-left:0}
ul.esc li{padding:.6mm 0 .6mm 2.5mm;border-left:.5pt solid #bbb;margin:.6mm 0}
.mission{border:.5pt dashed #333;padding:2mm 3mm;margin:2mm 0}
.chips{margin:2mm 0}
.chip{border:.5pt solid #666;border-radius:10pt;padding:.4mm 2mm;margin-right:2mm;font-size:9pt}
h3{font-size:12pt;margin:4mm 0 1.5mm}
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
                 + "".join(f"<li>{md_bold(c)}</li>" for c in unit["can_do_fr"]) + "</ul></div>")
    if unit["vocab"]:
        p.append("<h2>Vocabulaire</h2>" + vocab_table(unit["vocab"], course, with_audio=False))
    if unit["phrases"]:
        p.append("<h2>Phrases</h2>" + vocab_table(unit["phrases"], course, with_audio=False))
    for n in unit["notes_fr"]:
        p.append(f'<div class="note">{md_bold(n)}</div>')
    p.append(f'<footer>{E(course["name_fr"])} — {E(unit["title"])} — fiche de cours</footer></div>')
    sheets.append("".join(p))

    # Feuille 2 : le dialogue et les réponses — la feuille qu'on garde sous les
    # yeux pendant qu'on joue la scène à deux.
    conv = []
    if dialogue_lines(unit):
        dlg = unit["dialogue"]
        conv.append(f'<h2>{E(dlg.get("title_fr", "Le dialogue"))}</h2>')
        if dlg.get("context_fr"):
            conv.append(f'<p class="ctx">{E(dlg["context_fr"])}</p>')
        lines = []
        for ln in dialogue_lines(unit):
            phon = f' <span class="phon">{E(ln.get("phon",""))}</span>' if ln.get("phon") else ""
            lines.append(f'<div class="dline"><span class="who">{E(ln.get("who","?"))}</span>'
                         f'<span class="term">{E(ln["term"])}</span>{phon}'
                         f'<div class="dfr">{E(ln.get("fr",""))}</div></div>')
        conv.append(f'<div class="dial">{"".join(lines)}</div>')
    if unit.get("comprehension"):
        conv.append("<h2>Est-ce que j'ai compris ?</h2><ol>"
                    + "".join(f'<li>{md_bold(c["q_fr"])}<br><span class="phon">Réponse : '
                              f'{md_bold(c.get("a_fr",""))}</span></li>' for c in unit["comprehension"])
                    + "</ol>")
    if unit.get("qa"):
        conv.append("<h2>On me demande, je réponds</h2>")
        for item in unit["qa"]:
            q = item.get("question") or {}
            lis = "".join(
                f'<li><strong>{E(a["term"])}</strong> '
                f'<span class="phon">{E(a.get("phon",""))}</span>'
                f'<div class="afr">{E(a.get("fr",""))}</div></li>'
                for a in (item.get("answers") or []))
            conv.append(f'<div class="qa"><div class="q">{E(q.get("term",""))} '
                        f'<span class="phon">{E(q.get("phon",""))}</span></div>'
                        f'<div class="qfr">{E(q.get("fr",""))}</div><ul>{lis}</ul></div>')
    if conv:
        sheets.append(f'<div class="sheet"><h1>{E(unit["title"])} — la discussion</h1>'
                      f'<p class="sub">Le parent lit une réplique, l\'enfant donne la suivante. '
                      f'Puis on échange les rôles.</p>'
                      + "".join(conv)
                      + f'<footer>{E(course["name_fr"])} — {E(unit["title"])} — la discussion</footer></div>')

    # Feuille 3 : les activités
    if unit["activities"]:
        a_parts = [f'<div class="sheet"><h1>{E(unit["title"])} — activités</h1>']
        for a in unit["activities"]:
            steps = "".join(f"<li>{md_bold(s)}</li>" for s in a.get("steps_fr", []))
            a_parts.append(
                f'<div class="act"><span class="tag">{E(level_label(course, a.get("level","")))}</span>'
                f'<span class="tag">{E(a.get("type",""))}</span>'
                f'<h3>{E(a.get("title_fr",""))}</h3><ol>{steps}</ol></div>'
            )
        if unit.get("culture_fr"):
            a_parts.append('<div class="mission"><strong>Un pas de plus dans la culture :</strong> '
                           + md_bold(unit["culture_fr"]) + "</div>")
        if unit.get("reemploi_fr"):
            a_parts.append('<div class="note"><strong>Cette semaine, dans la vraie vie :</strong><ul>'
                           + "".join(f"<li>{md_bold(x)}</li>" for x in unit["reemploi_fr"])
                           + "</ul></div>")
        a_parts.append(f'<footer>{E(course["name_fr"])} — {E(unit["title"])} — activités</footer></div>')
        sheets.append("".join(a_parts))

    # Feuille 4 : les cartes à découper
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


def build_print_program(course: dict) -> str:
    body = (f'<div class="sheet"><h1>{E(course["name_fr"])} — le programme</h1>'
            f'<p class="sub">À afficher : on coche l\'unité quand les « je sais… » sont tenus.</p>'
            + program_body(course, links=False)
            + f'<footer>{E(course["name_fr"])} — programme</footer></div>')
    return page(f'{course["name_fr"]} — programme', body, PRINT_CSS)


def build_print_toolkit(course: dict) -> str:
    body = (f'<div class="sheet"><h1>{E(course["name_fr"])} — boîte à outils</h1>'
            f'<p class="sub">Les phrases qui permettent de rester dans la discussion '
            f'quand on ne comprend pas. À garder sur la table.</p>'
            + toolkit_html(course, interactive=False)
            + f'<footer>{E(course["name_fr"])} — boîte à outils</footer></div>')
    return page(f'{course["name_fr"]} — boîte à outils', body, PRINT_CSS)


def strip_page(html_doc: str) -> str:
    """Ne garde que le corps d'une page déjà construite, pour l'empiler dans le cahier."""
    return html_doc.split("<body>\n", 1)[1].rsplit("\n", 3)[0]


def build_print_all(course: dict) -> str:
    body = []
    if course.get("program"):
        body.append(strip_page(build_print_program(course)))
    if course.get("toolkit"):
        body.append(strip_page(build_print_toolkit(course)))
    if course.get("culture"):
        body.append(strip_page(build_print_culture(course)))
    if course.get("resources"):
        body.append(strip_page(build_print_resources(course)))
    for u in course["units"]:
        body.append(strip_page(build_print_unit(course, u)))
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
            # Une carte « on me pose cette question, je réponds ça » : c'est ce
            # qui s'utilise dans une discussion, pas le mot seul.
            for item in (u.get("qa") or []):
                q = item.get("question") or {}
                answers = item.get("answers") or []
                if not q.get("term") or not answers:
                    continue
                verso = "<br>".join(
                    f'{a["term"]} <i>({a.get("fr", "")})</i>' for a in answers)
                w.writerow([f'{q["term"]}<br><i>{q.get("fr", "")}</i>', verso,
                            f'{tag} {course["code"]}::conversa'])
        for g in (course.get("toolkit") or []):
            for v in g.get("items", []):
                w.writerow([v["term"], v.get("fr", ""), f'{course["code"]}::ferramentas'])
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
    (SITE / "voix.html").write_text(build_voice_help(langs), encoding="utf-8")
    print("site/index.html")

    for course in langs:
        code = course["code"]
        sdir = SITE / code
        pdir = PRINT / code
        sdir.mkdir(parents=True)
        pdir.mkdir(parents=True)

        (sdir / "index.html").write_text(build_lang_index(course), encoding="utf-8")
        if course.get("program"):
            (sdir / "programme.html").write_text(build_program_page(course), encoding="utf-8")
            (pdir / "programme.html").write_text(build_print_program(course), encoding="utf-8")
        if course.get("toolkit"):
            (sdir / "boite-a-outils.html").write_text(build_toolkit_page(course), encoding="utf-8")
            (pdir / "boite-a-outils.html").write_text(build_print_toolkit(course), encoding="utf-8")
        if course.get("culture"):
            (sdir / "passeport.html").write_text(build_culture_page(course), encoding="utf-8")
            (pdir / "passeport.html").write_text(build_print_culture(course), encoding="utf-8")
        if course.get("resources"):
            (sdir / "ressources.html").write_text(build_resources_page(course), encoding="utf-8")
            (pdir / "ressources.html").write_text(build_print_resources(course), encoding="utf-8")
        units = course["units"]
        for i, u in enumerate(units):
            prev_u = units[i - 1] if i else None
            next_u = units[i + 1] if i + 1 < len(units) else None
            (sdir / f'{u["id"]}.html').write_text(
                build_unit_page(course, u, prev_u, next_u), encoding="utf-8")
            (pdir / f'{u["id"]}.html').write_text(build_print_unit(course, u), encoding="utf-8")
        (pdir / "cahier-complet.html").write_text(build_print_all(course), encoding="utf-8")

        n_years = len(units_by_year(course))
        n_dial = sum(1 for u in units if dialogue_lines(u))
        n_qa = sum(len(u.get("qa") or []) for u in units)
        print(f'{course["name_fr"]} : {len(units)} unités sur {n_years} années, '
              f'{n_dial} dialogues, {n_qa} questions → site/{code}/ et print/{code}/')
        missing = [u["id"] for u in units if not dialogue_lines(u)]
        if missing:
            print(f'  (sans dialogue : {", ".join(missing)})')
        build_exports(course)

    # Le site publié embarque les fiches, les PDF (s'ils ont été produits) et les exports,
    # pour qu'un seul dossier suffise à tout distribuer.
    shutil.copytree(PRINT, SITE / "print")
    shutil.copytree(EXPORTS, SITE / "exports")
    # Les enregistrements réels priment sur la voix de synthèse : s'ils existent,
    # ils partent avec le site (voir scripts/audio.py).
    if AUDIO.exists():
        shutil.copytree(AUDIO, SITE / "audio", ignore=shutil.ignore_patterns("*.md"))
        n = len(list((SITE / "audio").rglob("*.mp3")))
        print(f"audio/ : {n} enregistrements inclus dans le site")
    else:
        print("audio/ : aucun enregistrement (make audio) — le site utilisera la voix "
              "de synthèse du navigateur")
    if PDF.exists():
        shutil.copytree(PDF, SITE / "pdf")
        print("pdf/ inclus dans le site")

    print("\nOK. Ouvrir site/index.html — imprimer depuis print/<langue>/cahier-complet.html")


if __name__ == "__main__":
    main()
