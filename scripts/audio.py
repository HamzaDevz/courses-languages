#!/usr/bin/env python3
"""Fabrique de vrais enregistrements pour chaque mot, réplique et réponse.

La voix de synthèse d'un navigateur est une loterie : sur beaucoup d'appareils
il n'y a aucune voix portugaise et la phrase est lue par une voix française,
donc faux. Ce script produit une fois pour toutes des fichiers MP3 avec une voix
neuronale **de la variante enseignée** (portugais du Portugal, pas du Brésil),
et deux voix différentes pour que les dialogues sonnent comme une discussion.

    make audio          # ou : python3 scripts/audio.py

Sortie : assets/audio/<langue>/*.mp3 + index.json (le manifeste lu par build.py).
Les fichiers déjà présents ne sont pas refaits : relancer est rapide et gratuit.

Pour une voix humaine, remplacer un .mp3 par son propre enregistrement en
gardant le même nom : le site jouera celui-là.

Dépendance : edge-tts (pip install -r requirements-audio.txt). Elle n'est pas
nécessaire pour construire le site.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build import (AUDIO, dialogue_lines, entries, load_all)  # noqa: E402

# Voix neuronales par défaut, une féminine et une masculine, choisies dans la
# variante enseignée. `voices:` dans course.yaml permet de les remplacer.
DEFAULT_VOICES = {
    "pt-PT": {"f": "pt-PT-RaquelNeural", "m": "pt-PT-DuarteNeural"},
    "pt-BR": {"f": "pt-BR-FranciscaNeural", "m": "pt-BR-AntonioNeural"},
    "ar-SA": {"f": "ar-SA-ZariyahNeural", "m": "ar-SA-HamedNeural"},
    "es-ES": {"f": "es-ES-ElviraNeural", "m": "es-ES-AlvaroNeural"},
    "en-GB": {"f": "en-GB-SoniaNeural", "m": "en-GB-RyanNeural"},
}


def voices_for(course: dict) -> dict[str, str]:
    lang = course["speech_lang"]
    voices = dict(DEFAULT_VOICES.get(lang, {}))
    voices.update(course.get("voices") or {})
    if not voices:
        raise SystemExit(
            f'Aucune voix connue pour « {lang} » ({course["name_fr"]}).\n'
            f"Ajoutez dans content/{course['code']}/course.yaml :\n"
            f"  voices:\n    f: <voix-feminine>\n    m: <voix-masculine>\n"
            f"La liste des voix disponibles : python3 -m edge_tts --list-voices")
    return voices


def wanted_clips(course: dict) -> dict[str, set[str]]:
    """Quel texte doit être enregistré, et avec quelle voix.

    Le choix des voix suit exactement celui de build.py : premier personnage du
    dialogue en voix féminine, deuxième en masculine, questions en masculine.
    """
    need: dict[str, set[str]] = {}

    def add(text: str, voice: str) -> None:
        text = (text or "").strip()
        if text:
            need.setdefault(text, set()).add(voice)

    for unit in course["units"]:
        for v in entries(unit):
            add(v["term"], "f")
        roles: list[str] = []
        for line in dialogue_lines(unit):
            who = line.get("who", "?")
            if who not in roles:
                roles.append(who)
            add(line["term"], "f" if roles.index(who) % 2 == 0 else "m")
        for item in unit.get("qa") or []:
            add((item.get("question") or {}).get("term", ""), "m")
            for a in item.get("answers") or []:
                add(a["term"], "f")
    for group in course.get("toolkit") or []:
        for v in group.get("items", []):
            add(v["term"], "f")
    for escale in (course.get("culture") or {}).get("escales") or []:
        for v in escale.get("words") or []:
            add(v["term"], "f")
    return need


def clip_name(text: str, voice_id: str) -> str:
    """Nom de fichier stable : il ne change pas tant que le texte ne change pas.

    SHA-256 plutôt que SHA-1 : l'empreinte ne sert qu'à nommer un fichier, mais
    autant ne pas laisser traîner un algorithme cassé dans le dépôt.
    """
    digest = hashlib.sha256(f"{voice_id}|{text}".encode("utf-8")).hexdigest()[:16]
    return f"{digest}.mp3"


ATTEMPT_TIMEOUT = 45      # secondes : au-delà, la connexion est pendue


class Postponed(Exception):
    """La limite de temps est atteinte : le clip est reporté, pas raté.

    La distinction compte : un report est normal et se rattrape à l'exécution
    suivante, un échec signale un vrai problème et doit faire sortir en erreur.
    """


async def synth(text: str, voice_id: str, rate: str, out: Path,
                tries: int = 3, deadline: float | None = None) -> None:
    """Enregistre une phrase, avec des reprises mais sans jamais s'éterniser.

    Une connexion pendue ne remonte aucune erreur : sans limite par tentative,
    un seul clip peut bloquer toute la publication. Et passé la limite globale,
    on ne retente plus — le clip sera repris à la prochaine exécution.
    """
    import edge_tts

    last = None
    for attempt in range(tries):
        try:
            tmp = out.with_suffix(".part")
            await asyncio.wait_for(
                edge_tts.Communicate(text, voice_id, rate=rate).save(str(tmp)),
                timeout=ATTEMPT_TIMEOUT)
            if tmp.stat().st_size < 500:      # un fichier vide = échec silencieux
                raise RuntimeError("fichier audio vide")
            tmp.replace(out)
            return
        except asyncio.TimeoutError:
            last = RuntimeError(f"pas de réponse en {ATTEMPT_TIMEOUT} s")
            out.with_suffix(".part").unlink(missing_ok=True)
        except Exception as exc:              # réseau instable : on retente
            last = exc
            out.with_suffix(".part").unlink(missing_ok=True)
        if deadline and time.monotonic() > deadline:
            # On reporte, mais on garde la cause : sans elle, un service
            # injoignable ressemblerait à un simple manque de temps.
            raise Postponed(f"« {text} » : {last}")
        await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"« {text} » : {last}")


async def build_language(course: dict, force: bool, prune: bool,
                         deadline_minutes: float = 0) -> int:
    voices = voices_for(course)
    rate = course.get("speech_rate", "-10%")
    outdir = AUDIO / course["code"]
    outdir.mkdir(parents=True, exist_ok=True)

    need = wanted_clips(course)
    clips: dict[str, dict[str, str]] = {}
    todo: dict[str, tuple[str, str, Path]] = {}
    for text, wanted in need.items():
        for voice in sorted(wanted):
            voice_id = voices.get(voice) or next(iter(voices.values()))
            name = clip_name(text, voice_id)
            clips.setdefault(text, {})[voice] = name
            target = outdir / name
            # Deux entrées peuvent viser le même fichier (même texte, même voix
            # pour `f` et `m`) : une seule tâche, sinon deux coroutines écrivent
            # dans le même .part en même temps.
            if (force or not target.exists()) and name not in todo:
                todo[name] = (text, voice_id, target)

    print(f'{course["name_fr"]} : {len(need)} textes, {len(todo)} à enregistrer '
          f'({", ".join(sorted(set(voices.values())))})')

    def write_manifest() -> int:
        """Écrit le manifeste des enregistrements **réellement présents**.

        Il est écrit même quand une partie a échoué : sinon un seul clip raté
        ferait perdre les centaines d'autres et le site publierait sans aucun
        son. À l'inverse, y lister un fichier absent ferait croire au site
        qu'il a une voix alors qu'il n'en a pas : on ne garde donc que ce qui
        existe sur le disque, et le reste est rattrapé à la relance.
        """
        present = {}
        for text, by_voice in clips.items():
            kept = {v: name for v, name in by_voice.items() if (outdir / name).exists()}
            if kept:
                present[text] = kept
        manifest = {"language": course["code"], "voices": voices,
                    "rate": rate, "clips": present}
        (outdir / "index.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True),
            encoding="utf-8")
        return len(present)

    if todo:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            raise SystemExit(
                "edge-tts n'est pas installé. Il produit les voix réelles :\n"
                "  python3 -m pip install -r requirements-audio.txt\n"
                "Sans lui, le site fonctionne mais s'appuie sur la voix du navigateur.")

        sem = asyncio.Semaphore(4)     # rester poli avec le service
        failures: list[str] = []
        skipped = 0
        last_error = ""
        deadline = time.monotonic() + deadline_minutes * 60 if deadline_minutes else None

        async def one(text: str, voice_id: str, target: Path) -> None:
            nonlocal skipped, last_error
            if deadline and time.monotonic() > deadline:
                skipped += 1
                return
            async with sem:
                try:
                    await synth(text, voice_id, rate, target, deadline=deadline)
                    print(f"  ✓ {text[:52]}")
                except Postponed as exc:
                    skipped += 1
                    last_error = str(exc)
                except Exception as exc:
                    failures.append(str(exc))
                    print(f"  ✗ {exc}")

        await asyncio.gather(*(one(*t) for t in todo.values()))
        if skipped:
            print(f"\n⏱  Limite de {deadline_minutes} min atteinte : {skipped} "
                  f"enregistrement(s) reportés. Ils seront produits à la prochaine "
                  f"exécution — les autres sont conservés.")
        # Un lot entièrement reporté sans qu'un seul fichier n'existe n'est pas
        # un manque de temps : c'est une panne. Le dire, sinon la publication
        # part sans son et personne ne sait pourquoi.
        if skipped and not any((outdir / n).exists()
                               for clip in clips.values() for n in clip.values()):
            write_manifest()
            raise SystemExit(
                f"\nAucun enregistrement n'a pu être produit. Dernière erreur :\n"
                f"  {last_error or 'inconnue'}\n"
                "Vérifiez l'accès réseau au service de synthèse avant de relancer.")
        if failures:
            kept = write_manifest()
            raise SystemExit(
                f"\n{len(failures)} enregistrement(s) sur {len(todo)} ont échoué ; "
                f"{kept} textes restent disponibles. Causes habituelles :\n"
                "  — pas d'accès réseau vers le service de synthèse ;\n"
                "  — service momentanément indisponible : relancer « make audio » "
                "reprend là où ça s'est arrêté.")

    kept = write_manifest()
    print(f"  {kept} textes disponibles dans {outdir.relative_to(ROOT)}/")

    if prune:
        # `clips` décrit tout ce qui est attendu, y compris les enregistrements
        # reportés : on ne supprime donc jamais un fichier encore utile.
        keep = {name for clip in clips.values() for name in clip.values()}
        for f in outdir.glob("*.mp3"):
            if f.name not in keep:
                f.unlink()
                print(f"  – {f.name} (plus utilisé)")
    return len(todo)


def main() -> None:
    ap = argparse.ArgumentParser(description="Produit les enregistrements du cours.")
    ap.add_argument("--lang", help="ne traiter qu'une langue (pt, ar…)")
    ap.add_argument("--force", action="store_true", help="refaire même les fichiers existants")
    ap.add_argument("--no-prune", action="store_true",
                    help="garder les fichiers qui ne correspondent plus à aucun texte")
    ap.add_argument("--deadline-minutes", type=float, default=0, metavar="N",
                    help="arrêter d'enregistrer après N minutes et garder ce qui est "
                         "fait ; le reste est produit à la prochaine exécution")
    args = ap.parse_args()

    langs = [c for c in load_all() if not args.lang or c["code"] == args.lang]
    if not langs:
        raise SystemExit(f"Langue « {args.lang} » introuvable dans content/.")

    total = 0
    for course in langs:
        total += asyncio.run(build_language(course, args.force, not args.no_prune,
                                            args.deadline_minutes))

    print(f"\n{total} nouveaux fichiers. Relancez « make build » pour que le site "
          f"les prenne en compte." if total else "\nTout était déjà à jour.")


if __name__ == "__main__":
    main()
