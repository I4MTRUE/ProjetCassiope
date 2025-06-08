from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import os
import multiprocessing
from multiprocessing import Lock
import csv
from datetime import date, timedelta

##### lemonde_scraper.py #####
# Ce Programme est conçu pour récupérer des articles du journal Le Monde à partir de ses archives.
# Il utilise Selenium pour naviguer sur le site, BeautifulSoup pour analyser le HTML,
# et enregistre les articles dans un fichier CSV. Il gère également la progression à l'aide d'un fichier de suivi.
# Il utilise geckodriver pour contrôler Firefox en mode headless.
# *Optionnel : Le multiprocessing est utilisé pour traiter plusieurs dates en parallèle.

START_DATE = date(2015, 1, 1)  # Date de départ pour les archives du Monde
END_DATE = date(2025, 1, 1)  # Date de fin pour les archives du Monde

# Configuration des options Selenium pour Firefox (dépend de l'installation de geckodriver)
options = Options()
ua = UserAgent()
options.add_argument("--disable-gpu")  # Désactive le GPU pour plus de stabilité
options.add_argument("--headless")  # Exécute le navigateur en mode headless (sans interface graphique)
options.set_preference("general.useragent.override", ua.random)
options.binary_location = "/snap/bin/geckodriver" 

# Initialisation d'un verrou global pour la gestion des accès concurrents au fichier CSV (multiprocessing)
global lock 
lock = Lock()

PROGRESS_FILE = "progress_monde.txt"

# Listes de mots-clés pour inclure ou exclure certaines catégories d'articles
inclu=['international','politique','societe','economie','idees','afrique','planete','police-justice','asie-pacifique','immigration-et-diversite','proche-orient']
exclu=['video','bande-dessinee','visuel','live','5241561','blog','mondephilatelique']

# Sauvegarde la date de progression dans un fichier
def save_progress(date):
    """
    Sauvegarde la date de progression dans un fichier.

    Args:
        date (str): La date à sauvegarder au format string.
    Returns:
        None
    """
    with open(PROGRESS_FILE, "w") as file:
        file.write(f"{date}")

# Charge la date de progression depuis un fichier, ou retourne la date de départ par défaut
def load_progress():
    """
    Charge la date de progression depuis un fichier, ou retourne la date de départ par défaut.

    Returns:
        date: La date de progression ou la date de départ si aucune progression sauvegardée.
    """
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as file:
            progress = file.read().strip()
            if progress:
                year, month, day = map(int, progress.split("-"))
                return date(year, month, day)
    return START_DATE  # Si aucun fichier détecté, retourne la date de départ

# Extrait le contenu d'un article du Monde à partir du HTML (BeautifulSoup)
def get_article_content_monde(soup):
    """
    Extrait le contenu d'un article du Monde à partir du HTML (BeautifulSoup).

    Args:
        soup (BeautifulSoup): La soupe BeautifulSoup de la page de l'article.

    Returns:
        tuple: (nom du journal, titre, date (liste), description, texte brut)
    """
    main_section = soup.find(class_="main")
    article_section = main_section.find(class_="article")
    if not article_section:
        return "Le Monde", "",["","","","",""],"",""
    if soup.find(class_="page__campaigns-img-wrapper"):
        return "Le Monde", "",["","","","",""],"",""
    article_title = article_section.find(class_ = "article__title").get_text(strip=True)
    article_desc = article_section.find(class_="article__desc")
    if not article_desc :
        article_desc = ""
    else:
        article_desc = article_desc.get_text(strip=True)
    article_heading = article_section.find(class_="article__heading")
    article_date = main_section.find(class_="meta__date")
    if not article_date:
        article_date = main_section.find(class_="meta__date-reading")
    article_date = article_date.get_text(strip=True)
    article_date = article_date.split(" ")
    article_content = article_section.find(class_="article__content")
    # Nettoie le texte en supprimant les balises <a> et <em>
    for a in soup.find_all("a"):
        a.insert_after(" ")
        a.unwrap()
    for em in soup.find_all("em"):
        em.insert_after(" ")
        em.unwrap()
    raw_text = "\n".join(p.get_text(strip=True) for p in article_content.find_all(["p"],recursive=False))
    return "Le Monde",article_title, article_date, article_desc, raw_text

# Sauvegarde les informations d'un article dans un fichier CSV (accès protégé par un verrou)
def saveToCSV(journal_name,article_title, article_date, article_desc, raw_text):
    """
    Sauvegarde les informations d'un article dans un fichier CSV (accès protégé par un verrou).

    Args:
        journal_name (str): Le nom du journal.
        article_title (str): Le titre de l'article.
        article_date (str): La date de l'article.
        article_desc (str): La description de l'article.
        raw_text (str): Le texte brut de l'article.
    Returns:
        None
    """
    lock.acquire()
    with open('articles_test.csv', mode='a') as file:
        writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([journal_name,article_title, article_date, article_desc, raw_text])
    lock.release()

