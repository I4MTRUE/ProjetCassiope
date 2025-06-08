import os
import time
from seleniumbase import Driver
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from datetime import date, timedelta
import re 
from selenium.webdriver.common.by import By
import csv

##### nyt_scraper.py #####
# Ce Programme est conçu pour récupérer des articles du journal The New York Times à partir de ses archives.
# Il utilise Selenium pour naviguer sur le site, BeautifulSoup pour analyser le HTML,
# et enregistre les articles dans un fichier CSV. Il gère également la progression à l'aide d'un fichier de suivi.
# Il utilise undetected_chromedriver pour contourner les restrictions de détection de Selenium.
# Il utilise également ADB pour réinitialiser l'adresse IP via un téléphone Android pour éviter les captchas.
# Un téléphone Android en mode débogage USB est nécessaire pour exécuter ce script.
# *Optionnel : Le multiprocessing est utilisé pour traiter plusieurs dates en parallèle.


# Fichier pour sauvegarder la progression
PROGRESS_FILE = "progress_nyt.txt"

START_DATE = date(2015, 1, 1)  # Date de départ pour les archives du NYT
END_DATE = date(2025, 1, 1)  # Date de fin pour les archives du NYT

# Dictionnaire pour stocker les cookies (à remplir si besoin avec cookies NYT)
cookies = {

}

# Variables globales pour suivre le nombre d'articles récupérés et à récupérer
global articles_fetched
global to_fetch

# Construction de l'en-tête Cookie pour les requêtes HTTP
cookies_str = '; '.join([f'{key}={value}' for key, value in cookies.items()])

headers = {
    'Cookie': cookies_str
}

def reset_ip():
    """
    Réinitialise l'adresse IP via ADB (mode avion sur un téléphone Android connecté en USB).

    Args:
        Aucun

    Returns:
        None
    """
    print("resetting ip ...")
    os.system('adb shell cmd connectivity airplane-mode enable') # Attention : cette commande nécessite un téléphone Android en mode débogage USB
    time.sleep(10)
    os.system('adb shell cmd connectivity airplane-mode disable')
    print('ip changed !')
    time.sleep(3)

def fetch_archives_nyt(driver,date):
    """
    Récupère les archives pour une date donnée depuis la recherche du NYT.

    Args:
        driver: Instance Selenium WebDriver.
        date (str): Date au format YYYY-MM-DD.

    Returns:
        None
    """
    url = 'https://www.nytimes.com/search?dropmab=false&endDate='+date+'&lang=en&query=&sections=Business|nyt%3A%2F%2Fsection%2F0415b2b0-513a-5e78-80da-21ab770cb753%2CNew%20York|nyt%3A%2F%2Fsection%2F39480374-66d3-5603-9ce1-58cfa12988e2%2COpinion|nyt%3A%2F%2Fsection%2Fd7a71185-aa60-5635-bce0-5fab76c7c297%2CU.S.|nyt%3A%2F%2Fsection%2Fa34d3d6c-c77f-5931-b951-241b4e28681c%2CWorld|nyt%3A%2F%2Fsection%2F70e865b6-cc70-5181-84c9-8368b3a5c34b&sort=best&startDate='+date+'&types=article'
    print(url)
    soup = fetch_article(url)
    getArticleURLNYT(driver,soup)

def fetch_article(driver, url, condition):
    """
    Charge une page web et retourne le contenu sous forme de BeautifulSoup.

    Args:
        driver: Instance Selenium WebDriver.
        url (str): URL de la page à charger.
        condition (int): Si 1, clique sur le bouton "show more".

    Returns:
        BeautifulSoup: La soupe de la page chargée.
    """
    driver.set_page_load_timeout(10)
    try:
        driver.get(url)
    except TimeoutException:
        print("TIMEOUT !!!")
        reset_ip()
        driver.get(url)
    if condition == 1:
        button = driver.find_element(By.CSS_SELECTOR, '[data-testid="search-show-more-button"]')
        button.click()
    time.sleep(1)
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, "html.parser")
    return soup

def getArticleURLNYT(driver, soup):
    """
    Extrait les URLs des articles et traite chaque article.

    Args:
        driver: Instance Selenium WebDriver.
        soup (BeautifulSoup): La soupe de la page de résultats de recherche.

    Returns:
        None
    """
    i=1
    print("Fetching articles from URL")
    liste = soup.find_all("ol")
    for li in soup.find_all("li"):
        if li.get("data-testid") == "search-bodega-result":
            print(to_fetch)
            print(articles_fetched)
            if i<=(10-to_fetch):
                i+=1
                continue
            if i>=(20-articles_fetched):
                break
            article_url = li.find("a")["href"]
            print(article_url)
            if not re.match(r"^/\d{4}/\d{2}/\d{2}($|/|\?)", article_url):
                continue
            article_date = ""+article_url.split("/")[1]+"-"+article_url.split("/")[2]+"-"+article_url.split("/")[3]
            print(article_date)
            try:
                print("Fetching article from URL:", article_url)
                soup = fetch_article(driver, "https://www.nytimes.com"+article_url,0)
                journal_name,article_title, article_desc, raw_text = get_article_content_nyt(soup)
            except ValueError:
                print("You got Captcha-ed ... RESETTING IP ...")
                retries = 0
                while retries<2:
                    try:
                        reset_ip()
                        print("Fetching article from URL:", article_url)
                        soup = fetch_article(driver, "https://www.nytimes.com"+article_url,0)
                        journal_name,article_title, article_desc, raw_text = get_article_content_nyt(soup)
                        break
                    except ValueError:
                        retries+=1
                        continue
                    except TimeoutException:
                        retries+=1
                        continue
                if retries==2: 
                    print("Driver is flagged, resetting ...")
                    # Réinitialise le driver et relance la fonction principale
                    driver.quit()
                    main()
            saveToCSV(journal_name,article_title, article_date, article_desc, raw_text)
            i=i+1
            print(article_title+" saved to CSV")

