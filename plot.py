import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

##### plot.py #####
# Ce Programme est conçu pour visualiser les biais politiques des journaux au fil du temps.
# Il charge les données étiquetées depuis deux fichiers CSV, calcule la moyenne mobile des scores de biais,
# et affiche un graphique comparatif des biais politiques par journal.
# Il utilise la bibliothèque Pandas pour la manipulation des données et Matplotlib pour la visualisation.


# Charger les données étiquetées depuis deux fichiers CSV (un pour chaque journal)
df = pd.read_csv("daily_with_bias_full_mini.csv")
df2 = pd.read_csv("nyt_with_bias_mini.csv")

window_size = 60  # Taille de la fenêtre pour la moyenne mobile
plt.figure(figsize=(12, 6))  # Créer une figure pour le graphique

# Boucle sur les deux DataFrames (un pour chaque journal)
for dframe in [df, df2]:
    # Vérifier que les colonnes nécessaires existent
    if 'date' not in dframe.columns or 'bias_label' not in dframe.columns:
        raise ValueError("Le DataFrame doit contenir les colonnes 'date' et 'bias_label'")
    if 'newspaper' not in dframe.columns:
        dframe['newspaper'] = 'Unknown'  # Ajouter une colonne 'newspaper' si elle n'existe pas
    dframe['date'] = pd.to_datetime(dframe['date'], errors='coerce')  # Convertir les dates
    dframe = dframe.dropna(subset=['date', 'bias_label'])  # Supprimer les lignes avec des valeurs manquantes
    dframe['bias_label'] = pd.to_numeric(dframe['bias_label'], errors='coerce')  # Convertir les labels en numérique
    dframe = dframe.dropna(subset=['bias_label'])  # Supprimer les lignes avec des labels manquants
    dframe = dframe.sort_values('date')  # Trier par date

    # Calculer la moyenne mobile par journal
    dframe['bias_ma'] = dframe.groupby('newspaper')['bias_label'].transform(
        lambda x: x.rolling(window=window_size, min_periods=1).mean()
    )
    # Lisser la courbe avec le filtre de Savitzky-Golay
    dframe['bias_smooth'] = savgol_filter(dframe['bias_ma'], window_length=2000, polyorder=4)

    # Récupérer le nom du journal pour la légende
    newspaper = dframe['newspaper'].iloc[0] if not dframe.empty else 'Unknown'
    # Tracer la courbe lissée
    plt.plot(dframe['date'], dframe['bias_smooth'], label=newspaper)

# Ajouter le titre et les labels du graphique
plt.title(f'Moyenne mobile sur {window_size} jours du biais politique par journal')
plt.xlabel('Date')
plt.ylabel('Score de biais (-3 : Extrême gauche, 3 : Extrême droite)')
plt.axhline(0, color='gray', linestyle='--', linewidth=2)  # Ligne de neutralité
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
