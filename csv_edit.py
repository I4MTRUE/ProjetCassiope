import csv
import sys
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt

##### csv_edit.py #####
# Ce Programme est conçu pour manipuler des fichiers CSV contenant des articles de presse.
# Il permet de supprimer les doublons, de générer des statistiques quotidiennes et mensuelles,
# de convertir les dates au format français, et de visualiser les données à l'aide de graphiques.

csv.field_size_limit(10**6)

### Définition des fonctions ###

# Récupère la dernière date enregistrée dans un fichier CSV, ainsi que le titre associé et le nombre d'articles.
def get_last_saved_date(csv_file_path):
    nb_articles = 0
    last_date = None
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            nb_articles += 1
            if len(row) < 4:
                continue  # Ignore les lignes qui n'ont pas assez de colonnes
            try:
                current_date = datetime.strptime(row[2], "%Y-%m-%d")
                if last_date is None or current_date > last_date:
                    last_date = current_date
                    title= row[1]
            except ValueError:
                continue  # Ignore les lignes avec un format de date invalide
    return last_date,title,nb_articles

# Supprime les doublons d'un fichier CSV et écrit le résultat dans un nouveau fichier.
def remove_duplicates_from_csv(input_file, output_file):
    seen = set()  # Pour suivre les lignes uniques
    with open(input_file, mode='r', encoding='utf-8') as infile, \
         open(output_file, mode='w', encoding='utf-8', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        for row in reader:
            row_tuple = tuple(row)  # Convertit la ligne en tuple (hashable)
            if row_tuple not in seen:
                seen.add(row_tuple)  # Ajoute à l'ensemble si pas déjà vu
                writer.writerow(row)  # Écrit la ligne unique dans le fichier de sortie

# Génère un dictionnaire du nombre d'articles par jour à partir d'un fichier CSV et écrit les résultats dans un fichier.
def generate_daily_article_counts(input_file, output_file):
    daily_counts = defaultdict(int)
    with open(input_file, mode='r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        next(reader, None)  # Ignore la ligne d'en-tête
        for row in reader:
            if len(row) < 3:
                continue
            date = row[2]
            daily_counts[date] += 1
    with open(output_file, mode='w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["Date", "Article Count"])
        for date, count in sorted(daily_counts.items()):
            writer.writerow([date, count])
    return daily_counts

# Affiche un graphique du nombre d'articles par jour.
def plot_daily_article_counts(daily_counts):
    # Trie les dates pour un ordre chronologique correct
    sorted_dates = sorted(daily_counts.keys())
    counts = [daily_counts[date] for date in sorted_dates]

    # Affiche le graphique
    plt.figure(figsize=(10, 6))
    plt.bar(sorted_dates, counts, color='skyblue')
    plt.xlabel('Date')
    plt.ylabel('Number of Articles')
    plt.title('Number of Articles per Day')
    plt.xticks(rotation=45, ha='right')  # Rotation des labels pour une meilleure lisibilité
    plt.tight_layout()  # Ajuste la mise en page
    plt.show()

from collections import defaultdict
from datetime import datetime

# Regroupe les articles par mois à partir d'un dictionnaire de comptage quotidien.
def group_by_month(daily_counts):
    monthly_counts = defaultdict(int)
    for date, count in daily_counts.items():
        date = date_from_string(date)
        if date:
            month = date.strftime("%Y-%m")
        print(date)
        print(month)

        monthly_counts[month] += count
    return monthly_counts

# Convertit une chaîne de date (français ou ISO) en objet datetime.
def date_from_string(date_str):
    french_months = {
        "janvier": 1,
        "février": 2,
        "fevrier": 2,
        "mars": 3,
        "avril": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7,
        "août": 8,
        "aout": 8,
        "septembre": 9,
        "octobre": 10,
        "novembre": 11,
        "décembre": 12,
        "decembre": 12
    }
    try:
        parts = date_str.strip().split()
        if len(parts) == 3:
            day = int(parts[0])
            month = french_months[parts[1].lower()]
            year = int(parts[2])
            return datetime(year, month, day)
        else:
            return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None

# Affiche un graphique du nombre d'articles par mois.
def plot_monthly_article_counts(daily_counts):
    monthly_counts = group_by_month(daily_counts)

    sorted_months = sorted(monthly_counts.keys())
    counts = [monthly_counts[month] for month in sorted_months]

    plt.figure(figsize=(12, 6))
    plt.bar(sorted_months, counts, color='skyblue')
    plt.xlabel('Month')
    plt.ylabel('Number of Articles')
    plt.title('Number of Articles per Month')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

# Convertit les dates françaises dans un fichier CSV au format ISO (YYYY-MM-DD).
def convert_french_dates_in_csv(input_file, output_file):
    french_months = {
        "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
        "décembre": 12, "decembre": 12
    }
    with open(input_file, mode='r', encoding='utf-8') as infile, \
         open(output_file, mode='w', encoding='utf-8', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        for row in reader:
            if len(row) >= 3:
                date_str = row[2].strip()
                parts = date_str.split()
                if len(parts) == 3 and parts[1].lower() in french_months:
                    try:
                        day = int(parts[0])
                        month = french_months[parts[1].lower()]
                        year = int(parts[2])
                        new_date = f"{year:04d}-{month:02d}-{day:02d}"
                        row[2] = new_date
                    except Exception:
                        pass  # Si une erreur se produit, on laisse la date inchangée
            writer.writerow(row)

### Fonctions principales à exécuter ###

# Enleve les doublons dans le fichier CSV
if False:
    input_csv = 'articles_monde.csv'  # Remplacez par le chemin de votre fichier CSV d'entrée
    output_csv = 'articles_monde_cleaned.csv'  # Remplacez par le chemin de sortie désiré
    remove_duplicates_from_csv(input_csv, output_csv)


# Génère les statistiques quotidiennes et trace les graphiques journaliers
if False :
    input_csv = 'articles_monde.csv'  # Remplacez par le chemin de votre fichier CSV nettoyé
    output_csv = 'monde_article_counts_daily.csv'  # Remplacez par le chemin de sortie désiré
    daily_counts = generate_daily_article_counts(input_csv, output_csv)
    plot_daily_article_counts(daily_counts)

# Génère les statistiques quotidiennes et trace les graphiques mensuels
if False:
    input_csv = 'articles_monde_formatted_cleaned.csv'  # Remplacez par le chemin de votre fichier CSV nettoyé
    output_csv = 'daily_article_counts_monde.csv'  # Remplacez par le chemin de sortie désiré
    daily_counts = generate_daily_article_counts(input_csv, output_csv)
    group_by_month(daily_counts)
    plot_monthly_article_counts(daily_counts)

# Affiche la dernière date enregistrée dans le fichier CSV
if False:
    csv_file_path = 'article_daily_cleaned.csv'  # Remplacez par le chemin de votre fichier CSV
    last_date,title,nb_articles = get_last_saved_date(csv_file_path)
    if last_date:
        print("Last saved article date:", last_date.strftime("%Y-%m-%d"))
        print("Last saved article title:", title)
        print("Number of articles in the file:", nb_articles)
    else:
        print("No valid dates found in the file.")

# Convertit les dates françaises dans le fichier CSV (exemple: Le Monde)
if False:
    input_csv = 'articles_monde_cleaned.csv'  # Remplacez par le chemin de votre fichier CSV nettoyé
    output_csv = 'articles_monde_formatted_cleaned.csv'  # Remplacez par le chemin de sortie désiré
    daily_counts = convert_french_dates_in_csv(input_csv, output_csv)