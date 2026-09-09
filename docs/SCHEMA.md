# Format du contenu

Tout le cours vit dans `content/`. Rien d'autre n'est à modifier pour ajouter
du contenu : le site, les fiches imprimables et les flashcards sont générés.

```
content/
  _template/          gabarit (ignoré par le build, dossiers en "_")
  pt/
    course.yaml       métadonnées de la langue
    units/
      01-ola.yaml     une unité = un fichier
      02-cores.yaml
```

## `course.yaml`

| Champ | Rôle |
|---|---|
| `code` | code court, doit être le nom du dossier (`pt`, `ar`…) |
| `name` / `name_fr` | nom dans la langue / en français |
| `variant` / `variant_fr` | variante enseignée (PT-PT, MSA…) |
| `direction` | `ltr` ou `rtl` (arabe, hébreu) |
| `script` | `latin`, `arabic`… |
| `has_transliteration` | `true` → affiche la colonne translittération |
| `speech_lang` | code BCP-47 pour la synthèse vocale (`pt-PT`, `ar-SA`) |
| `note_fr` | note affichée en bas de la page de la langue |
| `levels` | liste `{id, label_fr, desc_fr}` — les niveaux d'âge |

## Une unité

| Champ | Rôle |
|---|---|
| `id` | identifiant, sert de nom de fichier HTML |
| `order` | ordre d'affichage |
| `title` / `title_fr` | titre dans la langue / en français |
| `goal_fr` | objectif en une phrase |
| `can_do_fr` | liste de « je sais… » — c'est le critère pour passer à la suite |
| `duration_min` | durée visée de la séance |
| `vocab` | liste de mots |
| `phrases` | liste de phrases (même format que `vocab`) |
| `notes_fr` | explications, `**gras**` accepté |
| `activities` | liste d'activités |

### Une entrée de `vocab` / `phrases`

```yaml
- term: "obrigado"        # le mot dans la langue (obligatoire)
  translit: "..."         # si has_transliteration: true
  fr: "merci"             # traduction française
  phon: "o-bri-GA-dou"    # prononciation approximative pour un francophone
  level: grands           # facultatif : réserve le mot à un niveau
```

Convention pour `phon` : syllabes séparées par des tirets, **SYLLABE ACCENTUÉE
en majuscules**. C'est une approximation destinée aux parents, pas de l'API.

### Une activité

```yaml
- level: petits           # doit correspondre à un id de `levels`
  type: jeu               # jeu | chanson | exercice | production
  title_fr: "Le réveil et le dodo"
  steps_fr:
    - "Étape 1."
```

## Ajouter une langue

```bash
cp -r content/_template content/ar     # puis éditer course.yaml
make build
```

Le gabarit `content/_template/` est déjà pré-rempli pour l'arabe (RTL,
translittération, `speech_lang: ar-SA`).

## Ajouter de l'audio enregistré

La lecture vocale actuelle utilise la voix du système via le navigateur
(`speechSynthesis`), sans aucun fichier à produire. Pour de vraies voix,
déposer les fichiers dans `assets/audio/<langue>/` et ajouter un champ
`audio: nom-du-fichier.mp3` à l'entrée — le champ est prévu dans le schéma
mais pas encore lu par le build.
