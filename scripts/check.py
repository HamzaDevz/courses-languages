#!/usr/bin/env python3
"""Vérifie le contenu et ce que le build en a produit.

`build.py` s'arrête déjà sur ce qui l'empêche de construire : un YAML cassé, un
champ obligatoire absent, une unité citée par le programme mais inexistante.
Il ne dit rien, en revanche, de ce qui construit sans erreur mais donne une
page fausse — un niveau mal orthographié dans une activité, une question sans
réponse, une page qui a cessé d'être écrite. C'est ce que ce script attrape.

    python3 scripts/check.py        (après « make build »)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from build import CONTENT, EXPORTS, PRINT, SITE, entries, load_all  # noqa: E402

problems: list[str] = []


def fail(where: str, what: str) -> None:
    problems.append(f"{where} : {what}")


def check_content(course: dict) -> None:
    code = course["code"]
    levels = {lv["id"] for lv in course.get("levels", [])}
    for unit in course["units"]:
        where = f"content/{code}/units/{unit['id']}.yaml"
        for v in entries(unit):
            if not v.get("term") or not v.get("fr"):
                fail(where, f"le mot « {v.get('term', '?')} » n'a pas de terme ou de traduction")
            if v.get("level") and v["level"] not in levels:
                fail(where, f"le mot « {v['term']} » vise le niveau « {v['level']} », "
                            f"qui n'existe pas dans course.yaml")
        for item in unit.get("qa") or []:
            q = (item.get("question") or {}).get("term", "?")
            if not item.get("answers"):
                fail(where, f"la question « {q} » n'a aucune réponse : rien à entraîner")
        for a in unit["activities"]:
            title = a.get("title_fr", "?")
            # Un niveau mal orthographié construit sans erreur, mais l'étiquette
            # sort vide sur la fiche et l'activité n'appartient à aucun parcours.
            if a.get("level") not in levels:
                fail(where, f"l'activité « {title} » vise le niveau « {a.get('level')} », "
                            f"qui n'existe pas dans course.yaml")
            if not a.get("steps_fr"):
                fail(where, f"l'activité « {title} » n'a aucune étape")
        # Le parcours des petits passe quatre à sept semaines sur une unité :
        # deux activités ne la tiennent pas.
        petits = sum(1 for a in unit["activities"] if a.get("level") == "petits")
        if petits < 3:
            fail(where, f"seulement {petits} activités pour les petits — il en faut au moins 3")
    for group in course.get("toolkit") or []:
        for v in group.get("items", []):
            if not v.get("term") or not v.get("fr"):
                fail(f"content/{code}/course.yaml", "une phrase de la boîte à outils est incomplète")
    for group in (course.get("games") or {}).get("groups") or []:
        for game in group.get("games") or []:
            if not game.get("how_fr"):
                fail(f"content/{code}/games.yaml",
                     f"le jeu « {game.get('title_fr', '?')} » n'explique pas comment on y joue")


def check_built(course: dict) -> None:
    """Une page qui a cessé d'être écrite ne casse rien : elle disparaît."""
    code = course["code"]
    expected = [SITE / "index.html", SITE / code / "index.html",
                PRINT / code / "cahier-complet.html", EXPORTS / f"anki-{code}.csv",
                # L'appli installable : sans ces trois-là, le site continue de
                # s'afficher mais ne s'installe plus et ne marche plus hors
                # connexion — une perte qui ne fait échouer aucune construction.
                SITE / "manifest.webmanifest", SITE / "sw.js",
                SITE / "icons" / "icon-512.png"]
    for key, name in (("program", "programme"), ("toolkit", "boite-a-outils"),
                      ("culture", "passeport"), ("resources", "ressources"),
                      ("games", "boite-a-jeux")):
        if course.get(key):
            expected.append(SITE / code / f"{name}.html")
    for unit in course["units"]:
        expected.append(SITE / code / f'{unit["id"]}.html')
        expected.append(PRINT / code / f'{unit["id"]}.html')
    for path in expected:
        if not path.exists():
            fail("build", f"{path.relative_to(Path(__file__).parent.parent)} n'a pas été produit")


def check_audio(courses: list[dict]) -> None:
    """audio.py n'est lancé qu'à la publication, et sans bloquer si elle échoue.

    Une erreur dedans passerait donc inaperçue jusqu'à ce que le site perde ses
    voix. On calcule la liste des clips (sans réseau, rien n'est enregistré).
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("audio", Path(__file__).parent / "audio.py")
    audio = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(audio)
        for course in courses:
            if not audio.wanted_clips(course):
                fail("scripts/audio.py", f'aucun texte à enregistrer pour « {course["code"]} »')
    except Exception as exc:                                   # noqa: BLE001
        fail("scripts/audio.py", f"ne tourne pas : {exc.__class__.__name__} — {exc}")


def main() -> None:
    if not CONTENT.exists():
        raise SystemExit("Aucun dossier content/ : rien à vérifier.")
    courses = load_all()
    for course in courses:
        check_content(course)
        if SITE.exists():
            check_built(course)
    check_audio(courses)

    if not SITE.exists():
        print("site/ absent : les pages produites n'ont pas été vérifiées "
              "(lancez « make build » d'abord).")
    if problems:
        print(f"\n{len(problems)} problème(s) :\n")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit(1)
    n_units = sum(len(c["units"]) for c in courses)
    n_act = sum(len(u["activities"]) for c in courses for u in c["units"])
    print(f"OK — {len(courses)} langue(s), {n_units} unités, {n_act} activités, "
          f"pages et exports en place.")


if __name__ == "__main__":
    main()
