# 🗑️ Poubelles-Propres - Analyse de Zones de Franchise

Application d'analyse géographique pour identifier et prioriser les zones de chalandise potentielles pour le développement de franchises Poubelles-Propres en France.

## 📋 Vue d'ensemble

Cette application utilise des données réelles de l'INSEE pour analyser l'ensemble du territoire français et identifier les zones les plus prometteuses pour l'implantation de franchises. Elle regroupe les communes en zones géographiques cohérentes et les évalue selon plusieurs critères clés.

## 🎯 Méthodologie de Création des Zones

### Regroupement Géographique

1. **Identification des centres** : Les communes de 1000+ habitants servent de centres de zones
2. **Attribution par proximité** : Chaque commune éligible est rattachée au centre le plus proche (rayon max 15-20 km)
3. **Zones uniques** : Chaque commune appartient à une seule zone (pas de chevauchement)
4. **Agrégation** : Les données sont agrégées au niveau de la zone pour obtenir des statistiques consolidées

### Critères d'Éligibilité

Une commune est éligible si elle remplit ces critères minimums :
- **≥ 20%** de maisons individuelles (vs appartements)
- **≥ 50%** de résidences principales (vs secondaires)
- **≥ 100** ménages

Une zone est retenue après agrégation si :
- **≥ 50%** de maisons individuelles en moyenne
- **≥ 70%** de résidences principales
- **≥ 2** communes dans la zone

## 📊 Système de Scoring

Chaque zone reçoit un **score total sur 100** basé sur 3 composantes principales.

### ⚙️ Pondération Personnalisable

Vous pouvez maintenant **ajuster les pondérations** directement dans l'interface pour adapter le scoring à votre stratégie :

**Presets disponibles** :

| Preset | Logement | Revenus | Taille | Stratégie |
|--------|----------|---------|--------|-----------|
| **Classique** | 40% | 30% | 30% | Configuration par défaut, priorité légère au logement |
| **Équilibré** | 33% | 33% | 34% | Importance égale pour tous les critères |
| **Focus Logement** | 60% | 20% | 20% | Zones résidentielles pavillonnaires |
| **Focus Revenus** | 20% | 60% | 20% | Zones aisées à fort pouvoir d'achat |
| **Focus Taille** | 20% | 20% | 60% | Grandes zones urbaines, volume maximal |
| **Marché** | 20% | 30% | 50% | Stratégie chiffre d'affaires (volume + revenus) |
| **Personnalisé** | - | - | - | Ajustement manuel précis (total = 100%) |

**Caractéristiques** :
- **Validation stricte** : L'analyse ne démarre que lorsque le total = 100%
- **Champs désactivés** : Les pondérations sont verrouillées lors de l'utilisation d'un preset
- **Mode Personnalisé** : Débloquez les champs pour ajuster manuellement les pondérations

**Guide de sélection** :
- Utilisez **Classique** pour un équilibre traditionnel favorisant le logement
- Utilisez **Équilibré** pour donner la même importance à tous les critères
- Utilisez **Focus Logement** si vous ciblez des zones résidentielles pavillonnaires
- Utilisez **Focus Revenus** si vous ciblez des zones aisées
- Utilisez **Focus Taille** si vous privilégiez le volume et les grandes zones
- Utilisez **Marché** pour une stratégie orientée chiffre d'affaires (volume + revenus)
- Utilisez **Personnalisé** pour une stratégie sur-mesure

### 🏠 Score Logement (par défaut 40%)

**Objectif** : Évaluer l'adéquation du parc immobilier avec le service

**Calcul** :
- **Score maisons individuelles** (60%) : Normalisation du % de maisons
  - Plus il y a de maisons individuelles, meilleur c'est
  - Les maisons ont des poubelles individuelles à gérer
  
- **Score résidences principales** (40%) : Normalisation du % de résidences principales  
  - Les résidences principales sont des clients réguliers
  - Les résidences secondaires génèrent moins de demande

**Formule** :
```
Score_Logement = (Score_Maisons × 0.6) + (Score_ResidencesPrincipales × 0.4)
```

**Normalisation** : Les valeurs sont normalisées entre le min et max observés dans toutes les zones

