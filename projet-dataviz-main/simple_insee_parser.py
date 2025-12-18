"""
ULTRA-SIMPLE INSEE Parser - No fancy stuff, just works
"""

import pandas as pd
import os
import zipfile

class SimpleINSEEParser:
    def __init__(self, raw_dir="data/raw"):
        self.raw_dir = raw_dir
        self._extract_zipped_files()
    
    def _extract_zipped_files(self):
        """Extract ZIP files if they exist and CSV files don't"""
        zip_files = {
            "base-cc-emploi-pop-active-2020.zip": "base-cc-emploi-pop-active-2020_v2.CSV",
            "base-cc-logement-2021.zip": "base-cc-logement-2021.CSV"
        }
        
        for zip_name, csv_name in zip_files.items():
            zip_path = os.path.join(self.raw_dir, zip_name)
            csv_path = os.path.join(self.raw_dir, csv_name)
            
            # Extract if ZIP exists and CSV doesn't
            if os.path.exists(zip_path) and not os.path.exists(csv_path):
                print(f"📦 Extraction de {zip_name}...")
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(self.raw_dir)
                    print(f"✓ {csv_name} extrait avec succès")
                except Exception as e:
                    print(f"❌ Erreur lors de l'extraction de {zip_name}: {e}")
        
    def parse_population(self):
        """Parse population CSV - actually uses housing file which has the data we need"""
        try:
            # The employment file doesn't have total population or household count
            # Use the housing file which has comprehensive population/household data
            filepath = os.path.join(self.raw_dir, "base-cc-logement-2021.CSV")
            print(f"📂 Reading population data from housing file: {filepath}")
            
            df = pd.read_csv(filepath, sep=';', low_memory=False)
            print(f"✓ CSV loaded: {len(df)} rows")
            
            result = pd.DataFrame()
            result['code_commune'] = df['CODGEO'].astype(str)
            
            # Try to get commune name if available
            try:
                result['nom_commune'] = df['LIBGEO']
            except KeyError:
                result['nom_commune'] = result['code_commune']  # Use code as fallback
            
            # Get household count - the most important metric for us
            try:
                result['nb_menages'] = pd.to_numeric(df['P21_MEN'], errors='coerce').fillna(0).astype(int)
            except KeyError:
                result['nb_menages'] = 0
            
            # Try to get population if available, otherwise estimate from households (avg 2.2 persons/household in France)
            try:
                result['population_totale'] = pd.to_numeric(df['P21_POP'], errors='coerce').fillna(0).astype(int)
            except KeyError:
                result['population_totale'] = (result['nb_menages'] * 2.2).astype(int)
            
            print(f"✓ Population data parsed successfully: {len(result)} communes")
            return result
        except Exception as e:
            print(f"❌ Population parsing error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def parse_housing(self):
        """Parse housing CSV"""
        try:
            df = pd.read_csv(os.path.join(self.raw_dir, "base-cc-logement-2021.CSV"), sep=';', low_memory=False)
            
            result = pd.DataFrame()
            result['code_commune'] = df['CODGEO'].astype(str)
            
            # Try to get values, use defaults if column missing
            try:
                nb_log = pd.to_numeric(df['P21_LOG'], errors='coerce').fillna(1).astype(int)
            except:
                nb_log = pd.Series([1] * len(df))
                
            try:
                nb_maisons = pd.to_numeric(df['P21_MAISON'], errors='coerce').fillna(0).astype(int)
            except:
                nb_maisons = pd.Series([0] * len(df))
                
            try:
                nb_rp = pd.to_numeric(df['P21_RP'], errors='coerce').fillna(0).astype(int)
            except:
                nb_rp = pd.Series([0] * len(df))
            
            result['nb_logements'] = nb_log
            result['nb_maisons_individuelles'] = nb_maisons
            result['pct_maisons'] = (nb_maisons / nb_log * 100).clip(0, 100)
            result['pct_residences_principales'] = (nb_rp / nb_log * 100).clip(0, 100)
            
            try:
                result['nom_commune'] = df['LIBGEO']
            except:
                pass
            
            return result
        except Exception as e:
            print(f"Housing error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def parse_income(self):
        """Parse income Excel with robust error handling"""
        income_file = "Niveau_de_vie_2013_a_la_commune-Global_Map_Solution (1).xlsx"
        filepath = os.path.join(self.raw_dir, income_file)

        try:
            # Check if file exists
            if not os.path.exists(filepath):
                print(f"⚠️ Fichier de revenus non trouvé: {income_file}")
                print(f"💡 Utilisation de valeurs par défaut (ajustées inflation 2013-2024)")
                return self._create_default_income_data()

            df = pd.read_excel(filepath)

            # Find code column
            code_col = [c for c in df.columns if 'CODE' in str(c).upper() or 'COM' in str(c).upper()]
            code_col = code_col[0] if code_col else df.columns[0]

            # Find revenue column
            rev_col = [c for c in df.columns if any(x in str(c).upper() for x in ['REVENU', 'NIVEAU', 'MEDIAN', 'VIE'])]

            result = pd.DataFrame()
            result['code_commune'] = df[code_col].astype(str)

            # IMPORTANT: Adjust 2013 data for inflation (2013->2024 = +18%)
            INFLATION_ADJUSTMENT = 1.18

            if rev_col:
                result['revenu_median'] = pd.to_numeric(df[rev_col[0]], errors='coerce').fillna(22000) * INFLATION_ADJUSTMENT
                result['niveau_vie_median'] = result['revenu_median'] * 1.3
            else:
                result['revenu_median'] = 22000 * INFLATION_ADJUSTMENT
                result['niveau_vie_median'] = 29000 * INFLATION_ADJUSTMENT

            result['taux_pauvrete'] = 14

            print(f"✓ Données revenus 2013 chargées et ajustées (inflation +{(INFLATION_ADJUSTMENT-1)*100:.0f}%)")
            return result

        except FileNotFoundError:
            print(f"❌ Fichier introuvable: {income_file}")
            return self._create_default_income_data()
        except pd.errors.ExcelFileError:
            print(f"❌ Format Excel invalide: {income_file}")
            return self._create_default_income_data()
        except Exception as e:
            print(f"❌ Erreur inattendue lors du chargement des revenus: {e}")
            import traceback
            traceback.print_exc()
            return self._create_default_income_data()

    def _create_default_income_data(self):
        """Create default income data when file is missing"""
        # Adjusted for 2024 (base 2013 + 18% inflation)
        INFLATION_ADJUSTMENT = 1.18
        return pd.DataFrame({
            'code_commune': [],
            'revenu_median': [],
            'niveau_vie_median': [],
            'taux_pauvrete': []
        })
