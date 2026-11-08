"""Watts Demain — ML horaire, construction vectorisée des features.

À J14, prévoir chaque heure de J+1 avec la consommation jusqu’à J8,
la météo passée disponible à J14 et le calendrier connu de J+1.
Train 2012-2023, validation 2024, test 2025 non utilisé.

Important : les CSV peuvent avoir 24 lignes/jour même aux changements d'heure.
On conserve les lignes d'origine et on diagnostique les heures locales :
on masque les mesures des journées de transition sans supprimer de ligne.
"""
from pathlib import Path
from time import perf_counter
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
from protocole import enregistrer_execution, HEURE_COUPURE, masquer_transitions, disponibilite_meteo, jours_communs

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / 'data' / 'merge'
SORTIE = BASE / 'results' / 'analyse_2024' / 'ml'
CIBLE = 'consommation_MW'
CONSO = ['consommation_MW', 'consommation_00_MW', 'consommation_30_MW']
METEO = ['temperature_moyenne', 'temperature_ecart_type',
         'precipitation_moyenne', 'precipitation_ecart_type']
CALENDRIER = ['jour_changement_heure', 'lundi', 'mardi', 'mercredi',
              'jeudi', 'vendredi', 'samedi', 'dimanche', 'weekend',
              'jour_ferie', 'vacances_A', 'vacances_B', 'vacances_C',
              'vacances_scolaires']
NUMERIQUES = CONSO + METEO
RETARDS = [1, 7, 14, 28]  # relatifs à J (jour de lancement)


def charger(nom):
    """Charger sans rééchantillonnage ni suppression d'heures répétées."""
    df = pd.read_csv(DATA / nom, parse_dates=['horodatage'])
    absentes = [c for c in ['horodatage'] + NUMERIQUES + CALENDRIER if c not in df]
    if absentes:
        raise ValueError(f'{nom} : colonnes absentes : {absentes}')
    df['ordre_original'] = np.arange(len(df))
    df = df.sort_values(['horodatage', 'ordre_original'], kind='stable').reset_index(drop=True)

    # Évite FutureWarning de replace : traiter explicitement les booléens.
    for col in NUMERIQUES + CALENDRIER:
        serie = df[col]
        if pd.api.types.is_bool_dtype(serie):
            df[col] = serie.astype('int8')
        else:
            df[col] = pd.to_numeric(serie.astype('string').str.strip().str.lower()
                                    .map({'true': '1', 'false': '0'})
                                    .fillna(serie.astype('string').str.strip()),
                                    errors='coerce')
    df['jour'] = df['horodatage'].dt.normalize()
    df['heure_num'] = df['horodatage'].dt.hour
    df['occurrence'] = df.groupby('horodatage', sort=False).cumcount()
    if df[CIBLE].isna().any():
        raise ValueError(f'{nom} : consommation_MW manquante')
    df['date_utc'] = pd.to_datetime(df['date_utc'], utc=True)
    return masquer_transitions(df)


def diagnostic(df):
    """Afficher ce que les CSV contiennent réellement aux changements d'heure."""
    comptes = df.groupby('jour').size()
    print('\nNombre de lignes par journée :')
    print(comptes.value_counts().sort_index().to_string())
    print('Horodatages locaux répétés :', int(df['horodatage'].duplicated().sum()))
    if (df['occurrence'] > 1).any():
        raise ValueError('Plus de deux occurrences du même horodatage')
    anormaux = comptes[~comptes.isin([23, 24, 25])]
    if len(anormaux):
        raise ValueError(f'Journées hors 23/24/25 lignes : {anormaux.head(10)}')
    # Les deux dates officielles françaises de changement d'heure pour chaque année.
    for annee in sorted(df['jour'].dt.year.unique()):
        for mois in [3, 10]:
            fin = pd.Timestamp(annee, mois, 1) + pd.offsets.MonthEnd(0)
            dimanche = fin - pd.Timedelta(days=(fin.weekday() + 1) % 7)
            if dimanche in comptes.index:
                bloc = df.loc[df['jour'].eq(dimanche)]
                nb_2h = int(bloc['heure_num'].eq(2).sum())
                if nb_2h != (0 if mois == 3 else 2):
                    print(f'ATTENTION {dimanche.date()} : {len(bloc)} lignes, '
                          f'{nb_2h} observation(s) à 02 h. '
                          'La représentation horaire est peut-être normalisée.')


