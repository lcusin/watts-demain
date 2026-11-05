"""Analyse simple de la consommation horaire sur le TRAIN uniquement."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

BASE = Path(__file__).resolve().parent.parent
SORTIE = BASE / 'data_temp' / 'graphiques' / 'modelisation_horaire'
SORTIE.mkdir(parents=True, exist_ok=True)

def charger(nom):
    df = pd.read_csv(BASE / 'data' / 'processed' / nom, parse_dates=['horodatage'])
    # Une observation par heure : vérifier les doublons et les heures absentes.
    if df['horodatage'].duplicated().any():
        raise ValueError('Horodatages en double : vérifier le changement d’heure et le fuseau horaire.')
    s = df.set_index('horodatage')['consommation_MW'].sort_index().astype(float).asfreq('h')
    if s.isna().any() or not np.isfinite(s).all():
        raise ValueError('Heures ou consommations manquantes : vérifier les données avant modélisation.')
    return s

serie = charger('train.csv')
# Différence hebdomadaire : 7 jours x 24 heures = 168 heures.
diff168 = serie.diff(168).dropna()
print('Nombre d’heures train :', len(serie))

for nom, s in [('brute', serie), ('difference_168h', diff168)]:
    fig, axes = plt.subplots(1, 2, figsize=(14, 4))
    plot_acf(s, lags=336, zero=False, ax=axes[0])
    # PACF limitée à 48 retards pour éviter un calcul inutilement long.
    plot_pacf(s, lags=48, zero=False, method='ywm', ax=axes[1])
    axes[0].set_title(f'ACF - {nom} (retards en heures)')
    axes[1].set_title(f'PACF - {nom} (retards en heures)')
    fig.tight_layout()
    fig.savefig(SORTIE / f'acf_pacf_{nom}.png', dpi=180)
    plt.close(fig)
print('Graphiques enregistrés dans', SORTIE)
