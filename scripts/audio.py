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
    return need


def clip_name(text: str, voice_id: str) -> str:
    """Nom de fichier stable : il ne change pas tant que le texte ne change pas."""
    digest = hashlib.sha1(f"{voice_id}|{text}".encode("utf-8")).hexdigest()[:16]
    return f"{digest}.mp3"


async def synth(text: str, voice_id: str, rate: str, out: Path, tries: int = 3) -> None:
    import edge_tts

    last = None
    for attempt in range(tries):
        try:
            tmp = out.with_suffix(".part")
            await edge_tts.Communicate(text, voice_id, rate=rate).save(str(tmp))
            if tmp.stat().st_size < 500:      # un fichier vide = échec silencieux
                raise RuntimeError("fichier audio vide")
            tmp.replace(out)
            return
        except Exception as exc:              # réseau instable : on retente
            last = exc
            out.with_suffix(".part").unlink(missing_ok=True)
            await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"« {text} » : {last}")


async def build_language(course: dict, force: bool, prune: bool) -> int:
    voices = voices_for(course)
    rate = course.get("speech_rate", "-10%")
    outdir = AUDIO / course["code"]
    outdir.mkdir(parents=True, exist_ok=True)

    need = wanted_clips(course)
    clips: dict[str, dict[str, str]] = {}
    todo: list[tuple[str, str, Path]] = []
    for text, wanted in need.items():
        for voice in sorted(wanted):
            voice_id = voices.get(voice) or next(iter(voices.values()))
            name = clip_name(text, voice_id)
            clips.setdefault(text, {})[voice] = name
            target = outdir / name
            if force or not target.exists():
                todo.append((text, voice_id, target))

    print(f'{course["name_fr"]} : {len(need)} textes, {len(todo)} à enregistrer '
          f'({", ".join(sorted(set(voices.values())))})')

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

        async def one(text: str, voice_id: str, target: Path) -> None:
            async with sem:
                try:
                    await synth(text, voice_id, rate, target)
                    print(f"  ✓ {text[:52]}")
                except Exception as exc:
                    failures.append(str(exc))
                    print(f"  ✗ {exc}")

        await asyncio.gather(*(one(*t) for t in todo))
        if failures:
            raise SystemExit(
                f"\n{len(failures)} enregistrement(s) ont échoué. Causes habituelles :\n"
                "  — pas d'accès réseau vers le service de synthèse ;\n"
                "  — service momentanément indisponible : relancer « make audio » "
                "reprend là où ça s'est arrêté.")

    manifest = {"language": course["code"], "voices": voices, "rate": rate, "clips": clips}
    (outdir / "index.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")

    if prune:
        keep = {n for c in clips.values() for n in c.values()}
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
    args = ap.parse_args()

    langs = [c for c in load_all() if not args.lang or c["code"] == args.lang]
    if not langs:
        raise SystemExit(f"Langue « {args.lang} » introuvable dans content/.")

    total = 0
    for course in langs:
        total += asyncio.run(build_language(course, args.force, not args.no_prune))

    print(f"\n{total} nouveaux fichiers. Relancez « make build » pour que le site "
          f"les prenne en compte." if total else "\nTout était déjà à jour.")


if __name__ == "__main__":
    main()
