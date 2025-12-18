"""
Data collection module for INSEE datasets
Handles downloading and caching of demographic, housing, and income data
"""

import os
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
import zipfile
import io
import config
import streamlit as st
from simple_insee_parser import SimpleINSEEParser


class DataCollector:
    """Handles collection and caching of INSEE data"""
    
    def __init__(self):
        self.cache_dir = config.CACHE_DIR
        self.raw_dir = config.RAW_DATA_DIR
        
    def _get_cache_path(self, dataset_name: str) -> str:
        """Get cache file path for a dataset"""
        return os.path.join(self.cache_dir, f"{dataset_name}_cache.pkl")
    
    def _is_cache_valid(self, cache_path: str) -> bool:
        """Check if cache file exists and is not expired"""
        if not os.path.exists(cache_path):
            return False
        
        # Check if cache is older than CACHE_EXPIRY_DAYS
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        expiry_time = datetime.now() - timedelta(days=config.CACHE_EXPIRY_DAYS)
        
        return file_time > expiry_time
    
    def _load_from_cache(self, dataset_name: str) -> Optional[pd.DataFrame]:
        """Load data from cache if available"""
        cache_path = self._get_cache_path(dataset_name)
        
        if self._is_cache_valid(cache_path):
            try:
                return pd.read_pickle(cache_path)
            except Exception as e:
                print(f"Error loading cache for {dataset_name}: {e}")
                return None
        
        return None
    
    def _save_to_cache(self, dataset_name: str, df: pd.DataFrame):
        """Save data to cache"""
        cache_path = self._get_cache_path(dataset_name)
        try:
            df.to_pickle(cache_path)
        except Exception as e:
            print(f"Error saving cache for {dataset_name}: {e}")
    
    def get_communes_geo_data(self) -> pd.DataFrame:
        """
        Get geographic data for all French communes
        Returns DataFrame with commune code, name, latitude, longitude
        """
        cache_name = 'communes_geo'

        # Check cache first
        cached_data = self._load_from_cache(cache_name)
        if cached_data is not None:
            return cached_data

        try:
            # Download GeoJSON data
            st.info("🌍 Téléchargement des données géographiques...")
            response = requests.get(config.FRANCE_GEOJSON_URL, timeout=30)
            response.raise_for_status()
            geo_data = response.json()
            
            # Extract commune information
            communes = []
            for feature in geo_data['features']:
                props = feature['properties']
                geom = feature['geometry']
                
                # Calculate centroid for point representation
                if geom['type'] == 'Polygon':
                    coords = geom['coordinates'][0]
                elif geom['type'] == 'MultiPolygon':
                    coords = geom['coordinates'][0][0]
                else:
                    continue
                
                # Simple centroid calculation
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                centroid_lon = sum(lons) / len(lons)
                centroid_lat = sum(lats) / len(lats)
                
                communes.append({
                    'code_commune': props.get('code'),
                    'nom_commune': props.get('nom'),
                    'code_departement': props.get('code')[:2] if props.get('code') else None,
                    'latitude': centroid_lat,
                    'longitude': centroid_lon,
                    'geometry': geom  # Keep full geometry for mapping
                })
            
            df = pd.DataFrame(communes)
            
            # Save to cache
            self._save_to_cache(cache_name, df)
            st.success(f"✅ Données géographiques chargées: {len(df):,} communes")

            return df

        except requests.Timeout:
            st.error("❌ Délai d'attente dépassé lors du téléchargement des données géographiques")
            st.info("💡 **Solutions:** Vérifiez votre connexion internet ou réessayez dans quelques instants")
            return pd.DataFrame(columns=['code_commune', 'nom_commune', 'latitude', 'longitude', 'code_departement'])
        except requests.ConnectionError:
            st.error("❌ Impossible de se connecter au serveur de données géographiques")
            st.info("💡 **Solutions:** Vérifiez votre connexion internet ou contactez le support")
            return pd.DataFrame(columns=['code_commune', 'nom_commune', 'latitude', 'longitude', 'code_departement'])
        except requests.HTTPError as e:
            st.error(f"❌ Erreur HTTP lors du téléchargement: {e.response.status_code}")
            st.info("💡 **Solutions:** Le serveur de données est peut-être temporairement indisponible. Réessayez plus tard.")
            return pd.DataFrame(columns=['code_commune', 'nom_commune', 'latitude', 'longitude', 'code_departement'])
        except Exception as e:
            st.error(f"❌ Erreur inattendue lors du chargement des données géographiques: {str(e)}")
            st.info("💡 **Contact:** Si le problème persiste, contactez le support technique")
            return pd.DataFrame(columns=['code_commune', 'nom_commune', 'latitude', 'longitude', 'code_departement'])
    
    def get_population_data(self) -> pd.DataFrame:
        """
        Get population and demographic data from INSEE
        Returns DataFrame with commune-level population statistics
        """
        cache_name = 'population'
        
        # Check cache first
        cached_data = self._load_from_cache(cache_name)
        if cached_data is not None:
            return cached_data
        
        st.info("📊 Chargement des données RÉELLES INSEE...")
        
        parser = SimpleINSEEParser(self.raw_dir)
        df = parser.parse_population()
        
        if df is None or len(df) == 0:
            st.error("❌ Erreur chargement population")
            # Return empty DataFrame with required columns (no demographics)
            return pd.DataFrame(columns=['code_commune', 'nom_commune', 'population_totale', 'nb_menages'])
        
        st.success(f"✅ Données INSEE chargées: {len(df):,} communes")
        
        # Save to cache
        self._save_to_cache(cache_name, df)
        
        return df
    
    def get_housing_data(self) -> pd.DataFrame:
        """
        Get housing data from INSEE
        Returns DataFrame with commune-level housing statistics
        """
        cache_name = 'housing'
        
        # Check cache first
        cached_data = self._load_from_cache(cache_name)
        if cached_data is not None:
            return cached_data
        
        st.info("🏠 Chargement logements...")
        
        parser = SimpleINSEEParser(self.raw_dir)
        df = parser.parse_housing()
        
        if df is None or len(df) == 0:
            st.error("❌ Erreur chargement logements")
            # Return empty DataFrame with required columns
            return pd.DataFrame(columns=['code_commune', 'nom_commune', 'nb_logements',
                                        'nb_maisons_individuelles', 'pct_maisons', 
                                        'pct_residences_principales'])
        
        st.success(f"✅ Données logements chargées: {len(df):,} communes")
        
        # Save to cache
        self._save_to_cache(cache_name, df)
        
        return df
    
    def get_income_data(self) -> pd.DataFrame:
        """
        Get income and tax data from INSEE
        Returns DataFrame with commune-level income statistics
        """
        cache_name = 'income'
        
        # Check cache first
        cached_data = self._load_from_cache(cache_name)
        if cached_data is not None:
            return cached_data
        
        st.info("💰 Chargement revenus...")
        
        parser = SimpleINSEEParser(self.raw_dir)
        df = parser.parse_income()
        
        if df is None or len(df) == 0:
            st.error("❌ Erreur chargement revenus")
            # Return empty DataFrame with required columns
            return pd.DataFrame(columns=['code_commune', 'revenu_median', 
                                        'niveau_vie_median', 'taux_pauvrete'])
        
        st.success(f"✅ Données revenus chargées: {len(df):,} communes")
        
        # Save to cache
        self._save_to_cache(cache_name, df)
        
        return df
    
    def get_all_data(self) -> pd.DataFrame:
        """
        Get all data merged into a single DataFrame
        Returns comprehensive commune-level dataset
        """
        cache_name = 'all_data_merged'
        
        # Check cache first
        cached_data = self._load_from_cache(cache_name)
        if cached_data is not None:
            return cached_data
        
        # Get all individual datasets
        geo_df = self.get_communes_geo_data()
        pop_df = self.get_population_data()

        housing_df = self.get_housing_data()
        income_df = self.get_income_data()
        
        # Merge all datasets on commune code
        merged_df = geo_df.copy()
        merged_df = merged_df.merge(pop_df, on='code_commune', how='left', suffixes=('', '_pop'))
        merged_df = merged_df.merge(housing_df, on='code_commune', how='left', suffixes=('', '_housing'))
        merged_df = merged_df.merge(income_df, on='code_commune', how='left', suffixes=('', '_income'))
        
        # Clean up duplicate columns
        merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
        
        # Save to cache
        self._save_to_cache(cache_name, merged_df)
        
        return merged_df


# Singleton instance
_collector = None

def get_data_collector() -> DataCollector:
    """Get singleton instance of DataCollector"""
    global _collector
    if _collector is None:
        _collector = DataCollector()
    return _collector