def creer_exemples(df, jours_cibles):
    """Construction RAPIDE : groupby/merge plutôt que filtrages pandas imbriqués.

    Chaque ligne de la cible D=J+1 reçoit :
    - calendrier de D ; heure et occurrence de l'heure cible ;
    - statistiques de J entre 00 h et 8 h ;
    - statistiques de J-1, J-7, J-14, J-28 ;
    - consommation du matin de J à chaque heure ;
    - valeurs de la même heure des jours historiques.
    Les consommations et météos observées de D ne sont JAMAIS utilisées en X.
    """
    jours_cibles = pd.DatetimeIndex(jours_cibles)
    cible = df.loc[df['jour'].isin(jours_cibles),
                   ['jour', 'horodatage', 'heure_num', 'occurrence', CIBLE] + CALENDRIER].copy()
    if len(cible) != int(df['jour'].isin(jours_cibles).sum()):
        raise AssertionError('Perte de lignes cibles')
    if cible.empty:
        raise ValueError('Aucune heure cible')
    presents = pd.DatetimeIndex(cible['jour'].unique())
    manquants = jours_cibles.difference(presents)
    if len(manquants):
        raise ValueError(f'Jours cibles absents : {manquants[:5].tolist()}')
    cible = cible.rename(columns={'jour': 'jour_cible', CIBLE: 'y_reel'})
    cible['jour_J'] = cible['jour_cible'] - pd.Timedelta(days=1)
    cible['mois'] = cible['jour_cible'].dt.month
    fraction = cible['jour_cible'].dt.dayofyear / 365.25
    cible['jour_annee_sin'] = np.sin(2 * np.pi * fraction)
    cible['jour_annee_cos'] = np.cos(2 * np.pi * fraction)
    cible['heure_cible'] = cible['heure_num']
    cible['heure_sin'] = np.sin(2 * np.pi * cible['heure_num'] / 24)
    cible['heure_cos'] = np.cos(2 * np.pi * cible['heure_num'] / 24)
    cible['occurrence_heure'] = cible['occurrence']
    # Note : calendrier déjà présent par ligne cible ; ne pas utiliser météo/conso de D.

    # 1. Statistiques par journée, calculées UNE SEULE FOIS pour toutes les heures.
    stats = df.groupby('jour')[NUMERIQUES].agg(['mean', 'min', 'max'])
    stats.columns = [f'{col}_{stat}' for col, stat in stats.columns]
    stats['nb_heures'] = df.groupby('jour').size()
    stats = stats.reset_index()

    # 2. Statistiques du matin J jusqu’à 8 h ; météo disponible à J14.
    matin = df.loc[df['heure_num'] <= HEURE_COUPURE].copy()
    origine_utc = (matin['jour'] + pd.Timedelta(hours=14)).dt.tz_localize('Europe/Paris').dt.tz_convert('UTC')
    disponible = disponibilite_meteo(matin['date_utc']) <= origine_utc
    matin.loc[~disponible, METEO] = np.nan
    # Les historiques J-1 et plus anciens sont connus à J14 (même borne conservatrice).
    prochaine_origine = (df['jour'] + pd.Timedelta(days=1, hours=14)).dt.tz_localize('Europe/Paris').dt.tz_convert('UTC')
    assert (df[METEO].isna().all(axis=1) | (disponibilite_meteo(df['date_utc']) <= prochaine_origine)).all()
    mat_stats = matin.groupby('jour')[NUMERIQUES].agg(['mean', 'min', 'max'])
    mat_stats.columns = [f'J_matin_{col}_{"moyenne" if stat == "mean" else stat}' for col, stat in mat_stats.columns]
    derniers = matin.groupby('jour', sort=False).tail(1).set_index('jour')
    for col in NUMERIQUES:
        mat_stats[f'J_matin_{col}_derniere'] = derniers[col]
    mat_stats = mat_stats.reset_index().rename(columns={'jour': 'jour_J'})
    cible = cible.merge(mat_stats, on='jour_J', how='left', validate='many_to_one', sort=False)

    # 3. Les 9 heures de consommation du matin J, pivotées UNE SEULE FOIS.
    # En cas de 02 h répétée, moyenne des occurrences pour la feature du matin.
    matin_par_heure = matin.groupby(['jour', 'heure_num'])[CONSO].mean().unstack('heure_num')
    matin_par_heure.columns = [f'J_{col}_h{h:02d}' for col, h in matin_par_heure.columns]
    # Garantit toutes les colonnes 00..08, même si une heure n'existe pas.
    colonnes_matin = [f'J_{col}_h{h:02d}' for col in CONSO for h in range(HEURE_COUPURE + 1)]
    matin_par_heure = matin_par_heure.reindex(columns=colonnes_matin)
    matin_par_heure.index.name = 'jour_J'
    cible = cible.merge(matin_par_heure.reset_index(), on='jour_J',
                        how='left', validate='many_to_one', sort=False)

    # 4. Historique par retard : 4 jointures journalières + 4 jointures horaires.
    # On construit une table indexée par jour + heure + occurrence UNE SEULE FOIS.
    historique_heure = df[['jour', 'heure_num', 'occurrence'] + NUMERIQUES].copy()
    for retard in RETARDS:
        cle = f'jour_historique_{retard}'
        cible[cle] = cible['jour_J'] - pd.Timedelta(days=retard)
        renommage_stats = {c: f'Jmoins{retard}_{c.replace("_mean", "_moyenne")}' for c in stats if c != 'jour'}
        bloc_stats = stats.rename(columns={'jour': cle, **renommage_stats})
        cible = cible.merge(bloc_stats, on=cle, how='left',
                            validate='many_to_one', sort=False)
        bloc_heure = historique_heure.rename(columns={
            'jour': cle, 'heure_num': 'heure_cible',
            'occurrence': 'occurrence_heure',
            **{c: f'Jmoins{retard}_{c}_meme_heure' for c in NUMERIQUES}
        })
        cible = cible.merge(bloc_heure, on=[cle, 'heure_cible', 'occurrence_heure'],
                            how='left', validate='many_to_one', sort=False)
        cible = cible.drop(columns=cle)

    # Vérification : aucune ligne perdue / ajoutée par les jointures.
    if len(cible) != int(df['jour'].isin(jours_cibles).sum()):
        raise ValueError('Les jointures ont changé le nombre de lignes cibles')
    if cible['J_matin_consommation_MW_moyenne'].isna().any():
        raise ValueError('Historique du jour J indisponible pour certaines cibles')

    meta = cible[['horodatage', 'occurrence_heure', 'jour_cible']].copy()
    y = cible['y_reel'].to_numpy(dtype=float)
    exclus = {'jour_cible', 'jour_J', 'horodatage', 'heure_num', 'occurrence', 'y_reel'}
    X = cible.drop(columns=list(exclus))
    # Les features restantes doivent être numériques (pas de timestamp ni de cible).
    if not all(pd.api.types.is_numeric_dtype(X[c]) for c in X.columns):
        raise TypeError('Feature non numérique détectée')
    return X, y, meta


