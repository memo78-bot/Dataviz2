"""
Script pour générer le Top 50 des communes françaises par potentiel business
Usage: python generate_top50_communes.py
"""

import pandas as pd
from data_collector import get_data_collector
import utils
import config


def calculate_commune_score(row, weights={'housing': 0.25, 'income': 0.50, 'market': 0.25}):
    """
    Calcule le score business d'une commune individuelle

    Args:
        row: Ligne DataFrame avec les données de la commune
        weights: Pondération des critères

    Returns:
        Score total (0-100)
    """
    # Score Logement (0-100)
    score_housing = (
        (row['pct_maisons'] / 100) * 0.6 +
        (row['pct_residences_principales'] / 100) * 0.4
    ) * 100

    # Score Revenus (0-100)
    revenu_national = 26000  # Approximation médiane France 2024
    score_income = (
        min(row['revenu_median'] / (revenu_national * 1.5), 1) * 0.7 +
        max(0, (100 - row.get('taux_pauvrete', 14)) / 100) * 0.3
    ) * 100

    # Score Taille Marché (échelle log)
    import math
    score_market = min(100, (math.log(row['nb_menages'] + 1) / math.log(50000)) * 100)

    # Score total pondéré
    score_total = (
        score_housing * weights['housing'] +
        score_income * weights['income'] +
        score_market * weights['market']
    )

    return {
        'score_housing': round(score_housing, 1),
        'score_income': round(score_income, 1),
        'score_market': round(score_market, 1),
        'score_total': round(score_total, 1)
    }


def generate_top50_communes():
    """Génère le Top 50 des communes françaises"""

    print("🔄 Chargement des données INSEE...")
    collector = get_data_collector()
    data = collector.get_all_data()

    # Ajout région
    data = data.copy()
    if 'code_departement' in data.columns:
        data['region'] = data['code_departement'].apply(utils.get_region_from_department)

    print(f"✅ {len(data)} communes chargées")

    # Filtres business (critères stricts)
    print("\n🔍 Application des filtres business...")
    filtered = data[
        (data['pct_maisons'] >= 50) &  # Zone pavillonnaire
        (data['pct_residences_principales'] >= 70) &  # Résidents permanents
        (data['nb_menages'] >= 1000) &  # Taille minimale
        (data['revenu_median'] >= 24000)  # Revenus confortables
    ].copy()

    print(f"✅ {len(filtered)} communes éligibles")

    # Calcul des scores
    print("\n📊 Calcul des scores...")
    scores = filtered.apply(lambda row: calculate_commune_score(row), axis=1, result_type='expand')
    filtered = pd.concat([filtered, scores], axis=1)

    # Tri par score total
    top50 = filtered.nlargest(50, 'score_total').reset_index(drop=True)
    top50['rank'] = range(1, 51)

    # Calcul clients potentiels
    top50['potential_clients'] = (top50['nb_menages'] * config.TARGET_CONVERSION_RATE).astype(int)

    print("✅ Top 50 calculé\n")

    # Affichage résumé
    print("=" * 80)
    print("🏆 TOP 50 COMMUNES - POTENTIEL BUSINESS POUBELLES-PROPRES")
    print("=" * 80)
    print(f"\n{'Rang':<6} {'Commune':<30} {'Région':<20} {'Score':<8} {'Clients Pot.'}")
    print("-" * 80)

    for idx, row in top50.head(20).iterrows():  # Afficher top 20 dans console
        print(f"{row['rank']:<6} {row['nom_commune'][:28]:<30} {row['region'][:18]:<20} "
              f"{row['score_total']:<8.1f} {utils.format_number(row['potential_clients'], 0)}")

    print("\n... (voir fichier CSV pour le Top 50 complet)")

    # Export CSV
    output_file = 'top50_communes_poubelles_propres.csv'

    export_cols = [
        'rank', 'nom_commune', 'code_commune', 'code_departement', 'region',
        'nb_menages', 'population_totale', 'potential_clients',
        'pct_maisons', 'pct_residences_principales', 'revenu_median',
        'score_housing', 'score_income', 'score_market', 'score_total',
        'latitude', 'longitude'
    ]

    top50[export_cols].to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n✅ Export réussi : {output_file}")

    # Statistiques
    print("\n" + "=" * 80)
    print("📈 STATISTIQUES TOP 50")
    print("=" * 80)
    print(f"Score moyen         : {top50['score_total'].mean():.1f}/100")
    print(f"Ménages totaux      : {utils.format_number(top50['nb_menages'].sum())}")
    print(f"Clients potentiels  : {utils.format_number(top50['potential_clients'].sum(), 0)}")
    print(f"Régions représentées: {top50['region'].nunique()}")
    print("\nTop 3 régions :")
    for region, count in top50['region'].value_counts().head(3).items():
        print(f"  - {region}: {count} communes")

    return top50


if __name__ == "__main__":
    top50 = generate_top50_communes()
    print("\n🎉 Terminé !")
