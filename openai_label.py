import pandas as pd
import asyncio
import aiohttp
from tqdm import tqdm
import nest_asyncio
import tiktoken
import time

### openai_label.py ###
# Ce script utilise l'API OpenAI pour classifier des articles de presse en fonction de leur biais politique.
# Il charge un fichier CSV contenant des articles, envoie des requêtes à l'API OpenAI pour chaque article,
# et enregistre les résultats dans un nouveau fichier CSV.
# Il utilise asyncio pour gérer les requêtes asynchrones et respecter les limites de tokens par minute (TPM).

# Autorise les boucles d'événements imbriquées (utile pour les notebooks ou exécutions répétées)
nest_asyncio.apply()

# Constantes pour l'API OpenAI
OPENAI_API_KEY = ""
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4.1-mini"  # Ou gpt-3.5-turbo pour un modèle plus rapide/économique

# Charge le fichier CSV contenant les articles à annoter
df = pd.read_csv("articles_monde_formatted_cleaned.csv")
df.head(10000)

TPM_LIMIT = 100_000  # Limite de tokens par minute pour l'API (à ajuster selon votre quota)
encoding = tiktoken.encoding_for_model("gpt-4o") # Chargement de l'encodeur de tokens pour le modèle GPT-4o

# Définition du prompt système pour guider le modèle OpenAI
SYSTEM_PROMPT = (
    """You are a political ideology classifier. Given a news article (title, description, and full content), return a single number that represents the ideological stance of the article on a continuous scale from -3 to 3.

The scale:
-3.0: Strongly left-leaning
-1.0: Slightly left-leaning
 0.0: Neutral or balanced
 1.0: Slightly right-leaning
 3.0: Strongly right-leaning

You may return **decimal numbers**, e.g., -1.3 or 2.7 or 0.1. It can be every number in between -3 and 3 ! Do not round or simplify. Do not say “left” or “right” — only return a numeric value.
Consider tone, framing, language, implications, and underlying perspective.
"""
)
# Modèle de prompt utilisateur pour chaque article
USER_PROMPT_TEMPLATE = (
    "Title: {title}\n"
    "Description: {desc}\n"
    "Content: {content}"
)

# Fonction pour estimer le nombre de tokens utilisés par un texte
def estimate_tokens(text: str) -> int:
    return len(encoding.encode(text))


# Fonction asynchrone pour appeler l'API OpenAI et classifier un article
async def classify_article(session, title, desc, content):
    prompt = USER_PROMPT_TEMPLATE.format(
        title=str(title or ""),
        desc=str(desc or ""),
        content=str(content or "")
    )
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    json_payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }
    async with session.post(OPENAI_API_URL, headers=headers, json=json_payload) as resp:
        result = await resp.json()
        print(f"Response: {result}")
        label = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        print(f"Bias: {label}")
        return label, estimate_tokens(prompt)


# Fonction asynchrone pour traiter les articles par batch et respecter la limite de tokens par minute
async def batch_classify(rows, batch_size=10):
    results = []
    token_accumulator = 0
    window_start = time.time()

    async with aiohttp.ClientSession() as session:
        for i in tqdm(range(0, len(rows), batch_size)):
            batch = rows[i:i + batch_size]
            tasks = []
            for _, row in batch.iterrows():
                tasks.append(classify_article(session, row["title"], row["desc"], row["content"]))
            batch_results = await asyncio.gather(*tasks)

            for j, (label, tokens_used) in enumerate(batch_results):
                results.append(label)
                token_accumulator += tokens_used
                print(f"[{i + j}] Bias: {label} | Tokens: {tokens_used} | Accumulated: {token_accumulator}")

            # Vérifie si la limite TPM est atteinte et attend si nécessaire
            elapsed = time.time() - window_start
            if token_accumulator >= TPM_LIMIT:
                sleep_time = 60 - elapsed
                if sleep_time > 0:
                    print(f"Sleeping for {sleep_time:.1f} seconds to respect TPM limit...")
                    await asyncio.sleep(sleep_time)
                token_accumulator = 0
                window_start = time.time()

    return results

# Lance la classification des articles et ajoute les labels au DataFrame
bias_labels = asyncio.run(batch_classify(df, batch_size=10))
df["bias_label"] = bias_labels

# Sauvegarde le DataFrame annoté dans un nouveau fichier CSV
df.to_csv("monde_with_bias_mini.csv", index=False)

# Calcule et affiche le biais moyen des articles annotés
df["bias_score"] = pd.to_numeric(df["bias_label"], errors="coerce")
valid_scores = df["bias_score"].dropna()
mean_bias = valid_scores.mean()
print(f"\n🧭 Mean bias score: {mean_bias:.3f}")
