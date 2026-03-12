# GoogleMapsScraper

Ce projet permet de lancer automatiquement des recherches Google Maps par **catégorie** et **code postal**, puis d’enregistrer les entreprises trouvées dans `companies.csv`.

Le fonctionnement est simple :

1. vous préparez votre fichier `categories.csv` à la main ;
2. vous lancez le script `google_maps.py` ;
3. vous saisissez un code postal ;
4. le script ouvre Google Maps, exécute chaque recherche catégorie par catégorie, ferme le navigateur, puis recommence avec la catégorie suivante ;
5. les résultats sont enregistrés progressivement dans `companies.csv`, sans doublons.

## Fichiers du projet

* `google_maps.py` : script principal de scraping Google Maps
* `categories.csv` : liste des catégories à rechercher
* `companies.csv` : fichier de sortie contenant les entreprises trouvées
* `utils.py` : fonctions utilitaires (logs, pauses, normalisation)
* `requirements.txt` : dépendances Python du projet

## Prérequis

* macOS
* Google Chrome installé à cet emplacement :
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
* Python 3.11 ou plus récent
* un fichier `categories.csv` rempli manuellement

## Installation

Dans le dossier du projet, exécuter :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
playwright install
```

## Préparer le fichier `categories.csv`

Le script lit les catégories depuis un fichier CSV contenant une colonne obligatoire nommée `category_name`.

Exemple minimal :

```csv
category_name
Salon de coiffure
Restaurant
Boulangerie
Centre équestre
```

Règles à respecter :

* la première ligne doit être `category_name`
* une catégorie par ligne
* les catégories sont traitées dans l’ordre du fichier
* vous pouvez modifier ce fichier librement à la main avant chaque lancement

## Utilisation

Lancer le script principal :

```bash
python3 google_maps.py
```

Le script demandera uniquement un code postal français à 5 chiffres.

Exemple :

```text
83160
```

Ensuite, pour chaque catégorie présente dans `categories.csv`, le script :

* construit une recherche Google Maps sous la forme `<Catégorie> - <Code postal>`
* ouvre Chrome avec Playwright
* charge la page de résultats Google Maps
* parcourt les résultats visibles
* clique sur chaque fiche pour charger les détails
* extrait les informations disponibles
* écrit chaque entreprise immédiatement dans `companies.csv`
* ferme le navigateur en fin de catégorie
* rouvre un navigateur pour la catégorie suivante

## Exemple de recherche générée

Si `categories.csv` contient :

```csv
category_name
Salon de coiffure
Boulangerie
```

et que vous saisissez le code postal :

```text
83160
```

le script lancera successivement les recherches suivantes :

```text
Salon de coiffure - 83160
Boulangerie - 83160
```

## Fichier de sortie `companies.csv`

Les entreprises trouvées sont enregistrées dans ce fichier :

```text
companies.csv
```

Colonnes enregistrées :

```csv
business_name,category_name,postal_code,address,phone,website,rating,review_count,email,google_maps_url
```

Description rapide des colonnes :

* `business_name` : nom de l’établissement
* `category_name` : catégorie détectée ou catégorie recherchée
* `postal_code` : code postal utilisé pour la recherche
* `address` : adresse de l’établissement
* `phone` : numéro de téléphone
* `website` : site web ou lien principal trouvé
* `rating` : note Google
* `review_count` : nombre d’avis
* `email` : email détecté si disponible
* `google_maps_url` : URL de la fiche Google Maps

## Gestion des doublons

Le script évite d’enregistrer deux fois la même entreprise.

La détection de doublons se fait en priorité via :

* l’URL Google Maps
* sinon le couple nom + adresse
* sinon le couple nom + téléphone
* sinon le nom seul

Cela permet de relancer le script sans réécrire les lignes déjà présentes dans `companies.csv`.

## Comportement du navigateur

Pour chaque catégorie :

* un navigateur est ouvert
* la recherche Google Maps est exécutée directement par URL
* les résultats sont parcourus progressivement
* le navigateur est fermé à la fin

Ce comportement permet de repartir sur une session propre entre deux catégories.

## Conseils d’utilisation

* vérifier que `categories.csv` contient uniquement les catégories utiles
* commencer avec quelques catégories pour tester le comportement
* ne pas modifier manuellement `companies.csv` pendant l’exécution
* conserver le profil Chrome si vous souhaitez garder une session stable

## Lancer un test simple

Exemple de `categories.csv` :

```csv
category_name
Centre équestre
```

Puis lancer :

```bash
python3 google_maps.py
```

Entrer ensuite :

```text
83160
```

La recherche exécutée sera :

```text
Centre équestre - 83160
```

## Dépannage

Si le script ne fonctionne pas correctement, vérifier en priorité :

* que Google Chrome est bien installé au chemin configuré
* que `categories.csv` existe bien dans le dossier du projet
* que la colonne `category_name` est présente
* que le code postal saisi contient exactement 5 chiffres
* que les dépendances ont bien été installées
* que Playwright est bien installé

## Commandes utiles

Créer l’environnement virtuel et installer les dépendances :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install
```

Lancer le scraper :

```bash
python3 google_maps.py
```

## Résumé

* `categories.csv` est préparé à la main
* le script demande seulement le code postal
* chaque catégorie est recherchée automatiquement
* le navigateur est fermé puis rouvert entre chaque catégorie
* les résultats sont ajoutés progressivement dans `companies.csv`
* les doublons sont ignorés
