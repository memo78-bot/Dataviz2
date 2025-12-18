"""
Zone analysis and scoring module
Handles grouping of communes into zones and scoring them based on franchise criteria
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from sklearn.cluster import DBSCAN
from scipy.spatial import cKDTree
import config
import utils
import streamlit as st


class ZoneAnalyzer:
    """Analyzes and scores potential franchise zones"""
    
    def __init__(self, data: pd.DataFrame):
        """
        Initialize analyzer with commune data
        
        Args:
            data: DataFrame with commune-level data including demographics, housing, income, and geographic info
        """
        self.data = data.copy()
        self.zones = None
        self.scored_zones = None
        
        # Calculate national statistics for benchmarking
        self.national_median_income = self.data['revenu_median'].median()
        self.national_median_houses_pct = self.data['pct_maisons'].median()
        
    def filter_eligible_communes(self) -> pd.DataFrame:
        """
        Filter communes that meet basic eligibility criteria
        
        RELAXED filtering: We apply minimal criteria at commune level,
        then apply strict criteria at ZONE level after aggregation.
        This allows more communes to participate in zone formation.
        
        Returns:
            DataFrame with eligible communes
        """
        eligible = self.data[
            # Very minimal criteria - just need some houses and households
            (self.data['pct_maisons'] >= 20) &  # At least 20% houses (vs 50% before)
            (self.data['pct_residences_principales'] >= 50) &  # At least 50% primary residences
            (self.data['nb_menages'] >= 100)  # At least 100 households to be meaningful
        ].copy()
        
        return eligible
    
    def create_zones(self, max_radius_km: float = None) -> pd.DataFrame:
        """
        Group eligible communes into geographic zones using city-centered approach (OPTIMIZED with KD-Tree)

        Strategy:
        1. Identify cities with 1000+ inhabitants as zone centers
        2. For each eligible commune, find nearest city center within max_radius_km
        3. Assign commune to that zone (NO OVERLAP - each commune in ONE zone only)
        4. Each zone is scored separately

        Optimization: Uses KD-Tree for O(log n) nearest neighbor search instead of O(n)
        This reduces computation from ~35 million distance calculations to ~100k tree queries

        Args:
            max_radius_km: Maximum radius for zone (default 15km)

        Returns:
            DataFrame with zone assignments
        """
        if max_radius_km is None:
            max_radius_km = 15  # Default 15km radius

        # Get eligible communes (those meeting basic criteria)
        eligible = self.filter_eligible_communes()

        if len(eligible) == 0:
            return pd.DataFrame()

        # Identify city centers (communes with 1000+ inhabitants)
        city_centers = eligible[eligible['population_totale'] >= 1000].copy()

        if len(city_centers) == 0:
            # If no cities with 1000+ population, use top communes by population
            city_centers = eligible.nlargest(100, 'population_totale').copy()

        # OPTIMIZED APPROACH: Use KD-Tree for fast nearest neighbor search
        # Convert lat/lon to radians for spherical distance calculation
        center_coords = np.radians(city_centers[['latitude', 'longitude']].values)
        center_names = city_centers['nom_commune'].values

        # Build KD-Tree (one-time cost, enables fast queries)
        try:
            tree = cKDTree(center_coords)
        except Exception as e:
            st.warning(f"⚠️ KD-Tree construction failed, using fallback method: {e}")
            return self._create_zones_fallback(eligible, city_centers, max_radius_km)

        # Progress tracking (optional - only works in Streamlit context)
        try:
            progress_bar = st.progress(0)
            progress_text = st.empty()
            has_progress = True
        except:
            has_progress = False

        commune_assignments = []
        total_communes = len(eligible)

        # Convert max_radius to angular distance (radians)
        # Approximate: 1 degree ≈ 111 km at equator
        max_radius_rad = max_radius_km / 6371.0  # Earth radius in km

        # Batch process communes for better performance
        commune_coords = np.radians(eligible[['latitude', 'longitude']].values)

        # Query tree for all communes at once (MASSIVE SPEEDUP)
        try:
            distances, indices = tree.query(commune_coords, k=1, distance_upper_bound=max_radius_rad)
        except Exception as e:
            st.warning(f"⚠️ KD-Tree query failed, using fallback method: {e}")
            return self._create_zones_fallback(eligible, city_centers, max_radius_km)

        # Process results
        for idx, (_, commune) in enumerate(eligible.iterrows()):
            # Update progress (optional)
            if has_progress and idx % 500 == 0:
                try:
                    progress = idx / total_communes
                    progress_bar.progress(progress)
                    progress_text.text(f"⚡ Attribution rapide: {idx}/{total_communes}")
                except:
                    pass

            # Check if a center was found within radius
            if indices[idx] < len(city_centers) and not np.isinf(distances[idx]):
                # Convert angular distance back to km
                distance_km = distances[idx] * 6371.0

                commune_copy = commune.copy()
                commune_copy['zone_id'] = indices[idx]
                commune_copy['distance_to_center'] = distance_km
                commune_copy['center_commune'] = center_names[indices[idx]]
                commune_assignments.append(commune_copy)

        # Clear progress (optional)
        if has_progress:
            try:
                progress_bar.empty()
                progress_text.empty()
            except:
                pass

        if len(commune_assignments) == 0:
            st.warning("⚠️ Aucune commune n'a été assignée à une zone. Essayez d'augmenter le rayon maximum.")
            return pd.DataFrame()

        # Create DataFrame
        zones_df = pd.DataFrame(commune_assignments)

        # Aggregate data at zone level
        self.zones = self._aggregate_zones(zones_df)

        return self.zones

    def _create_zones_fallback(self, eligible: pd.DataFrame, city_centers: pd.DataFrame, max_radius_km: float) -> pd.DataFrame:
        """
        Fallback method using vectorized Haversine (used if KD-Tree fails)

        This is the original implementation, kept as backup.
        """
        center_lats = city_centers['latitude'].values
        center_lons = city_centers['longitude'].values
        center_names = city_centers['nom_commune'].values

        commune_assignments = []

        for _, commune in eligible.iterrows():
            comm_lat = commune['latitude']
            comm_lon = commune['longitude']

            # Calculate distance to ALL city centers at once (vectorized)
            dlat = np.radians(center_lats - comm_lat)
            dlon = np.radians(center_lons - comm_lon)

            a = (np.sin(dlat/2)**2 +
                 np.cos(np.radians(comm_lat)) * np.cos(np.radians(center_lats)) *
                 np.sin(dlon/2)**2)
            c = 2 * np.arcsin(np.sqrt(a))
            distances = 6371 * c  # Earth radius in km

            # Find nearest center within max_radius
            min_distance = distances.min()

            if min_distance <= max_radius_km:
                nearest_idx = distances.argmin()
                commune_copy = commune.copy()
                commune_copy['zone_id'] = nearest_idx
                commune_copy['distance_to_center'] = min_distance
                commune_copy['center_commune'] = center_names[nearest_idx]
                commune_assignments.append(commune_copy)

        if len(commune_assignments) == 0:
            return pd.DataFrame()

        zones_df = pd.DataFrame(commune_assignments)
        self.zones = self._aggregate_zones(zones_df)

        return self.zones
    
    def _aggregate_zones(self, zones_df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate commune data to zone level
        
        Each commune is now assigned to exactly ONE zone, so no deduplication needed.
        
        Args:
            zones_df: DataFrame with zone assignments
            
        Returns:
            DataFrame with zone-level aggregated data
        """
        # Helper function to create readable zone names
        def format_zone_name(commune_list):
            communes = sorted(commune_list.tolist())
            if len(communes) <= 3:
                return ', '.join(communes)
            else:
                return f"{', '.join(communes[:3])} + {len(communes)-3} autres"
        
        # Simple aggregation - no duplicates to worry about!
        agg_funcs = {
            'code_commune': 'count',  # Number of communes
            'nom_commune': format_zone_name,  # Readable list of commune names
            'population_totale': 'sum',
            'nb_menages': 'sum',
            'nb_maisons_individuelles': 'sum',
            'latitude': 'mean',  # Zone center
            'longitude': 'mean',
            'pct_maisons': 'mean',
            'pct_residences_principales': 'mean',
            'revenu_median': 'median',
            'niveau_vie_median': 'median',
            'taux_pauvrete': 'mean',
            'code_departement': 'first',
            'center_commune': 'first',
        }
        
        zones = zones_df.groupby('zone_id').agg(agg_funcs).reset_index()
        
        # Rename column
        zones.rename(columns={'code_commune': 'nb_communes'}, inplace=True)
        
        # Add region information
        zones['region'] = zones['code_departement'].apply(utils.get_region_from_department)
        
        # APPLY STRICT CRITERIA AT ZONE LEVEL
        # Filter zones that meet the target criteria after aggregation
        zones = zones[
            (zones['pct_maisons'] >= 50) &  # Zones must have 50%+ houses on average
            (zones['pct_residences_principales'] >= 70) &  # 70%+ primary residences
            (zones['nb_communes'] >= 2)  # At least 2 communes per zone
        ].copy()
        
        return zones
    
    def calculate_scores(self, scoring_weights: dict = None) -> pd.DataFrame:
        """
        Calculate scores for all zones based on franchise criteria

        Args:
            scoring_weights: Dictionary with 'housing', 'income', 'market' weights (0-1, must sum to 1)
                           If None, uses default weights (housing: 0.4, income: 0.3, market: 0.3)

        Returns:
            DataFrame with scored zones
        """
        if self.zones is None or (isinstance(self.zones, pd.DataFrame) and len(self.zones) == 0):
            self.create_zones()

        # Check again after creation attempt
        if self.zones is None or len(self.zones) == 0:
            st.warning("⚠️ Aucune zone n'a pu être créée avec les critères actuels")
            return pd.DataFrame()

        zones = self.zones.copy()

        # DON'T filter by minimum households - keep ALL zones to show all possibilities
        # zones = zones[zones['nb_menages'] >= config.MIN_HOUSEHOLDS].copy()

        if len(zones) == 0:
            return pd.DataFrame()

        # Use default weights if not provided
        if scoring_weights is None:
            scoring_weights = {'housing': 0.4, 'income': 0.3, 'market': 0.3}

        # Calculate individual component scores (0-100)
        zones['score_housing'] = self._score_housing(zones)
        zones['score_income'] = self._score_income(zones)
        zones['score_market_size'] = self._score_market_size(zones)

        # Calculate weighted total score with custom weights
        zones['score_total'] = (
            zones['score_housing'] * scoring_weights['housing'] +
            zones['score_income'] * scoring_weights['income'] +
            zones['score_market_size'] * scoring_weights['market']
        )

        # Calculate potential clients (estimated)
        zones['potential_clients'] = zones['nb_menages'] * config.TARGET_CONVERSION_RATE

        # Sort by total score
        zones = zones.sort_values('score_total', ascending=False).reset_index(drop=True)

        # Add rank
        zones['rank'] = range(1, len(zones) + 1)

        self.scored_zones = zones

        return zones
    
    def _score_housing(self, zones: pd.DataFrame) -> pd.Series:
        """
        Score zones based on housing suitability
        
        Args:
            zones: DataFrame with zone data
            
        Returns:
            Series with housing scores (0-100)
        """
        # Normalize percentage of individual houses
        houses_score = utils.normalize_score(
            zones['pct_maisons'].values,
            zones['pct_maisons'].min(),
            zones['pct_maisons'].max()
        )
        
        # Normalize percentage of primary residences
        primary_score = utils.normalize_score(
            zones['pct_residences_principales'].values,
            zones['pct_residences_principales'].min(),
            zones['pct_residences_principales'].max()
        )
        
        # Combined housing score (weighted average)
        housing_score = (houses_score * 0.6 + primary_score * 0.4)
        
        return pd.Series(housing_score, index=zones.index)
    
    def _score_demographics(self, zones: pd.DataFrame) -> pd.Series:
        """
        Score zones based on demographic profile
        
        Args:
            zones: DataFrame with zone data
            
        Returns:
            Series with demographic scores (0-100)
        """
        # Score for children (families)
        children_score = utils.normalize_score(
            zones['pct_0_17_ans'].values,
            zones['pct_0_17_ans'].min(),
            zones['pct_0_17_ans'].max()
        )
        
        # Score for retraités
        retraites_score = utils.normalize_score(
            zones['pct_60_plus'].values,
            zones['pct_60_plus'].min(),
            zones['pct_60_plus'].max()
        )
        
        # Score for couples with children
        couples_score = utils.normalize_score(
            zones['pct_couples_enfants'].values,
            zones['pct_couples_enfants'].min(),
            zones['pct_couples_enfants'].max()
        )
        
        # Combined demographic score
        demo_score = (children_score * 0.3 + retraites_score * 0.4 + couples_score * 0.3)
        
        return pd.Series(demo_score, index=zones.index)
    
    def _score_income(self, zones: pd.DataFrame) -> pd.Series:
        """
        Score zones based on income level
        
        Args:
            zones: DataFrame with zone data
            
        Returns:
            Series with income scores (0-100)
        """
        # Compare to national median
        income_score = utils.normalize_score(
            zones['revenu_median'].values,
            self.national_median_income * 0.8,  # Lower bound
            self.national_median_income * 1.5   # Upper bound
        )
        
        # Penalize high poverty rates
        poverty_penalty = utils.normalize_score(
            -zones['taux_pauvrete'].values,  # Negative because lower is better
            -zones['taux_pauvrete'].max(),
            -zones['taux_pauvrete'].min()
        )
        
        # Combined income score
        income_final = (income_score * 0.7 + poverty_penalty * 0.3)
        
        return pd.Series(income_final, index=zones.index)
    
    def _score_market_size(self, zones: pd.DataFrame) -> pd.Series:
        """
        Score zones based on market size (number of households)
        
        Args:
            zones: DataFrame with zone data
            
        Returns:
            Series with market size scores (0-100)
        """
        # Normalize household count
        # More households = better, but with diminishing returns
        market_score = utils.normalize_score(
            np.log1p(zones['nb_menages'].values),  # Log scale for diminishing returns
            np.log1p(config.MIN_HOUSEHOLDS),
            np.log1p(zones['nb_menages'].max())
        )
        
        return pd.Series(market_score, index=zones.index)
    
    def get_top_zones(self, n: int = 20) -> pd.DataFrame:
        """
        Get top N zones by score
        
        Args:
            n: Number of top zones to return
            
        Returns:
            DataFrame with top zones
        """
        if self.scored_zones is None:
            self.calculate_scores()
        
        return self.scored_zones.head(n)
    
    def get_zone_details(self, zone_id: int) -> Dict:
        """
        Get detailed information for a specific zone
        
        Args:
            zone_id: Zone identifier
            
        Returns:
            Dictionary with zone details
        """
        if self.scored_zones is None:
            self.calculate_scores()
        
        zone = self.scored_zones[self.scored_zones['zone_id'] == zone_id]
        
        if len(zone) == 0:
            return {}
        
        zone_data = zone.iloc[0].to_dict()
        
        return zone_data
