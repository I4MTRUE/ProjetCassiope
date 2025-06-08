import os
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
import time
from bs4 import BeautifulSoup
import requests
from fake_useragent import UserAgent
from datetime import date, timedelta

##### 20minutes_scraper.py #####
# Ce Programme est conçu pour récupérer des articles du journal 20 Minutes à partir de ses archives.
# Il est inspiré du script de scraping du Monde, mais adapté pour le 20 Minutes.
# Il utilise Selenium pour naviguer sur le site, BeautifulSoup pour analyser le HTML,
# et enregistre les articles dans un fichier CSV. Il gère également la progression à l'aide d'un fichier de suivi.

# Configuration des options Selenium pour Firefox (dépend de l'installation de geckodriver)
options = Options()
ua = UserAgent()
options.add_argument("--disable-gpu")  # Désactive le GPU pour plus de stabilité
options.add_argument("--headless")  # Exécute le navigateur en mode headless (sans interface graphique)
options.set_preference("general.useragent.override", ua.random)  # Définit un user-agent aléatoire pour éviter le blocage
options.binary_location = "/snap/bin/geckodriver"  # Définit le chemin du binaire geckodriver (à adapter si besoin)


PROGRESS_FILE = "progress_20min.txt"  # Fichier pour sauvegarder la progression

START_DATE = date(2015, 1, 1)  # Date de départ pour les archives du Daily Mail
END_DATE = date(2025, 1, 1)  # Date de fin pour les archives du Daily Mail

# Listes des mots-clés inclus et exclus pour le filtrage des articles
inclu=['international','politique','societe','economie','idees','afrique','planete','police-justice','monde','planete','faits_divers','sante','france','elections']
exclu=['video','direct']

def get_article_content_20min(soup):
    """
    Extrait le contenu d'un article à partir de la soupe BeautifulSoup d'une page d'article 20 Minutes.
    
    Args:
        soup (BeautifulSoup): La soupe BeautifulSoup de la page de l'article.
        
    Returns:
        tuple: Un tuple contenant le nom du journal, le titre de l'article, la date de l'article,
               la description de l'article et le texte brut de l'article.
    """
    article_section = soup.find(id="page-content")
    article_title = article_section.find(class_ = "heading-xxl@md").get_text(strip=True)
    article_desc = article_section.find(class_="text-xxl@xs")
    if not article_desc :
        article_desc = ""
    else:
        article_desc = article_desc.get_text(strip=True)
    article_date = soup.find("meta", property="article:published_time")
    if article_date:
        article_date = article_date.get("content")
        article_date = article_date.split("T")[0]   
    focus = article_section.find(class_="c-content")

    raw_text = "\n".join(p.get_text(strip=False) for p in focus.find_all(["p"],recursive=False))
    return "20 Minutes",article_title, article_date, article_desc, raw_text

def saveToCSV(journal_name,article_title, article_date, article_desc, raw_text):
    """
    Enregistre les données d'un article dans un fichier CSV.
    
    Args:
        journal_name (str): Le nom du journal.
        article_title (str): Le titre de l'article.
        article_date (str): La date de l'article.
        article_desc (str): La description de l'article.
        raw_text (str): Le texte brut de l'article.
    """
    import csv
    with open('articles_20min.csv', mode='a') as file:
        writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([journal_name,article_title, article_date, article_desc, raw_text])

def getArticleURL20min(soup):
    """
    Récupère les URLs des articles à partir de la page d'archives 20 Minutes.
    """
    fetched=0
    river = soup.find(class_="mb-xxl@md")
    ul = river.find("ul")
    if ul is None:
        for div in river.find_all("div", class_="flex@xs"):
            if fetched<10:
                link = div.find("a")
                if link:
                    article_url = link["href"]
                    # Filtre selon les mots-clés inclus/exclus
                    if not any(word in article_url for word in inclu):
                            continue
                    if 'https://www.20minutes.fr/' not in article_url:
                        continue
                    if any(word in article_url for word in exclu):
                        continue
                    print("Fetching article from URL:", article_url)
                    soup = fetch_article(article_url)
                    journal_name,article_title, article_date, article_desc, raw_text = get_article_content_20min(soup)
                    saveToCSV(journal_name,article_title, article_date, article_desc, raw_text)
                    fetched+=1
            else:
                return
    for li in ul.find_all("li"):
        if fetched<10:
            link = li.find("a")
            if link:
                article_url = link["href"]
                print(article_url)
                # Filtrage des URLs d'articles selon les mots-clés inclus et exclus
                if not any(word in article_url for word in inclu):
                    continue
                if 'https://www.20minutes.fr/' not in article_url:
                    continue
                if any(word in article_url for word in exclu):
                    continue
                print("Fetching article from URL:", article_url)
                soup = fetch_article(article_url)
                journal_name,article_title, article_date, article_desc, raw_text = get_article_content_20min(soup)
                saveToCSV(journal_name,article_title, article_date, article_desc, raw_text)
                fetched+=1
            else:
                return
            

def fetch_article(url):
    """
    Récupère le contenu d'un article à partir de son URL.
    
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

def fetch_archives_20minutes(y,m,d):
    """
    Récupère les archives de 20 Minutes pour une date donnée.
    
    Args:
        y (int): L'année de la date.
        m (int): Le mois de la date.
        d (int): Le jour de la date.
    """
    url = f"https://www.20minutes.fr/archives/{y}/{m:02d}-{d:02d}/"
    soup = fetch_article(url)
    getArticleURL20min(soup)

def save_progress(year, month, day):
    """
    Sauvegarde la progression dans un fichier.
    
    Args:
        year (int): L'année à sauvegarder.
        month (int): Le mois à sauvegarder.
        day (int): Le jour à sauvegarder.
    """
    with open(PROGRESS_FILE, "w") as file:
        file.write(f"{year},{month},{day}")

def load_progress():
    """
    Charge la progression à partir du fichier de progression.
    
    Returns:
        date: La date de la dernière progression.
    """
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as file:
            progress = file.read().strip()
            if progress:
                year, month, day = map(int, progress.split(","))
                return date(year, month, day)
    return START_DATE # Date de départ


if __name__ == "__main__":
    start_date = load_progress()
    end_date = END_DATE
    driver = webdriver.Firefox(options=options)
    driver.get('https://www.20minutes.fr')
    current_date = start_date
    # Boucle à travers les dates, en récupérant les archives pour chaque date
    while current_date <= end_date:
        fetch_archives_20minutes(current_date.year,current_date.month,current_date.day)
        current_date += timedelta(days=1)
        save_progress(current_date.year, current_date.month, current_date.day)