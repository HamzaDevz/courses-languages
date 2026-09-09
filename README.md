# Les langues à la maison

Cours de langues pour les enfants (3-10 ans), en français.
Première langue : **le portugais du Portugal**. L'arabe est prévu ensuite.

Le but n'est pas d'apprendre des listes de mots : c'est que l'enfant
**comprenne une discussion entière et sache y répondre**. Chaque unité part donc
d'un dialogue joué à deux voix, vérifie qu'il a été compris, puis entraîne les
réponses possibles — et le tout suit un **programme sur trois ans**.

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

**Portugais — 3 années, 30 unités, 30 dialogues, 90 questions à savoir répondre.**

| Année | Ce qu'on vise | Unités |
|---|---|---|
| **1** | Comprendre qu'on me parle et **répondre** — six répliques sur moi | `Olá!` · `As cores` · `Os números` · `A família` · `Os animais` · `À mesa` · `O corpo` · `Em casa` · `Vamos brincar!` · `Vamos conversar!` |
| **2** | **Raconter mon quotidien** et poser des questions — dix répliques | `A roupa` · `O tempo` · `Os dias e as horas` · `Na escola` · `Na cidade` · `Às compras` · `Como me sinto` · `Vamos passear` · `Ao telefone` · `Uma conversa a sério` |
| **3** | **Raconter, donner son avis, discuter** — cinq minutes libres | `Ontem` · `Amanhã` · `Na minha opinião` · `Como é?` · `Era uma vez` · `No restaurante` · `No médico` · `Em viagem` · `Vamos combinar?` · `Falar de tudo` |

Dix unités par année, **une unité toutes les trois semaines** (je comprends /
je réponds / je parle), cinq périodes, un bilan concret à la fin de chacune.
Le plan complet est sur la page **Programme** du site, et à imprimer pour
l'afficher au mur.

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
content/pt/program.yaml   le programme : années, périodes, semaines
content/pt/units/         une unité = un fichier (dialogue, Q/R, activités)
scripts/build.py          génère site/ print/ exports/
scripts/audio.py          produit les enregistrements (assets/audio/)
scripts/pdf.py            convertit print/ en PDF
docs/                     schéma du contenu et méthode pédagogique
```

Les dossiers `site/`, `print/`, `pdf/` et `exports/` sont générés et ignorés par git.
