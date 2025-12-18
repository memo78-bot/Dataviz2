"""
Utility functions for the franchise zone analysis
"""

import numpy as np
import pandas as pd
from typing import Tuple, List
import math


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth (in kilometers)
    
    Args:
        lat1, lon1: Latitude and longitude of first point
        lat2, lon2: Latitude and longitude of second point
        
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def normalize_score(value, min_val: float, max_val: float):
    """
    Normalize a value or array of values to 0-100 range
    
    Args:
        value: Value or array to normalize
        min_val: Minimum value in the range
        max_val: Maximum value in the range
        
    Returns:
        Normalized score(s) (0-100), same type as input
    """
    if max_val == min_val:
        if isinstance(value, np.ndarray):
            return np.full_like(value, 50.0, dtype=float)
        return 50.0
    
    normalized = ((value - min_val) / (max_val - min_val)) * 100
    
    # Use numpy clip for arrays, regular max/min for scalars
    if isinstance(normalized, np.ndarray):
        return np.clip(normalized, 0, 100)
    else:
        return max(0.0, min(100.0, float(normalized)))


def clean_commune_name(name: str) -> str:
    """
    Clean and standardize commune names
    
    Args:
        name: Raw commune name
        
    Returns:
        Cleaned commune name
    """
    if pd.isna(name):
        return ""
    
    # Remove leading/trailing whitespace
    name = str(name).strip()
    
    # Standardize case (Title Case)
    name = name.title()
    
    return name


def calculate_percentile(value: float, series: pd.Series) -> float:
    """
    Calculate the percentile rank of a value in a series
    
    Args:
        value: Value to rank
        series: Series of values
        
    Returns:
        Percentile (0-100)
    """
    if pd.isna(value) or len(series) == 0:
        return 0
    
    rank = (series < value).sum()
    percentile = (rank / len(series)) * 100
    
    return percentile


def format_number(num: float, decimal_places: int = 0) -> str:
    """
    Format a number with thousand separators
    
    Args:
        num: Number to format
        decimal_places: Number of decimal places
        
    Returns:
        Formatted string
    """
    if pd.isna(num):
        return "N/A"
    
    if decimal_places == 0:
        return f"{int(num):,}".replace(',', ' ')
    else:
        return f"{num:,.{decimal_places}f}".replace(',', ' ')


def group_by_proximity(df: pd.DataFrame, max_distance_km: float, 
                       lat_col: str = 'latitude', lon_col: str = 'longitude') -> pd.DataFrame:
    """
    Group rows by geographic proximity using simple clustering
    
    Args:
        df: DataFrame with latitude and longitude columns
        max_distance_km: Maximum distance for grouping
        lat_col: Name of latitude column
        lon_col: Name of longitude column
        
    Returns:
        DataFrame with added 'cluster_id' column
    """
    from sklearn.cluster import DBSCAN
    
    if len(df) == 0:
        df['cluster_id'] = []
        return df
    
    # Extract coordinates
    coords = df[[lat_col, lon_col]].values
    
    # Convert max distance to radians (approximate)
    epsilon = max_distance_km / 6371.0  # Earth's radius in km
    
    # Perform clustering
    clustering = DBSCAN(eps=epsilon, min_samples=1, metric='haversine')
    df['cluster_id'] = clustering.fit_predict(np.radians(coords))
    
    return df


def get_region_from_department(dept_code: str) -> str:
    """
    Get region name from department code
    
    Args:
        dept_code: Department code (2 or 3 digits)
        
    Returns:
        Region name
    """
    # Simplified mapping (main regions)
    dept_to_region = {
        '01': 'Auvergne-Rhône-Alpes', '03': 'Auvergne-Rhône-Alpes', '07': 'Auvergne-Rhône-Alpes',
        '15': 'Auvergne-Rhône-Alpes', '26': 'Auvergne-Rhône-Alpes', '38': 'Auvergne-Rhône-Alpes',
        '42': 'Auvergne-Rhône-Alpes', '43': 'Auvergne-Rhône-Alpes', '63': 'Auvergne-Rhône-Alpes',
        '69': 'Auvergne-Rhône-Alpes', '73': 'Auvergne-Rhône-Alpes', '74': 'Auvergne-Rhône-Alpes',
        '21': 'Bourgogne-Franche-Comté', '25': 'Bourgogne-Franche-Comté', '39': 'Bourgogne-Franche-Comté',
        '58': 'Bourgogne-Franche-Comté', '70': 'Bourgogne-Franche-Comté', '71': 'Bourgogne-Franche-Comté',
        '89': 'Bourgogne-Franche-Comté', '90': 'Bourgogne-Franche-Comté',
        '22': 'Bretagne', '29': 'Bretagne', '35': 'Bretagne', '56': 'Bretagne',
        '18': 'Centre-Val de Loire', '28': 'Centre-Val de Loire', '36': 'Centre-Val de Loire',
        '37': 'Centre-Val de Loire', '41': 'Centre-Val de Loire', '45': 'Centre-Val de Loire',
        '08': 'Grand Est', '10': 'Grand Est', '51': 'Grand Est', '52': 'Grand Est',
        '54': 'Grand Est', '55': 'Grand Est', '57': 'Grand Est', '67': 'Grand Est',
        '68': 'Grand Est', '88': 'Grand Est',
        '59': 'Hauts-de-France', '62': 'Hauts-de-France', '60': 'Hauts-de-France',
        '02': 'Hauts-de-France', '80': 'Hauts-de-France',
        '75': 'Île-de-France', '77': 'Île-de-France', '78': 'Île-de-France',
        '91': 'Île-de-France', '92': 'Île-de-France', '93': 'Île-de-France',
        '94': 'Île-de-France', '95': 'Île-de-France',
        '14': 'Normandie', '27': 'Normandie', '50': 'Normandie', '61': 'Normandie', '76': 'Normandie',
        '16': 'Nouvelle-Aquitaine', '17': 'Nouvelle-Aquitaine', '19': 'Nouvelle-Aquitaine',
        '23': 'Nouvelle-Aquitaine', '24': 'Nouvelle-Aquitaine', '33': 'Nouvelle-Aquitaine',
        '40': 'Nouvelle-Aquitaine', '47': 'Nouvelle-Aquitaine', '64': 'Nouvelle-Aquitaine',
        '79': 'Nouvelle-Aquitaine', '86': 'Nouvelle-Aquitaine', '87': 'Nouvelle-Aquitaine',
        '09': 'Occitanie', '11': 'Occitanie', '12': 'Occitanie', '30': 'Occitanie',
        '31': 'Occitanie', '32': 'Occitanie', '34': 'Occitanie', '46': 'Occitanie',
        '48': 'Occitanie', '65': 'Occitanie', '66': 'Occitanie', '81': 'Occitanie', '82': 'Occitanie',
        '44': 'Pays de la Loire', '49': 'Pays de la Loire', '53': 'Pays de la Loire',
        '72': 'Pays de la Loire', '85': 'Pays de la Loire',
        '04': "Provence-Alpes-Côte d'Azur", '05': "Provence-Alpes-Côte d'Azur",
        '06': "Provence-Alpes-Côte d'Azur", '13': "Provence-Alpes-Côte d'Azur",
        '83': "Provence-Alpes-Côte d'Azur", '84': "Provence-Alpes-Côte d'Azur",
    }
    
    dept_code = dept_code.zfill(2)  # Ensure 2 digits
    return dept_to_region.get(dept_code, 'Autre')
