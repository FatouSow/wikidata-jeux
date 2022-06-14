# Wikidata-jeux
## Présentation
Wikidata-jeux est un projet comportant trois jeux qui s'appuient sur le graphe de connaissances Wikidata.

Le projet est disponible avec ou sans interface utilisateur. Le fichier Interface_jeux_Flask.py contient les trois jeux implémentés intégrés à une interface utilisateur (Flask). Pour le lancer, il faut exécuter le fichier au niveau d'un terminal puis lancer http://127.0.0.1:5000/. Il est nécessaire de télécharger toutes les librairies Python nécessaires pour que le code puisse s'exécuter. Les dossiers static, template et ressources doivent appartenir au même répertoire que le fichier Interface_jeux_Flask.py.

En plus du fichier d'interface utilisateur, les jeux sont disponibles dans des fichiers Jupyter Notebook séparés. Toutes les importations sont indiquées au niveau de la première cellule et le répertoire ressources doit se situer dans le même répertoire que les fichiers Jupyter Notebook.

## Crédits et licences
Ce projet s'est appuyé sur PAGERANKRDF (https://github.com/QAnswer/PageRankRDF) sous licence MIT, Wembedder sous licence Apache (https://github.com/fnielsen/wembedder) et du fichier obtenu grâce à Danker (https://github.com/athalhammer/danker) sous licence GNUPL v3.0. Le fichier ressources/quiz_en_fr.json contient des données extraites du corpus QALD-9-plus qui est sous licence CC-BY-4.0 (https://github.com/KGQA/QALD_9_plus).