---

### 💰 Score Revenus (par défaut 30%)

**Objectif** : Mesurer le pouvoir d'achat et la capacité à payer le service

**Calcul** :
- **Score revenu médian** (70%) : Comparaison au revenu national
  - Borne basse : 80% du revenu médian national
  - Borne haute : 150% du revenu médian national
  - Les zones avec revenus plus élevés sont favorisées
  
- **Pénalité pauvreté** (30%) : Impact du taux de pauvreté
  - Normalisation inversée (moins de pauvreté = meilleur score)
  - Balance l'effet du revenu médian

**Formule** :
```
Score_Revenus = (Score_RevenuMédian × 0.7) + (Score_AntiPauvreté × 0.3)
```

---

### 📈 Score Taille du Marché (par défaut 30%)

**Objectif** : Évaluer le potentiel commercial en termes de volume d'affaires

**Calcul** :
- Basé sur le **nombre de ménages** dans la zone
- Utilise une **échelle logarithmique** pour éviter que les très grandes zones écrasent les autres
- Plus de ménages = potentiel commercial plus important

**Formule** :
```
Score_TailleMaché = normalize(log(nb_ménages + 1))
```

La normalisation se fait entre :
- Borne basse : log(500) - minimum de ménages attendu
- Borne haute : log(max_ménages_observé)

---

### 🎯 Score Total Final

Le **score total** est la somme pondérée des 3 composantes :

```
Score_Total = (Score_Logement × W_Logement) +
              (Score_Revenus × W_Revenus) +
              (Score_TailleMaché × W_Taille)

où W_Logement + W_Revenus + W_Taille = 1.0 (100%)
```

**Pondération par défaut (Équilibré)** :
- 40% - Logement : Critère le plus important (adéquation du parc immobilier)
- 30% - Revenus : Important pour la viabilité économique
- 30% - Taille : Important pour le volume d'affaires

**Ces pondérations sont entièrement personnalisables** dans l'interface pour s'adapter à votre stratégie commerciale.

### Interprétation des Scores

| Score | Catégorie | Signification |
|-------|-----------|---------------|
| 80-100 | 🟢 Excellent | Zone prioritaire, potentiel maximal |
| 60-80 | 🟢 Très bon | Zone très attractive |
| 40-60 | 🟡 Bon | Zone prometteuse avec bon potentiel |
| 20-40 | 🟠 Moyen | Zone à considérer selon la stratégie |
| 0-20 | 🔴 Faible | Zone peu prioritaire |

## 📊 Sources de Données

### Données INSEE

- **Population et Ménages** : Base logement 2021 (INSEE)
  - Nombre de ménages par commune
  - Population totale (estimée à 2.2 personnes/ménage)
  
- **Logements** : Base logement 2021 (INSEE)
  - Types de logements (maisons vs appartements)
  - Résidences principales vs secondaires
  
- **Revenus** : Niveau de vie 2013 par commune (DGFiP)
  - Revenu médian par commune
  - Niveau de vie médian
  - Taux de pauvreté

### Données Géographiques

- GeoJSON des communes françaises
- Coordonnées GPS (latitude/longitude)
- Codes et noms des communes
- Régions et départements

## 🚀 Installation et Utilisation

### Prérequis

```bash
Python 3.8+
pip install -r requirements.txt
```

### Données INSEE

Les datasets INSEE sont inclus dans le repository sous forme de fichiers ZIP compressés pour respecter la limite de taille de GitHub. Ils seront **automatiquement extraits** au premier lancement de l'application.

Aucune action manuelle requise ! 🎉

### Lancement

```bash
streamlit run app.py
```

Au premier lancement, vous verrez:
```
📦 Extraction de base-cc-emploi-pop-active-2020.zip...
✓ base-cc-emploi-pop-active-2020_v2.CSV extrait avec succès
📦 Extraction de base-cc-logement-2021.zip...
✓ base-cc-logement-2021.CSV extrait avec succès
```

L'application sera accessible sur `http://localhost:8501`

### Configuration

