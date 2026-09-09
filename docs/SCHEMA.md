# Format du contenu

Tout le cours vit dans `content/`. Rien d'autre n'est à modifier pour ajouter
du contenu : le site, les fiches imprimables et les flashcards sont générés.

```
content/
  _template/          gabarit (ignoré par le build, dossiers en "_")
  pt/
    course.yaml       métadonnées de la langue + boîte à outils
    program.yaml      le programme : parcours par âge, périodes, semaines
    culture.yaml      le passeport culturel : escales et missions
    resources.yaml    livres, chansons, écrans à acheter ou emprunter
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
| `cefr` | niveau visé, affiché sous le titre (`A1.1`, `A1 → A1+`…) |
| `culture_fr` | un repère culturel, une ou deux phrases |
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

Un mot marqué `level:` s'affiche avec l'étiquette de ce niveau (« 7-10 ans ») :
le parcours des petits le saute, le parent le voit sans avoir à le chercher.
Le socle commun d'une unité — les mots **sans** `level` — ne dépasse jamais
douze.

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

## `program.yaml` — le programme

Sans ce fichier le cours fonctionne, mais il n'y a plus de plan : les unités
sont une liste, pas une progression. Le build **vérifie que chaque unité citée
existe** et refuse de construire sinon.

Un programme contient un ou plusieurs **parcours** (`tracks`). Un parcours = un
âge, avec son rythme, ses objectifs et son niveau visé. Les parcours partagent
les mêmes unités : c'est la vitesse et la profondeur qui changent, pas le
contenu.

```yaml
intro_fr: >
  Deux parcours selon l'âge, un seul contenu d'unités.
cefr_fr: >
  Le cadre de référence utilisé (CECRL…), affiché en tête du programme.
tracks:
  - id: petits
    label_fr: "Parcours A — Les petits (3-6 ans)"
    ages_fr: "3 à 6 ans, avant de savoir lire"
    cefr_fr: "pré-A1 puis A1.1 à l'oral"
    session_fr: "8 à 10 min, 4 à 5 fois par semaine"
    total_fr: "3 années, 15 unités"
    intro_fr: "Pourquoi ce parcours est fait ainsi."
    method_fr: ["Les règles propres à cet âge."]
    rhythm_fr:              # la semaine type de CE parcours
      - { day_fr: "Lundi", what_fr: "**Le dialogue** en fond, deux fois.", min: 5 }
    cycle_fr:               # comment CE parcours traite une unité
      - { label_fr: "Semaines 1-2 — j'entends", what_fr: "Zéro production demandée." }
    years:
      - year: 1
        label_fr: "Petits · Année 1 (3-4 ans) — J'écoute et je montre"
        cefr_fr: "pré-A1 : compréhension orale de consignes simples"
        age_fr: "3-4 ans"
        goal_fr: "Ce que l'enfant sait faire de nouveau à la fin de l'année."
        can_do_fr: ["Je réagis à *bom dia*…"]
        periods:
          - label_fr: "Période 1"
            weeks_fr: "semaines 1 à 7"
            units: [01-ola]          # liste vide = période de révision
            focus_fr: "Ce qu'on travaille."
            milestone_fr: "Le bilan de la période, vérifiable."
        evaluation_fr: ["Comment vérifier, sans faire d'examen."]
  - id: grands
    spine: true               # ce parcours numérote les années sur la liste des unités
    label_fr: "Parcours B — Les grands (7-10 ans)"
    years: [...]
bridge_fr: >
  Comment on passe d'un parcours à l'autre.
practice_fr:                  # la pratique réelle, hors du cours
  - title_fr: "Trouver un vrai interlocuteur"
    when_fr: "Dès l'année 1"
    steps_fr: ["…"]
```

`spine: true` désigne le parcours qui donne les titres d'années sur la page de
la langue. Un `program.yaml` écrit sans `tracks`, avec `years:` directement,
reste valide : il devient un parcours unique.

## `culture.yaml` — le passeport culturel

Facultatif. Douze escales environ, chacune avec une **mission** à faire pour de
vrai — c'est la mission qui donne le tampon, pas la lecture.

```yaml
title_fr: "Le passeport culturel"
intro_fr: >
  Une langue sans son pays reste un exercice.
escales:
  - label_fr: "Lisboa — la ville aux sept collines"
    when_fr: "Année 1, période 1"        # quand la placer
    intro_fr: "Une phrase de présentation."
    see_fr: "À voir."
    taste_fr: "À goûter."
    listen_fr: "À écouter."
    story_fr: "L'histoire ou la légende."
    know_fr: "À savoir."
    words:                                # même format que vocab, avec audio
      - { term: "o elétrico", fr: "le tramway", phon: "ou i-LÈ-tri-kou" }
    mission_fr: "Ce que l'enfant doit faire dans la vraie vie."
outro_fr: "Ce qu'on ajoute pour les plus grands."
```

## `resources.yaml` — livres, chansons et écrans

Facultatif. Ce qu'on achète, emprunte ou écoute autour du cours.

```yaml
title_fr: "Livres, chansons et écrans"
intro_fr: "…"
warning_fr: "Les précautions avant d'acheter (variante PT/BR, éditions)."
groups:
  - title_fr: "Pour les 3-6 ans — albums à lire à voix haute"
    intro_fr: "…"
    items:
      - title: "A Lagartinha Muito Comilona"
        author: "Eric Carle"
        kind_fr: "album illustré"
        age_fr: "3-6 ans"
        why_fr: "Pourquoi celui-là, et à quelle unité il se rattache."
        where_fr: "Où le trouver."
outro_fr: "S'il ne fallait garder que trois choses…"
```

Aucun ISBN, aucun prix : ils changent, et une référence fausse est pire que pas
de référence. Le champ `where_fr` dit où chercher, c'est suffisant.

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
