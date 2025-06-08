import pandas as pd
from sklearn.model_selection import train_test_split

### fine_tune.py ###
# Ce script fine-tune un modèle de classification de texte sur un dataset d'articles annotés avec des labels de biais.
# Il utilise la bibliothèque HuggingFace Transformers pour le modèle et le tokenizer.
# Il utilise le modèle XLM-Roberta, qui est adapté pour la classification de texte multilingue.

# Chemin du fichier CSV contenant les articles et les labels de biais
CSV_FILE = "nyt_with_bias_mini.csv"

# Lecture du fichier CSV dans un DataFrame pandas
df = pd.read_csv(CSV_FILE)
# Suppression des lignes où 'bias_label' ou 'content' est manquant
df = df.dropna(subset=["bias_label", "content"])

# Garde uniquement les lignes où 'bias_label' n'est pas vide
df = df[df['bias_label'].notna() & (df['bias_label'] != "")]

# Convertit la colonne 'bias_label' en entier (supposé déjà entre -3 et 3)
df["bias_label"] = df["bias_label"].astype(int)

# Remappe les valeurs de -3 à 3 en 0 à 6 pour la classification
df["class_label"] = df["bias_label"] + 3

# Sépare les données en ensembles d'entraînement et de validation (stratifié par classe)
train_texts, val_texts, train_labels, val_labels = train_test_split(
    df["content"].tolist(),
    df["class_label"].tolist(),
    test_size=0.2, # 20% pour la validation
    stratify=df["class_label"]
)

from transformers import AutoTokenizer
from torch.utils.data import Dataset

# Charge le tokenizer XLM-Roberta
tokenizer = AutoTokenizer.from_pretrained("xlm-roberta-base", use_fast=True)

# Dataset personnalisé pour les articles
class ArticleDataset(Dataset):
    def __init__(self, texts, labels):
        # Tokenisation des textes avec padding et troncature
        self.encodings = tokenizer(texts, truncation=True, padding=True, max_length=512)
        self.labels = labels

    def __len__(self):
        # Retourne le nombre d'exemples
        return len(self.labels)

    def __getitem__(self, idx):
        # Retourne un exemple sous forme de dictionnaire pour PyTorch
        item = {key: val[idx] for key, val in self.encodings.items()}
        item["labels"] = self.labels[idx]
        return item

# Création des datasets d'entraînement et de validation
train_dataset = ArticleDataset(train_texts, train_labels)
val_dataset = ArticleDataset(val_texts, val_labels)

from transformers import AutoModelForSequenceClassification, Trainer, TrainingArguments
import torch

# Charge le modèle XLM-Roberta pour la classification de séquence avec 7 classes
model = AutoModelForSequenceClassification.from_pretrained("xlm-roberta-base", num_labels=7)
# Limite la mémoire GPU utilisée à 90% (optionnel, dépend du matériel)
torch.cuda.set_per_process_memory_fraction(0.9, device=0)

# Définition des arguments d'entraînement
training_args = TrainingArguments(
    output_dir="./results",            # Dossier de sortie pour les checkpoints
    eval_strategy="epoch",             # Évaluation à chaque époque
    save_strategy="epoch",             # Sauvegarde à chaque époque
    per_device_train_batch_size=4,     # Taille de batch pour l'entraînement
    per_device_eval_batch_size=4,      # Taille de batch pour l'évaluation
    num_train_epochs=3,                # Nombre d'époques
    learning_rate=2e-5,                # Taux d'apprentissage
    weight_decay=0.01,                 # Décroissance du poids
    logging_dir="./logs",              # Dossier pour les logs
    report_to="none",                  # Désactive les rapports externes
)

# Création de l'objet Trainer de HuggingFace
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
)

# Lance l'entraînement du modèle
trainer.train()
# Sauvegarde le modèle fine-tuné
trainer.save_model("./fine_tuned_model")