Modifiez `config.py` pour ajuster :
- Rayon maximum des zones (défaut : 15 km)
- Nombre minimum de ménages par zone (défaut : 500)
- Critères de filtrage
- Taux de conversion estimé pour le calcul des clients potentiels

## 📁 Structure du Projet

```
.
├── app.py                    # Application Streamlit principale
├── config.py                 # Configuration et paramètres
├── data_collector.py         # Collecte et cache des données INSEE
├── simple_insee_parser.py    # Parsing des fichiers INSEE
├── zone_analyzer.py          # Logique de création et scoring des zones
├── map_viz.py                # Visualisations cartographiques
├── utils.py                  # Fonctions utilitaires
├── data/
│   ├── raw/                  # Données brutes INSEE
│   └── cache/                # Cache des données traitées
└── README.md                 # Ce fichier
```

## 🔧 Fonctionnalités

### Interface Interactive

- **Vue d'ensemble** : Métriques clés et visualisations
  - Statistiques globales (zones, scores, ménages, clients potentiels)
  - Distribution des scores
  - Répartition par région
  - **Moyennes par région** avec graphiques et tableaux détaillés
  - Comparaison des composantes de score par région
  - Top 20 zones
- **Carte Interactive** : Visualisation géographique des zones avec 3 types de cartes
  - Carte Folium avec marqueurs et tooltips (affichage des communes)
  - Carte scatter Plotly avec informations détaillées
  - Heatmap de densité
- **Top Zones** : Détails approfondis des meilleures zones
- **Analyses** : Corrélations et relations entre variables
  - Pondération du scoring (graphique camembert)
  - Matrice de corrélation des composantes
  - Scatter plots revenus vs score et maisons vs score
  - Export CSV complet

### Filtrage et Personnalisation Dynamique

**Paramètres de zone** :
- Ajustement du rayon de zone (10-50 km)
- Seuil de ménages minimum
- Pourcentage de maisons minimum
- Niveau de revenu minimum

**Pondération du scoring personnalisable** :
- 6 presets prédéfinis (Classique, Équilibré, Focus Logement, Focus Revenus, Focus Taille, Marché)
- Mode personnalisé avec contrôle précis au pourcentage près
- Validation stricte : total doit = 100% pour lancer l'analyse
- Champs désactivés lors de l'utilisation d'un preset (sélection claire)
- Barre de progression visuelle
- Recalcul automatique des scores en temps réel

### Export de Données

- Export CSV complet avec toutes les métriques
- Données prêtes pour analyse externe

## 📈 Métriques Calculées

Pour chaque zone identifiée :

- **Géographie** : Région, département, nombre de communes
- **Population** : Population totale, nombre de ménages
- **Logement** : % maisons, % résidences principales
- **Revenus** : Revenu médian, taux de pauvreté
- **Scores** : Score logement, revenus, taille marché, score total
- **Potentiel** : Estimation du nombre de clients potentiels

## 🎯 Estimation des Clients Potentiels

```
Clients Potentiels = Nombre de Ménages × Taux de Conversion
```

**Taux de conversion par défaut** : 2% (configurable)

Ce taux représente l'estimation du pourcentage de ménages qui pourraient devenir clients.

## 💡 Conseils d'Utilisation

1. **Commencez large** : Utilisez des critères souples pour voir toutes les possibilités
2. **Affinez progressivement** : Ajustez les filtres selon votre stratégie
3. **Analysez par région** : Certaines régions peuvent être plus prometteuses
4. **Comparez les scores** : Les top 20-30 zones méritent une attention particulière
5. **Considérez la géographie** : La proximité entre zones peut influencer la stratégie

## 📝 Notes Techniques

### Cache des Données

Les données INSEE sont mises en cache après le premier chargement pour accélérer les utilisations ultérieures. Le cache expire après 30 jours.

Pour forcer un rechargement :
```bash
rm -rf data/cache/*
```

### Performance

- Traitement de ~35 000 communes
- Création de 4 000+ zones potentielles
- Temps de calcul initial : ~30-60 secondes
- Temps de calcul avec cache : ~5-10 secondes

---

**Développé pour Poubelles-Propres.fr**  
*Analyse basée sur données INSEE & DGFiP*