def saveToCSV(journal_name,article_title, article_date, article_desc, raw_text):
    """
    Sauvegarde les informations de l'article dans un fichier CSV.

    Args:
        journal_name (str): Le nom du journal.
        article_title (str): Le titre de l'article.
        article_date (str): La date de l'article.
        article_desc (str): La description de l'article.
        raw_text (str): Le texte brut de l'article.

    Returns:
        None
    """
    with open('article_nyt.csv', mode='a') as file:
        writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([journal_name,article_title, article_date, article_desc, raw_text])
    update_article_count(article_date)

def update_article_count(article_date):
    """
    Met à jour le nombre d'articles récupérés pour chaque date.

    Args:
        article_date (str): La date de l'article.

    Returns:
        None
    """
    count_file = "article_count.txt"
    counts = {}

    if os.path.exists(count_file):
        with open(count_file, "r") as file:
            for line in file:
                date, count = line.strip().split(",")
                counts[date] = int(count)

    if article_date in counts:
        counts[article_date] += 1
    else:
        counts[article_date] = 1

    with open(count_file, "w") as file:
        for date, count in counts.items():
            file.write(f"{date},{count}\n")

def get_article_content_nyt(soup):
    """
    Extrait le contenu d'un article NYT (titre, description, texte brut).

    Args:
        soup (BeautifulSoup): La soupe de la page de l'article.

    Returns:
        tuple: (nom du journal, titre, description, texte brut)
    """
    article_title = soup.find(class_="e1h9rw200")
    if not article_title:
        for iframe in soup.find_all("iframe"):
            print(iframe.get("src"))
        if soup.find("iframe", {"src": lambda x: x and "captcha-delivery.com" in x}): # Détection de captcha
            raise ValueError("You got Captcha-ed ... RESETTING IP ...") # Réinitialisation de l'IP
        else :
            return "The New York Times", "",["","","","",""],"",""
    article_title = article_title.get_text(strip=True)
    article_desc = soup.find(id="article-summary")
    if not article_desc :
        article_desc = soup.find(class_="e1wiw3jv0")
    if article_desc:
        article_desc = article_desc.get_text(strip=True)
    article_content = soup.find(class_="meteredContent")
    raw_text = "\n".join(p.get_text(strip=True) for p in article_content.find_all(["p"],recursive=True))
    return "The New York Times",article_title, article_desc, raw_text

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
    Charge la progression sauvegardée, ou retourne une date de départ par défaut.

    Returns:
        date: La date de reprise ou la date de départ si aucune progression.
    """
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as file:
            progress = file.read().strip()
            if progress:
                year, month, day = map(int, progress.split(","))
                return date(year, month, day)
    return START_DATE  # Si aucun fichier détecté, retourne la date de départ

def process_daily_article_counts(file_path):
    """
    Lit un fichier CSV contenant le nombre d'articles par jour.

    Args:
        file_path (str): Chemin du fichier CSV.

    Returns:
        dict: Dictionnaire {date: nombre d'articles}
    """
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)
        daily_counts = {row[0]: int(row[1]) for row in reader}
    return daily_counts

def main():
    """
    Fonction principale : boucle sur les dates, récupère les articles et gère la progression.

    Args:
        Aucun

    Returns:
        None
    """
    start_date = load_progress()
    end_date = END_DATE

    daily_counts_file = "daily_article_counts.csv"
    daily_counts = process_daily_article_counts(daily_counts_file)

    with Driver(uc=True, headless=False) as driver:
        driver.get("https://www.nytimes.com/")
        for key, value in cookies.items():
            driver.add_cookie({'name': key, 'value': value})
        print(f"Added {len(cookies)} cookies.")
        driver.refresh()

        current_date = start_date
        while current_date <= end_date:
            # Boucle sur chaque date à traiter
            global articles_fetched
            global to_fetch
            articles_fetched = daily_counts.get(current_date.strftime("%Y-%m-%d"), -1)
            to_fetch = 0
            print(f"Fetching articles for {current_date}: {10-articles_fetched} articles")
            if articles_fetched == 10:
                # Si tous les articles sont déjà récupérés pour cette date, passe à la suivante
                print(f"No articles to fetch for {current_date}. Skipping...")
                current_date += timedelta(days=1)
                continue
            if articles_fetched == -1:
                # Si aucun article n'a été récupéré, initialise les compteurs
                to_fetch=10
                articles_fetched=0
            try:
                # Lance la récupération des articles pour la date courante
                fetch_archives_nyt(driver,current_date.strftime("%Y-%m-%d"))
                save_progress(current_date.year, current_date.month, current_date.day)
                print(f"Saved progress for {current_date}")
            except Exception as e:
                # Gestion des erreurs pour chaque date
                print(f"Error on {current_date}: {e}")
            current_date += timedelta(days=1)

        driver.quit()
        print("Finished fetching articles.")
        return

if __name__ == "__main__":
    main()
