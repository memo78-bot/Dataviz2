"""
Configuration file for Poubelles-Propres franchise zone analysis
"""

import os

# Project paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, 'processed')
CACHE_DIR = os.path.join(DATA_DIR, 'cache')
GEO_DIR = os.path.join(DATA_DIR, 'geo')

# Create directories if they don't exist
for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, CACHE_DIR, GEO_DIR]:
    os.makedirs(directory, exist_ok=True)

# INSEE API Configuration
INSEE_BASE_URL = "https://api.insee.fr/donnees-locales/V0.1"
INSEE_DOWNLOAD_BASE = "https://www.insee.fr/fr/statistiques/fichier"

# Dataset URLs (INSEE open data)
INSEE_DATASETS = {
    'population': 'https://www.insee.fr/fr/statistiques/fichier/7739582/base-cc-filosofi-2020.xlsx',
    'logements': 'https://www.insee.fr/fr/statistiques/fichier/7632867/BTT_TD_LOG_2020.zip',
    'revenus': 'https://www.insee.fr/fr/statistiques/fichier/7739582/base-cc-filosofi-2020.xlsx',
    'menages': 'https://www.insee.fr/fr/statistiques/fichier/7632867/BTT_TD_MEN_2020.zip',
}

# Geographic data
FRANCE_GEOJSON_URL = "https://france-geojson.gregoiredavid.fr/repo/communes.geojson"
DEPARTEMENTS_GEOJSON_URL = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"

# Target criteria for franchise zones
MIN_HOUSEHOLDS = 1000  # Reduced to 1000 to allow many more smaller zones
TARGET_CONVERSION_RATE = 0.02  # 2% conversion rate
MIN_CLIENTS = 20  # Reduced to allow very small zones

# Scoring weights (must sum to 1.0)
SCORING_WEIGHTS = {
    'housing_suitability': 0.30,  # % individual houses, % primary residences
    'demographics': 0.25,          # % retraités, % families with children, CSP+
    'income_level': 0.25,          # Median income vs national median
    'market_size': 0.20,           # Total eligible households
}

# Target demographics criteria
TARGET_CRITERIA = {
    'min_pct_maisons': 20,         # Reduced to 20% to include more zones
    'min_pct_residences_principales': 50,  # Reduced to 50% to include more communes
    'min_income_percentile': 0,    # No minimum to include all income levels
    'target_age_ranges': [(0, 17), (60, 100)],  # Children and retraités
}

# Zone clustering parameters  
MAX_ZONE_RADIUS_KM = 20  # 20km radius to allow better grouping of communes
MIN_COMMUNES_PER_ZONE = 2  # Require at least 2 communes per zone

# La Rochelle area example communes (for testing)
LA_ROCHELLE_COMMUNES = [
    'Puilboreau', 'Marsilly', 'Lagord', "L'Houmeau",
    'Périgny', 'Dompierre-sur-Mer', 'Saint-Xandre', 'Aytré'
]

# Map visualization settings
MAP_CENTER = [46.603354, 1.888334]  # Center of France
MAP_ZOOM = 6
HEATMAP_COLORS = ['#2E7D32', '#66BB6A', '#FDD835', '#FB8C00', '#E53935']  # Green to Red

# Cache settings
CACHE_EXPIRY_DAYS = 7  # Cache data for 7 days