# Récupère les URLs des articles du Monde pour une date donnée et les traite
def getArticleURLMonde(driver, soup):
    """
    Récupère les URLs des articles du Monde pour une date donnée et les traite.

    Args:
        driver (webdriver): Instance Selenium WebDriver.
        soup (BeautifulSoup): La soupe BeautifulSoup de la page d'archives.

    Returns:
        int: Le nombre d'articles sauvegardés.
    """
    count = 0
    river = soup.find(class_="river")
    for section in river.find_all(class_="teaser"):
        if count >= 10:
            break
        link = section.find("a")
        if not link:
            continue
        article_url = link["href"]
        if not any(word in article_url for word in inclu): # Inclut uniquement les articles désirés
            continue
        if any(word in article_url for word in exclu): # Exclut les articles indésirables
            continue
        if "https://www.lemonde.fr" not in article_url: # Vérifie que l'URL est bien celle du Monde
            continue
        print("Fetching article from URL:", article_url)
        soup = fetch_article(driver, article_url)
        if soup is None:
            continue
        journal_name, article_title, article_date, article_desc, raw_text = get_article_content_monde(soup)
        article_date_str = article_date[2] + " " + article_date[3] + " " + article_date[4]
        saveToCSV(journal_name, article_title, article_date_str, article_desc, raw_text)
        count += 1
    return count

# Récupère le contenu HTML d'un article via Selenium et BeautifulSoup
def fetch_article(driver,url):
    """
    Récupère le contenu HTML d'un article via Selenium et BeautifulSoup.

    Args:
        driver (webdriver): Instance Selenium WebDriver.
        url (str): L'URL de l'article.

    Returns:
        BeautifulSoup | None: La soupe BeautifulSoup de la page de l'article, ou None si la page n'est pas trouvée.
    """
    driver.get(url)
    if driver.current_url == "https://www.lemonde.fr" or driver.current_url == "https://www.lemonde.fr/en/":
        return None
    soup = BeautifulSoup(driver.page_source, "html.parser")
    return soup

# Récupère les archives du Monde pour une date donnée (jusqu'à 10 articles)
def fetch_archives_monde(driver, date):
    """
    Récupère les archives du Monde pour une date donnée (jusqu'à 10 articles).

    Args:
        driver (webdriver): Instance Selenium WebDriver.
        date (str): Date au format JJ-MM-YYYY.

    Returns:
        None
    """
    attempts = 0
    saved_articles = 0
    while saved_articles < 10 and attempts < 3:
        url = f"https://www.lemonde.fr/archives-du-monde/{date}" # URL pour les archives du Monde
        soup = fetch_article(driver, url)
        if soup:
            saved_articles = getArticleURLMonde(driver, soup)
        attempts += 1
        time.sleep(2)
    print(f"[{date}] Saved {saved_articles} articles.")

# Fonction exécutée par chaque processus pour traiter une date spécifique (multiprocessing)
def worker_init(date):
    """
    Fonction exécutée par chaque processus pour traiter une date spécifique (multiprocessing).

    Args:
        date (str): Date à traiter au format JJ-MM-YYYY.

    Returns:
        None
    """
    driver = webdriver.Firefox(options=options)
    driver.get("https://www.lemonde.fr")
    driver.add_cookie({"name": "lmd_a_s", "value": "I%2BMVwLYXuI9D5yqg9arDKw9s8SEStIKz2B8ayMidZPY60Wl9y%2BAwig15cBDVo1Nw"})
    fetch_archives_monde(driver,date)
    save_progress(date)
    driver.quit()

if __name__ == "__main__":

    # Charge la date de départ depuis le fichier de progression
    start_date = load_progress()
    end_date = END_DATE
    print("Initializing from date:", start_date)
    dates = []
    current_date = start_date
    # Génère la liste des dates à traiter
    while current_date <= end_date:
        dates.append(current_date.strftime("%d-%m-%Y"))
        current_date += timedelta(days=1)
    print("Done")

    # Gestion du multiprocessing pour traiter plusieurs dates en parallèle (optionnel)
    processes = []
    max_processes = 3
    while len(dates) > 0 or len(processes) > 0:
        processes = [p for p in processes if p.is_alive()]

        while len(processes) < max_processes and len(dates) > 0:
            date = dates.pop(0)
            print("Starting process for date:", date)
            p = multiprocessing.Process(target=worker_init, args=(date,))
            p.start()
            processes.append(p)

        time.sleep(0.1) # Attente pour éviter une surcharge CPU
