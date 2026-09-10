# Les langues à la maison

Cours de langues pour les enfants (3-10 ans), en français.
Première langue : **le portugais du Portugal**. L'arabe est prévu ensuite.

Le but n'est pas d'apprendre des listes de mots : c'est que l'enfant
**comprenne une discussion entière et sache y répondre**. Chaque unité part donc
d'un dialogue joué à deux voix, vérifie qu'il a été compris, puis entraîne les
réponses possibles.

Le tout suit un **vrai programme** : deux parcours selon l'âge, trois années
chacun, des niveaux CECRL annoncés, un passeport culturel à tamponner et une
liste de livres et de chansons. Le document à donner à un professeur de langue
pour qu'il juge la cohérence est **[docs/REFERENTIEL.md](docs/REFERENTIEL.md)**.

Le contenu est écrit **une seule fois** en YAML, puis généré en trois supports :

| Support | Où | Pour quoi |
|---|---|---|
| **Site web** | `site/` | écouter les dialogues, jouer les rôles, s'entraîner à répondre |
| **Fiches A4** | `print/` puis `pdf/` | programme, cours, dialogue + Q/R, activités, cartes à découper |
| **Flashcards** | `exports/anki-*.csv` | révision espacée dans Anki, questions/réponses comprises |
| **Enregistrements** | `assets/audio/` | de vraies voix, produites par `make audio` |

## Démarrer

```bash
make install     # installe PyYAML (seule dépendance pour construire le site)
make serve       # génère tout et ouvre http://localhost:8000
make audio       # enregistre les vraies voix portugaises (voir « Le son »)
make pdf         # fabrique les PDF imprimables (nécessite Chrome/Chromium)
```

Sans Chromium : ouvrir `print/pt/cahier-complet.html` dans un navigateur puis
Ctrl+P → « Enregistrer au format PDF ». La mise en page A4 est déjà prête.

## Le programme

**Portugais — 30 unités, 30 dialogues, 90 questions à savoir répondre,
12 escales culturelles.**

Deux parcours, parce qu'un enfant de 4 ans et un enfant de 9 ans n'apprennent
pas de la même façon :

| | **Parcours A — les petits** | **Parcours B — les grands** |
|---|---|---|
| Âge | 3-6 ans | 7-10 ans |
| Séance | 8-10 min, 4-5 fois/semaine | 12-20 min, 5 fois/semaine |
| Rythme | une unité en **4 à 7 semaines** | une unité en 3 semaines |
| Écrit | **aucun**, tout par le jeu | dès l'année 1 |
| Sur 3 ans | 15 unités | 30 unités |
| Niveau visé | pré-A1 → A1.1 oral | A1.1 → **A2** |

Une **passerelle** relie les deux : l'enfant qui sort du parcours A refait les
unités 1 à 10 en dix semaines, avec l'écrit, puis rejoint le parcours B.

Le contenu, lui, est commun — trois années qui vont de « je réponds » à
« je discute » :

| Année | Ce qu'on vise | Unités |
|---|---|---|
| **1** | Comprendre qu'on me parle et **répondre** — six répliques sur moi | `Olá!` · `As cores` · `Os números` · `A família` · `Os animais` · `À mesa` · `O corpo` · `Em casa` · `Vamos brincar!` · `Vamos conversar!` |
| **2** | **Raconter mon quotidien** et poser des questions — dix répliques | `A roupa` · `O tempo` · `Os dias e as horas` · `Na escola` · `Na cidade` · `Às compras` · `Como me sinto` · `Vamos passear` · `Ao telefone` · `Uma conversa a sério` |
| **3** | **Raconter, donner son avis, discuter** — cinq minutes libres | `Ontem` · `Amanhã` · `Na minha opinião` · `Como é?` · `Era uma vez` · `No restaurante` · `No médico` · `Em viagem` · `Vamos combinar?` · `Falar de tudo` |

Cinq périodes par année, un bilan concret à la fin de chacune, et le niveau
CECRL visé annoncé pour chaque année. Le plan complet est sur la page
**Programme** du site, et à imprimer pour l'afficher au mur.

Le niveau A2 en fin de parcours B suppose que **la pratique réelle suive** ;
sans interlocuteur ni séjour, le résultat honnête est un A1+ solide. C'est écrit
tel quel dans le programme.

### Ce que contient une unité

1. **Le dialogue** — une scène de 6 à 14 répliques, jouée à deux voix. Le site
   la lit en entier, masque le français, et le bouton « Je joue Ana » efface les
   répliques d'un rôle pour que l'enfant les dise lui-même.
2. **Est-ce que j'ai compris ?** — des questions en français sur l'ensemble,
   réponses masquées.
3. **Le vocabulaire et les phrases**, avec prononciation approchée et audio.
4. **On me demande, je réponds** — chaque question avec **plusieurs** réponses
   possibles, plus un entraînement où la question sort à l'oral.
5. **Les points à retenir** et **quatre à cinq activités** — pour les 3-6 ans
   (jeux, oral, mime) et pour les 7-10 ans (écrit, règles, production).
6. **Cette semaine dans la vraie vie** — ce qui sort du cours.

### Le voyage culturel