def creer_modeles():
    """Utiliser les memes configurations en validation et en test."""
    return {
        'Regression lineaire': make_pipeline(
            SimpleImputer(strategy='median', keep_empty_features=True),
            StandardScaler(), LinearRegression()),
        'Ridge': make_pipeline(
            SimpleImputer(strategy='median', keep_empty_features=True),
            StandardScaler(), Ridge(alpha=100.0)),
        'Random Forest': make_pipeline(
            SimpleImputer(strategy='median', keep_empty_features=True),
            RandomForestRegressor(n_estimators=100, max_depth=15,
                                  min_samples_leaf=3, random_state=42, n_jobs=-1)),
        'Gradient Boosting': make_pipeline(
            SimpleImputer(strategy='median', keep_empty_features=True),
            GradientBoostingRegressor(n_estimators=80, learning_rate=0.08,
                                      max_depth=2, random_state=42)),
    }


def main():
    t0 = perf_counter()
    SORTIE.mkdir(parents=True, exist_ok=True)
    print('Chargement...', flush=True)
    train = charger('train.csv')
    val = charger('validation.csv')
    df = pd.concat([train, val], ignore_index=True)
    df = df.sort_values(['horodatage', 'ordre_original'], kind='stable').reset_index(drop=True)
    df['occurrence'] = df.groupby('horodatage', sort=False).cumcount()
    diagnostic(df)
    print(f'Chargement terminé en {perf_counter()-t0:.1f} s', flush=True)

    debut_train = train['jour'].min() + pd.Timedelta(days=30)
    # Exclure le 31 décembre : ses cibles tardives ne sont pas connues à la première origine.
    fin_train = val['jour'].min() - pd.Timedelta(days=2)
    jours_train = jours_communs(df, debut_train, fin_train)
    jours_val = jours_communs(df, val['jour'].min(), val['jour'].max())
    pd.Series(jours_val, name='jour').to_csv(SORTIE / 'jours_evalues.csv', index=False)
    print('\nCréation des features TRAIN...', flush=True)
    t = perf_counter()
    X_train, y_train, _ = creer_exemples(df, jours_train)
    print(f'TRAIN : {X_train.shape}, {perf_counter()-t:.1f} s', flush=True)
    print('Création des features VALIDATION...', flush=True)
    t = perf_counter()
    X_val, y_val, meta_val = creer_exemples(df, jours_val)
    print(f'VALIDATION : {X_val.shape}, {perf_counter()-t:.1f} s', flush=True)
    if len(y_val) != 24 * len(jours_val):
        raise ValueError('Une journée retenue ne contient pas 24 heures')
    if list(X_train.columns) != list(X_val.columns):
        raise ValueError('Features TRAIN et VALIDATION différentes')
    pd.Series(X_train.columns, name='feature').to_csv(SORTIE / 'liste_features.csv', index=False)

    modeles = creer_modeles()
    scores, toutes_previsions = [], []
    for nom, modele in modeles.items():
        print(f'\nEntraînement : {nom}...', flush=True)
        t = perf_counter()
        modele.fit(X_train, y_train)
        pred = modele.predict(X_val)
        mae = mean_absolute_error(y_val, pred)
        rmse = np.sqrt(mean_squared_error(y_val, pred))
        duree = perf_counter() - t
        print(f'{nom} : MAE={mae:.2f} MW ; RMSE={rmse:.2f} MW ; {duree:.1f} s', flush=True)
        scores.append({'modele': nom, 'MAE_MW': mae, 'RMSE_MW': rmse,
                       'temps_secondes': round(duree, 1), 'heures_evaluees': len(y_val)})
        resultat = meta_val.copy()
        resultat['modele'] = nom
        resultat['reel_MW'] = y_val
        resultat['prediction_MW'] = pred
        toutes_previsions.append(resultat)

    comparaison = pd.DataFrame(scores).sort_values('RMSE_MW')
    previsions = pd.concat(toutes_previsions, ignore_index=True)
    comparaison.to_csv(SORTIE / 'comparaison_ml_2024.csv', index=False)
    previsions.to_csv(SORTIE / 'previsions_ml_2024.csv', index=False)
    print('\n===== COMPARAISON ML : VALIDATION 2024 =====')
    print(comparaison.round(2).to_string(index=False))
    enregistrer_execution(SORTIE, __file__)
    print(f'\nRésultats enregistrés dans : {SORTIE}')
    print(f'Temps total : {perf_counter()-t0:.1f} s')


if __name__ == '__main__':
    main()
