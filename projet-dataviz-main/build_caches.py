"""
Script de pré-chargement des caches de données pour l'application Streamlit.

Objectif :
- Télécharger / parser les données INSEE si nécessaire
- Construire tous les fichiers de cache utilisés par `DataCollector`
- Accélérer fortement le premier lancement de l'application

Important :
- Ce script NE modifie pas la logique métier.
- Il utilise les mêmes fonctions que l'app (`DataCollector`) et écrit
  uniquement dans le répertoire de cache configuré dans `config.py`.

Utilisation :
    python build_caches.py
"""

from time import perf_counter

from data_collector import get_data_collector
import config


def timed_step(label: str, func):
    """Exécute une étape en mesurant le temps et affiche un résumé."""
    print(f"\n▶ {label} ...")
    start = perf_counter()
    result = func()
    duration = perf_counter() - start
    if hasattr(result, "shape"):
        try:
            n_rows, n_cols = result.shape
            print(f"   ✅ Terminé en {duration:.1f}s - {n_rows:,} lignes, {n_cols} colonnes")
        except Exception:
            print(f"   ✅ Terminé en {duration:.1f}s")
    else:
        print(f"   ✅ Terminé en {duration:.1f}s")
    return result


def main():
    print("=== Pré-chargement des caches de données INSEE ===")
    print(f"Répertoire de cache configuré : {config.CACHE_DIR}")
    print(f"Répertoire des données brutes : {config.RAW_DATA_DIR}")

    collector = get_data_collector()

    # 1. Cache géographique (communes + coordonnées)
    geo_df = timed_step("Chargement / cache des données géographiques", collector.get_communes_geo_data)

    # 2. Population & ménages
    pop_df = timed_step("Chargement / cache des données de population", collector.get_population_data)

    # 3. Logements
    housing_df = timed_step("Chargement / cache des données de logement", collector.get_housing_data)

    # 4. Revenus
    income_df = timed_step("Chargement / cache des données de revenus", collector.get_income_data)

    # 5. Jeu de données fusionné utilisé par l'app
    all_df = timed_step("Construction / cache du DataFrame fusionné (all_data_merged)", collector.get_all_data)

    print("\n=== Résumé des caches construits ===")
    for label, df in [
        ("Géographie", geo_df),
        ("Population", pop_df),
        ("Logement", housing_df),
        ("Revenus", income_df),
        ("Données fusionnées", all_df),
    ]:
        try:
            n_rows, n_cols = df.shape
            print(f"- {label:17s} : {n_rows:,} lignes, {n_cols} colonnes")
        except Exception:
            print(f"- {label:17s} : (format non tabulaire)")

    print("\n✅ Pré-chargement terminé.")
    print("Au prochain lancement de l'application Streamlit, les données seront lues depuis les caches,")
    print("ce qui réduit fortement le temps de chargement initial.")


if __name__ == "__main__":
    main()

