import os
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from datetime import date, timedelta
import csv

##### dailymail_scraper.py #####
# Ce programme permet de récupérer des articles du journal Daily Mail à partir de ses archives.
# Il utilise Selenium pour naviguer sur le site, BeautifulSoup pour analyser le HTML,
# et enregistre les articles dans un fichier CSV. Il gère aussi la progression via un fichier de suivi.

# Configuration des options Selenium pour Firefox
options = Options()
ua = UserAgent()
options.add_argument("--disable-gpu")  # Désactive le GPU pour plus de stabilité
options.add_argument("--headless")     # Exécute le navigateur en mode headless (sans interface graphique)
options.set_preference("general.useragent.override", ua.random)  # Définit un user-agent aléatoire
options.binary_location = "/snap/bin/geckodriver"  # Chemin du binaire geckodriver

START_DATE = date(2015, 1, 1)  # Date de départ pour les archives
END_DATE = date(2025, 1, 1)    # Date de fin pour les archives

PROGRESS_FILE = "progress_daily.txt"  # Fichier pour sauvegarder la progression

inclu=['news']      # Mots-clés à inclure dans les URLs d'articles
exclu=['indianews'] # Mots-clés à exclure des URLs d'articles

def get_article_content_daily(soup):
    """
    Extrait le contenu d'un article Daily Mail à partir de la soupe BeautifulSoup.

    Args:
        soup (BeautifulSoup): La soupe BeautifulSoup de la page de l'article.

    Returns:
        tuple: (nom du journal, titre, date, description, texte brut)
    """
    article_head = soup.find(id = "js-article-text")  # Bloc principal de l'article
    article_title = article_head.find("h1").get_text(strip=True)  # Titre de l'article
    article_desc = article_head.find("ul")  # Liste des points forts (ul)
    # Concatène tous les textes des balises <strong> dans la description
    article_desc = " ".join(strong.get_text(strip=False) for strong in article_desc.find_all(["strong"],recursive=True))
    article_date = soup.find("meta", property="article:published_time")  # Date de publication
    if article_date:
        article_date = article_date.get("content")
        article_date = article_date.split("T")[0]   # Garde uniquement la date (YYYY-MM-DD)
    focus = soup.find(itemprop="articleBody")  # Corps principal de l'article
    # Concatène tous les paragraphes du corps de l'article
    raw_text = "\n".join(p.get_text(strip=False) for p in focus.find_all(["p"],recursive=False))
    return "Daily Mail",article_title, article_date, article_desc, raw_text

def saveToCSV(journal_name,article_title, article_date, article_desc, raw_text):
    """
    Enregistre les données d'un article dans un fichier CSV.

    Args:
        journal_name (str): Le nom du journal.
        article_title (str): Le titre de l'article.
        article_date (str): La date de l'article.
        article_desc (str): La description de l'article.
        raw_text (str): Le texte brut de l'article.
    Returns:
        None
    """
    import csv
    with open('articles_daily.csv', mode='a') as file:
        writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([journal_name,article_title, article_date, article_desc, raw_text])

def getArticleURLdaily(soup):
    """
    Récupère les URLs des articles à partir de la page d'archives Daily Mail et traite chaque article.

    Args:
        soup (BeautifulSoup): La soupe BeautifulSoup de la page d'archives.

    Returns:
        None
    """
    global fetched
    ul = soup.find("ul", class_="archive-articles")
    for li in ul.find_all("li")[10:]:
        if fetched<10:
            link = li.find("a")
            if link:
                article_url = link["href"]
                print(article_url)
                # Filtre selon les mots-clés inclus/exclus
                if any(word in article_url for word in exclu):
                    continue
                if not any(word in article_url for word in inclu):
                    continue
                print("Fetching article from URL:", article_url)
                soup = fetch_article('https://www.dailymail.co.uk'+article_url)
                journal_name,article_title, article_date, article_desc, raw_text = get_article_content_daily(soup)
                saveToCSV(journal_name,article_title, article_date, article_desc, raw_text)
                fetched+=1
            else:
                return

def get_fetched_count_for_date(year, month, day):
    """
    Retourne le nombre d'articles déjà récupérés pour une date donnée.

    Args:
        year (int): Année.
        month (int): Mois.
        day (int): Jour.

    Returns:
        int: Nombre d'articles déjà récupérés pour la date.
    """
    filename = "daily_article_counts_daily.csv"
    date_str = f"{year}-{month:02d}-{day:02d}"
    if not os.path.exists(filename):
        return 0
    with open(filename, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("date") == date_str:
                try:
                    return int(row.get("count", 0))
                except Exception:
                    return 0
    return 0

def fetch_article(url):
    """
    Récupère le contenu HTML d'un article à partir de son URL.

    Args:
        url (str): L'URL de l'article.

    Returns:
        BeautifulSoup: La soupe BeautifulSoup de la page de l'article.
    """
    try:
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, "html.parser")
    finally:
        return soup

def fetch_archives_daily(y,m,d):
    """
    Récupère la liste des articles pour une date donnée depuis les archives du Daily Mail.

    Args:
        y (int): Année.
        m (int): Mois.
        d (int): Jour.

    Returns:
        None
    """
    url = f"https://www.dailymail.co.uk/home/sitemaparchive/day_{y}{m:02d}{d:02d}.html"
    soup = fetch_article(url)
    getArticleURLdaily(soup)

def save_progress(year, month, day):
    """
    Sauvegarde la progression (date courante) dans un fichier.

    Args:
        year (int): Année.
        month (int): Mois.
        day (int): Jour.

    Returns:
        None
    """
    with open(PROGRESS_FILE, "w") as file:
        file.write(f"{year},{month},{day}")

def load_progress():
    """
    Charge la progression sauvegardée, ou retourne la date de départ par défaut.

    Returns:
        date: La date de reprise ou la date de départ si aucune progression.
    """
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as file:
            progress = file.read().strip()
            if progress:
                year, month, day = map(int, progress.split(","))
                return date(year, month, day)
    return START_DATE # Date de départ

if __name__ == "__main__":
    # Point d'entrée principal du script
    global fetched
    fetched=0
    start_date = load_progress()
    end_date = END_DATE
    driver = webdriver.Firefox(options=options,service=service)

    driver.get('https://www.dailymail.co.uk/')
    current_date = start_date
    while current_date <= end_date:
        fetched = get_fetched_count_for_date(current_date.year, current_date.month, current_date.day)
        for attempts in range(3):
            try:
                fetch_archives_daily(current_date.year,current_date.month,current_date.day)
                break
            except Exception as e:
                print(f"Error fetching {current_date}: {e}")
                if attempts == 2:
                    print("Max attempts reached. Skipping date.")
        current_date += timedelta(days=1)
        fetched=0
        save_progress(current_date.year, current_date.month, current_date.day)