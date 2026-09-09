# Format du contenu

Tout le cours vit dans `content/`. Rien d'autre n'est à modifier pour ajouter
du contenu : le site, les fiches imprimables et les flashcards sont générés.

```
content/
  _template/          gabarit (ignoré par le build, dossiers en "_")
  pt/
    course.yaml       métadonnées de la langue + boîte à outils
    program.yaml      le programme : années, périodes, semaines
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
| `voices` | `{f, m}` — voix utilisées par `scripts/audio.py` |
| `speech_rate` | vitesse des enregistrements (`"-10%"` par défaut) |
| `toolkit` | la boîte à outils de la discussion (voir plus bas) |

## Une unité

| Champ | Rôle |
|---|---|
| `id` | identifiant, sert de nom de fichier HTML |
| `order` | ordre d'affichage (continu sur tout le cours : 1 → 30) |
| `year` | année du programme (1, 2, 3…). Défaut : 1 |
| `title` / `title_fr` | titre dans la langue / en français |
| `goal_fr` | objectif en une phrase |
| `can_do_fr` | liste de « je sais… » — c'est le critère pour passer à la suite |
| `duration_min` | durée visée de la séance |
| `vocab` | liste de mots |
| `phrases` | liste de phrases (même format que `vocab`) |
| `dialogue` | **la scène de l'unité** : c'est par là qu'on commence |
| `comprehension` | questions en français pour vérifier qu'on a compris l'ensemble |
| `qa` | « on me demande / je réponds » — le cœur de la conversation |
| `notes_fr` | explications, `**gras**` accepté |
| `activities` | liste d'activités |
| `reemploi_fr` | ce qu'on utilise dans la vraie vie cette semaine |

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

### `dialogue` — la scène

C'est la partie la plus importante d'une unité : l'enfant entend une discussion
**entière** avant qu'on démonte les mots. Sur le site, elle se lit toute seule
(une voix par personnage), le français se masque, et le bouton « Je joue X »
efface les répliques d'un rôle pour que l'enfant les produise lui-même.

```yaml
dialogue:
  title_fr: "Deux enfants se rencontrent"
  context_fr: "Le matin, devant l'école."       # facultatif
  lines:
    - { who: "Ana",   term: "Olá!", fr: "Salut !", phon: "o-LA" }
    - { who: "Tomás", term: "Bom dia!", fr: "Bonjour !", phon: "bon DI-a" }
```

`who` est le nom du personnage : le premier prend la voix féminine des
enregistrements, le deuxième la voix masculine. Six à douze répliques suffisent.

### `comprehension` — est-ce que j'ai compris ?

```yaml
comprehension:
  - q_fr: "Comment s'appellent les deux enfants ?"
    a_fr: "Ana et Tomás."
```

Question **en français**, à poser après deux écoutes, sans lire. La réponse est
masquée sur le site (clic pour l'afficher) et imprimée en petit sur la fiche.

### `qa` — on me demande, je réponds

Savoir un mot ne sert à rien si l'enfant ne sait pas quoi répondre quand on le
lui demande. Chaque question a **plusieurs** réponses possibles : l'enfant
choisit celle qui est vraie pour lui.

```yaml
qa:
  - question: { term: "Como te chamas?", fr: "Comment t'appelles-tu ?", phon: "KO-mou te CHA-mach" }
    answers:
      - { term: "Chamo-me Léo.", fr: "Je m'appelle Léo.", phon: "CHA-mou-me Léo" }
      - { term: "O meu nome é Ana.", fr: "Mon nom est Ana.", phon: "ou méou NO-me è A-na" }
```

Ces couples alimentent aussi l'« entraînement à répondre » du site (la question
sort à l'oral, l'enfant répond à voix haute, puis vérifie) et l'export Anki.

### Une activité

```yaml
- level: petits           # doit correspondre à un id de `levels`
  type: jeu               # jeu | chanson | exercice | production | dialogue
  title_fr: "Le réveil et le dodo"
  steps_fr:
    - "Étape 1."
```

### `toolkit` dans `course.yaml`

Les phrases de dépannage — celles qui permettent de **rester** dans la
discussion. Elles ne sont rattachées à aucune unité et se révisent toute
l'année. Le build en fait une page du site et une feuille à imprimer.

```yaml
toolkit:
  - title_fr: "Quand je n'ai pas compris"
    intro_fr: "À savoir par cœur avant tout le reste."
    items:
      - { term: "Não percebi.", fr: "Je n'ai pas compris.", phon: "nan-ou per-se-BI" }
```

## `program.yaml` — le programme de l'année

Sans ce fichier le cours fonctionne, mais il n'y a plus de plan : les unités
sont une liste, pas une progression. Le build **vérifie que chaque unité citée
existe** et refuse de construire sinon.

```yaml
intro_fr: >
  Trois années, dix unités par année, une unité toutes les trois semaines.
rhythm_fr:                  # la semaine type
  - { day_fr: "Lundi", what_fr: "**Le dialogue** : l'écouter deux fois.", min: 12 }
cycle_fr:                   # comment une unité se traite sur trois semaines
  - { label_fr: "Semaine 1 — je comprends", what_fr: "Écouter, comprendre l'ensemble." }
years:
  - year: 1
    label_fr: "Année 1 — Je comprends qu'on me parle et je réponds"
    age_fr: "3-6 ans : tout à l'oral. 7-10 ans : oral + écrit."
    goal_fr: "Ce que l'enfant sait faire de nouveau à la fin de l'année."
    can_do_fr: ["Je salue, je dis mon nom, mon âge…"]
    periods:
      - label_fr: "Période 1 — Qui je suis"
        weeks_fr: "semaines 1 à 7"
        units: [01-ola, 02-cores]
        focus_fr: "Saluer, se présenter, nommer les couleurs."
        milestone_fr: "L'enfant répond à *Olá, como te chamas?* sans aide."
    evaluation_fr: ["Comment vérifier, sans faire d'examen."]
```

## Ajouter une langue

```bash
cp -r content/_template content/ar     # puis éditer course.yaml
make build
```

Le gabarit `content/_template/` est déjà pré-rempli pour l'arabe (RTL,
translittération, `speech_lang: ar-SA`).

## L'audio

Le son suit deux règles, dans cet ordre :

1. **Un enregistrement réel existe** → c'est lui qui est joué.
   `make audio` produit un MP3 par mot, par réplique et par réponse, dans une
   voix neuronale de la variante enseignée (deux voix, une par personnage des
   dialogues). Les fichiers vont dans `assets/audio/<langue>/`, avec un
   manifeste `index.json` que le build lit tout seul.
2. **Sinon**, la voix de synthèse du navigateur — **mais uniquement si
   l'appareil possède une voix de cette langue**. Faire lire du portugais par
   une voix française donne une prononciation fausse : dans ce cas le site
   ne lit rien et affiche comment installer une vraie voix (`site/voix.html`).

Pour une **voix humaine**, remplacer un `.mp3` par son propre enregistrement en
gardant le même nom de fichier : le site jouera celui-là, sans rien changer au
code. Le nom se lit dans `assets/audio/<langue>/index.json`.

```bash
make install-audio   # une fois : installe edge-tts
make audio           # produit ce qui manque, ne refait pas l'existant
```