Une langue sans son pays reste un exercice. Chaque unité porte un **repère
culturel** (pourquoi le coq de Barcelos est partout, pourquoi lundi se dit
« deuxième jour », pourquoi le couvert du restaurant est payant), et un
**passeport culturel** propose douze escales — Lisbonne, le fado, les azulejos,
les Santos Populares, les Découvertes, Madère et les Açores… — chacune avec une
chose à voir, à goûter, à écouter, et **une mission à faire pour de vrai**.

Le passeport s'imprime : une case par escale, qu'on tamponne quand la mission
est faite. Pas quand l'escale est lue.

### La pratique, avant tout le reste

Le programme organise, il ne remplace pas l'usage — **une heure de vraie
conversation vaut dix fiches**. La page Programme détaille six façons d'en
trouver : un interlocuteur réel (proche, association, cours du réseau Instituto
Camões), l'heure portugaise hebdomadaire à la maison, sortir commander soi-même,
les écrans **en portugais du Portugal** suivis de deux questions, un
correspondant, et le voyage.

Et **[une liste de livres, chansons et dessins animés](content/pt/resources.yaml)**
par âge, avec pourquoi chacun et où le trouver — publiée aussi sur le site.

### La boîte à outils

Une page à part, à afficher près de la table : *não percebi*, *outra vez, por
favor*, *como se diz… em português?*, *e tu?* Ce sont les phrases qui permettent
de **rester** dans la conversation au lieu de se taire — et donc de continuer à
apprendre.

## Le son

Les boutons 🔊 jouent, dans cet ordre :

1. **Un vrai enregistrement** dans la variante enseignée, produit par
   `make audio` (une voix féminine et une voix masculine, ce qui donne aux
   dialogues deux personnages distincts). Le site publié en contient
   automatiquement : le workflow GitHub les produit à chaque déploiement.
2. **Sinon** la voix du système — **seulement si l'appareil a une voix de cette
   langue**. Sinon le site **ne lit rien** et explique comment en installer une :
   faire lire du portugais par une voix française apprend une prononciation
   fausse, ce qui est pire que le silence.

```bash
make install-audio   # une fois : installe edge-tts
make audio           # produit ce qui manque (relancer est rapide et sans risque)
```

La première production prend environ six minutes pour un millier de phrases.
Le workflow GitHub garde les fichiers en cache d'une publication à l'autre :
seuls les textes modifiés sont réenregistrés.

Pour une **voix humaine** : remplacer un fichier de `assets/audio/pt/` par son
propre enregistrement, en gardant le même nom. Le site jouera celui-là.

## Le site en ligne

Le site est publié automatiquement sur GitHub Pages à chaque push sur `main`,
par le workflow `.github/workflows/pages.yml` :

**https://hamzadevz.github.io/courses-languages/**

Il embarque tout : le programme, les unités, la boîte à outils, les
enregistrements (`/audio/`), les fiches à imprimer (`/print/`), les PDF
(`/pdf/`) et l'export Anki (`/exports/`). Rien à installer côté enfant, une
tablette et un navigateur suffisent.

Activation, une seule fois : dans le dépôt, **Settings → Pages → Source :
GitHub Actions**.

### L'installer comme une application

Le site est une *application web installable* : il s'ajoute à l'écran d'accueil
comme n'importe quelle appli, s'ouvre en plein écran (sans barre d'adresse) et
continue de fonctionner sans réseau.

* **Android (Chrome)** : ouvrir le site, menu ⋮ → *Installer l'application*.
* **iPhone / iPad (Safari)** : bouton Partager → *Sur l'écran d'accueil*.
* **Ordinateur (Chrome, Edge)** : l'icône d'installation dans la barre d'adresse.

Hors connexion, toutes les pages déjà publiées restent lisibles ; les
enregistrements se gardent au fur et à mesure qu'ils sont écoutés (les mille
fichiers ne sont pas téléchargés d'office, ce serait des dizaines de Mo imposés
à l'installation).

Le manifeste, les icônes et le service worker sont générés par
`scripts/webapp.py` à chaque `make build` — rien de binaire n'est versionné.

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
avant l'écrit, le dialogue avant les mots, et on ne passe pas à l'unité suivante
tant que les « je sais… » ne sont pas tenus.

## Organisation du dépôt

```
content/pt/course.yaml    la langue + la boîte à outils
content/pt/program.yaml   le programme : parcours par âge, périodes, pratique
content/pt/culture.yaml   le passeport culturel : 12 escales, 12 missions
content/pt/resources.yaml livres, chansons, écrans, outils
content/pt/units/         une unité = un fichier (dialogue, Q/R, activités)
scripts/build.py          génère site/ print/ exports/
scripts/webapp.py         l'appli web : manifeste, icônes, service worker
scripts/audio.py          produit les enregistrements (assets/audio/)
scripts/pdf.py            convertit print/ en PDF
docs/REFERENTIEL.md       niveaux CECRL, progression, grilles d'évaluation
docs/PEDAGOGIE.md         la méthode, parcours par parcours
docs/SCHEMA.md            le format du contenu
```

Les dossiers `site/`, `print/`, `pdf/` et `exports/` sont générés et ignorés par git.
