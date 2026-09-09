# Les enregistrements

Un dossier par langue (`pt/`, `ar/`), rempli par `make audio` :

```
assets/audio/pt/
  index.json          le manifeste : quel texte → quel fichier, quelle voix
  0a1b2c3d….mp3       un fichier par texte et par voix
```

Le nom des fichiers est une empreinte du texte et de la voix : il ne change pas
tant que le texte ne change pas, donc relancer `make audio` ne refait que ce qui
manque. Les fichiers devenus inutiles sont supprimés automatiquement (sauf avec
`--no-prune`).

## Pourquoi ce dossier existe

La synthèse vocale du navigateur n'est pas fiable : beaucoup d'appareils n'ont
aucune voix portugaise, et le texte est alors lu par une voix française — ce qui
apprend une prononciation fausse. Le site refuse de le faire. Ces
enregistrements, produits dans une voix neuronale de la variante enseignée,
règlent le problème pour tout le monde, y compris hors ligne.

## Mettre sa propre voix

Remplacer un `.mp3` par son propre enregistrement, **en gardant le même nom** :
le site jouera celui-là, sans rien changer au code. Pour retrouver le fichier
d'un mot, chercher le mot dans `index.json`.

## Faut-il les committer ?

Ce n'est pas obligatoire : le workflow GitHub les reproduit à chaque
publication. Les committer rend le site utilisable hors ligne et fige la
prononciation — c'est le bon choix dès qu'on y a mis de vraies voix humaines.
