# -*- coding: utf-8 -*-
import os, time, csv
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from fake_useragent import UserAgent

# === Configuration du navigateur Firefox ===
options = Options()
ua = UserAgent()
options.add_argument("--disable-gpu")  # Désactive le GPU pour plus de stabilité
options.add_argument("--headless")     # Exécute le navigateur en mode headless (sans interface graphique)
options.set_preference("general.useragent.override", ua.random)  # Définit un user-agent aléatoire
options.add_argument("/home/melvil/snap/firefox/common/.cache/mozilla/firefox/n3ri59jd.default")  # Chemin du profil Firefox

PROGRESS_FILE = "progress.txt"            # Fichier pour sauvegarder la progression
ARTICLE_COUNT_FILE = "article_count.txt"  # Fichier pour compter les articles par date
OUTPUT_CSV = "LesEchos_scraped.csv"       # Fichier de sortie CSV

# === Initialisation du driver ===
def init_driver():
    """
    Initialise le navigateur Firefox avec les options définies.
    Retourne :
        driver (webdriver.Firefox) : Instance du navigateur Firefox.
    """
    driver = webdriver.Firefox(options=options)
    driver.get("https://www.lesechos.fr")  # Charge la page d'accueil pour initialiser les cookies
    return driver

# === Sauvegarde de la progression ===
def save_progress(year, month, page):
    """
    Sauvegarde la progression courante (année, mois, page) dans un fichier.
    """
    with open(PROGRESS_FILE, "w") as f:
        f.write(f"{year},{month},{page}")

def load_progress():
    """
    Charge la progression sauvegardée depuis le fichier, ou retourne la date de départ par défaut.
    Retourne :
        tuple (year, month, page)
    """
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            y, m, p = f.read().strip().split(',')
            return int(y), int(m), int(p)
    return 2015, 1, 1

# === Gestion du compteur journalier ===
def update_article_count(article_date):
    """
    Met à jour le compteur d'articles pour une date donnée.
    Args:
        article_date (str): Date de l'article au format 'jour mois année'
    Retourne :
        int : Nombre d'articles pour cette date après mise à jour
    """
    date_str = datetime.strptime(article_date, "%d %B %Y").strftime("%Y-%m-%d")
    counts = {}
    if os.path.exists(ARTICLE_COUNT_FILE):
        with open(ARTICLE_COUNT_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) == 2:
                    counts[parts[0]] = int(parts[1])
    counts[date_str] = counts.get(date_str, 0) + 1
    with open(ARTICLE_COUNT_FILE, 'w') as f:
        for k, v in counts.items():
            f.write(f"{k},{v}\n")
    return counts[date_str]

def get_article_count(article_date):
    """
    Retourne le nombre d'articles déjà enregistrés pour une date donnée.
    Args:
        article_date (str): Date de l'article au format 'jour mois année'
    Retourne :
        int : Nombre d'articles pour cette date
    """
    date_str = datetime.strptime(article_date, "%d %B %Y").strftime("%Y-%m-%d")
    if os.path.exists(ARTICLE_COUNT_FILE):
        with open(ARTICLE_COUNT_FILE, 'r') as f:
            for line in f:
                if line.startswith(date_str):
                    return int(line.strip().split(',')[1])
    return 0

# === Sauvegarde CSV ===
def save_to_csv(journal, title, date, desc, content):
    """
    Enregistre un article dans le fichier CSV de sortie.
    Args:
        journal (str): Nom du journal
        title (str): Titre de l'article
        date (str): Date de l'article
        desc (str): Description de l'article
        content (str): Texte complet de l'article
    """
    with open(OUTPUT_CSV, "a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([journal, title, date, desc, content])

# === Extraction d'un article complet ===
def get_article_content_lesechos(soup):
    """
    Extrait le contenu d'un article Les Echos à partir de la soupe BeautifulSoup.
    Args:
        soup (BeautifulSoup): La soupe de la page de l'article.
    Retourne :
        tuple ou None : (journal, titre, date, description, texte) ou None si extraction impossible
    """
    try:
        main_section = soup.find(class_="sc-1guqewj-0")
        if not main_section:
            return None

        article_section = main_section.find(class_="sc-dygkz8-0")
        if not article_section:
            return None

        if soup.find(class_="page__campaigns-img-wrapper"):
            return None  # Ignore les articles promotionnels

        title = article_section.find(class_="sc-1nfy22n-0")
        desc = article_section.find(class_="text")
        date = main_section.find(class_="sc-1h4katp-0")
        content_section = article_section.find(class_="sc-1s859o0-0")

        if not content_section:
            return None

        # Nettoyage du HTML (suppression des balises <a> et <em>)
        for a in soup.find_all("a"):
            a.insert_after(" ")
            a.unwrap()
        for em in soup.find_all("em"):
            em.insert_after(" ")
            em.unwrap()

        content = "\n".join(p.get_text(strip=True) for p in content_section.find_all("p", recursive=False))
        return (
            "Les Echos",
            title.get_text(strip=True) if title else "Titre indisponible",
            date.get_text(strip=True) if date else "Date inconnue",
            desc.get_text(strip=True) if desc else "",
            content
        )
    except Exception:
        return None

# === Chargement page HTML ===
def fetch_soup(driver, url):
    """
    Charge une page web et retourne la soupe BeautifulSoup correspondante.
    Args:
        driver (webdriver.Firefox): Instance du navigateur Firefox.
        url (str): URL à charger.
    Retourne :
        BeautifulSoup : La soupe de la page chargée.
    """
    driver.get(url)
    return BeautifulSoup(driver.page_source, "html.parser")

# === Traitement d'une page d'archives ===
def process_archive_page(driver, year, month, page):
    """
    Traite une page d'archives (liste d'articles) pour une année, un mois et une page donnés.
    Args:
        driver (webdriver.Firefox): Instance du navigateur Firefox.
        year (int): Année.
        month (int): Mois.
        page (int): Numéro de page.
    """
    url = f"https://www.lesechos.fr/{year}/{month:02d}/?page={page}"
    print(f"🔎 Traitement de {url}")
    soup = fetch_soup(driver, url)

    for card in soup.find_all(class_="sc-19z4l96-2"):
        a_tag = card.find("a")
        if not a_tag or "href" not in a_tag.attrs:
            continue
        article_url = "https://www.lesechos.fr" + a_tag["href"]

        article_soup = fetch_soup(driver, article_url)
        article = get_article_content_lesechos(article_soup)
        if not article:
            continue

        _, title, date_str, desc, text = article

        if get_article_count(date_str) >= 10:
            print(f"⏭️ Déjà 10 articles pour le {date_str}, on passe.")
            continue

        save_to_csv("Les Echos", title, date_str, desc, text)
        update_article_count(date_str)
        print(f"✅ Article sauvé : {title[:60]}...")

# === Boucle principale ===
def main():
    """
    Boucle principale du script : parcourt les années, mois et pages pour scraper les articles.
    """
    year, month, page = load_progress()
    driver = init_driver()

    try:
        for y in range(year, 2025):
            for m in range(month if y == year else 1, 13):
                for p in range(page if (y == year and m == month) else 1, 50):
                    save_progress(y, m, p)
                    process_archive_page(driver, y, m, p)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
