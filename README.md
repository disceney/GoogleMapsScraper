# Scrapper

Ce projet contient deux scripts Python basés sur Playwright.

Le workflow est le suivant :

1. Générer la liste des catégories Google Business dans `categories.csv`
2. Lancer la recherche Google Maps à partir d’une catégorie et d’un code postal
3. Enregistrer les entreprises trouvées dans `companies.csv`

## Fichiers

- `categories.py` : récupère les catégories depuis PlePer et les enregistre dans `categories.csv`
- `google_maps.py` : ouvre Google Maps, lance une recherche `<Category> - <Postal Code>` et enregistre les résultats dans `companies.csv`
- `utils.py` : fonctions utilitaires de logs, pauses “humaines” et normalisation de texte

## Prérequis

- macOS
- Google Chrome installé dans : `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- Python 3.14

## Installation

```shell
sudo rm -Rf .venv/

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install --upgrade pip
pip3 install --upgrade pip

pip3 install -r ./requirements.txt --upgrade
```

## Utilisation

### 1. Générer les catégories

Lancer d’abord le script de récupération des catégories :

```shell
python3 categories.py
```

Ce script :

- ouvre la page PlePer des catégories Google Business
- parcourt les pages une par une
- récupère les catégories uniques
- enregistre le résultat dans `categories.csv`

Fichier généré :

```text
categories.csv
```

Format attendu :

```csv
category_name
Centre Aadhar
Concessionnaire Abarth
Abbaye
...
```

### 2. Lancer la recherche Google Maps

Une fois `categories.csv` généré, lancer le script Google Maps :

```shell
python3 google_maps.py
```

Le script demande alors :

- un code postal français
- une catégorie existante dans `categories.csv`

Il ouvre ensuite Google Maps avec une recherche de ce type :

```text
<Category> - <Postal Code>
```

Exemple :

```text
Salon de coiffure - 94500
```

## Résultat Google Maps

Le script Google Maps :

- ouvre Google Maps dans Chrome via Playwright
- charge la recherche à partir de la catégorie et du code postal
- parcourt les résultats visibles dans la colonne de gauche
- ouvre chaque fiche établissement
- extrait les informations disponibles
- écrit chaque entreprise au fur et à mesure dans `companies.csv`
- évite les doublons déjà enregistrés

Fichier généré :

```text
companies.csv
```

Colonnes enregistrées :

```csv
business_name,category_name,postal_code,address,phone,website,rating,review_count,email,google_maps_url
```

## Exemple de workflow complet

```shell
# 1. Générer les catégories
python3 categories.py

# 2. Lancer Google Maps
python3 google_maps.py
```

## Notes

- Il est recommandé d’exécuter `categories.py` avant `google_maps.py`
- `google_maps.py` dépend du fichier `categories.csv`
- Des pauses aléatoires sont ajoutées pour simuler un comportement humain
- Les résultats sont enregistrés progressivement dans le CSV
- Les doublons sont ignorés
