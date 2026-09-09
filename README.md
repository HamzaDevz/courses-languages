# Les langues à la maison

Cours de langues pour les enfants (3-10 ans), en français.
Première langue : **le portugais du Portugal**. L'arabe est prévu ensuite.

Le contenu est écrit **une seule fois** en YAML, puis généré en trois supports :

| Support | Où | Pour quoi |
|---|---|---|
| **Site web** | `site/` | écouter la prononciation, réviser avec les flashcards |
| **Fiches A4** | `print/` puis `pdf/` | fiche de cours, activités, cartes à découper |
| **Flashcards** | `exports/anki-*.csv` | révision espacée dans Anki |

## Démarrer

```bash
make install     # installe PyYAML (seule dépendance)
make serve       # génère tout et ouvre http://localhost:8000
make pdf         # fabrique les PDF imprimables (nécessite Chrome/Chromium)
```

Sans Chromium : ouvrir `print/pt/cahier-complet.html` dans un navigateur puis
Ctrl+P → « Enregistrer au format PDF ». La mise en page A4 est déjà prête.

## Ce qu'il y a aujourd'hui

**Portugais — 6 unités, 100 mots et phrases**

1. `Olá!` — saluer, remercier, dire son nom
2. `As cores` — les couleurs et l'accord
3. `Os números` — compter jusqu'à 10 (20 pour les grands), dire son âge
4. `A família` — les membres de la famille, *o* / *a*
5. `Os animais` — les animaux, *gosto de…*, le pluriel
6. `À mesa` — les aliments, *tenho fome*, demander poliment

Chaque unité contient : le vocabulaire avec prononciation, des phrases utiles,
les points à retenir, et **quatre activités** — deux pour les 3-6 ans (jeux,
oral, mime) et deux pour les 7-10 ans (écrit, règles, production).

## Écrire du contenu

Tout se passe dans `content/`, un fichier YAML par unité. Le format est décrit
dans **[docs/SCHEMA.md](docs/SCHEMA.md)**.

```bash
cp -r content/_template content/ar   # le gabarit est déjà réglé pour l'arabe
make build
```

## La méthode

Le rythme conseillé, ce qui marche et ce qu'on évite : **[docs/PEDAGOGIE.md](docs/PEDAGOGIE.md)**.
En résumé : 10 minutes par jour valent mieux qu'une heure le dimanche, l'audio
avant l'écrit, et une unité par semaine tant que les objectifs ne sont pas tenus.

## Organisation du dépôt

```
content/         le cours (source unique, versionnée)
scripts/build.py génère site/ print/ exports/
scripts/pdf.py   convertit print/ en PDF
assets/audio/    enregistrements réels (optionnel — le site parle déjà seul)
docs/            schéma du contenu et méthode pédagogique
```

Les dossiers `site/`, `print/`, `pdf/` et `exports/` sont générés et ignorés par git.
