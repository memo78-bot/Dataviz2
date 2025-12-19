"""
Outil de nettoyage du projet.

Ce script supprime UNIQUEMENT :
- les dossiers __pycache__ (fichiers Python compilés)
- les fichiers de cache générés dans data/cache
- les éventuels caches Streamlit (.streamlit/cache)

Rien dans vos données brutes INSEE n'est touché.

Utilisation :
    python clean_project.py              # mode interactif (demande confirmation)
    python clean_project.py --dry-run    # affiche ce qui serait supprimé
    python clean_project.py --yes        # supprime sans demander (non interactif)
"""

import argparse
import os
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def find_paths_to_clean() -> dict:
    """Recense les fichiers / dossiers de cache à supprimer."""
    paths = {
        "pycache_dirs": [],
        "data_cache_files": [],
        "streamlit_cache_dirs": [],
    }

    # 1. Tous les __pycache__ du projet
    for root, dirs, _ in os.walk(PROJECT_ROOT):
        for d in dirs:
            if d == "__pycache__":
                paths["pycache_dirs"].append(Path(root) / d)

    # 2. Fichiers de cache de data_collector (data/cache/*.pkl)
    data_cache_dir = PROJECT_ROOT / "data" / "cache"
    if data_cache_dir.exists():
        for p in data_cache_dir.glob("*.pkl"):
            paths["data_cache_files"].append(p)

    # 3. Caches internes de Streamlit (s'ils existent)
    # Streamlit peut utiliser .streamlit/cache ou .streamlit/cache_data
    streamlit_dir = PROJECT_ROOT / ".streamlit"
    if streamlit_dir.exists():
        for candidate in ["cache", "cache_data", "cache_directory"]:
            cache_dir = streamlit_dir / candidate
            if cache_dir.exists():
                paths["streamlit_cache_dirs"].append(cache_dir)

    return paths


def print_summary(paths: dict) -> None:
    """Affiche un résumé lisible des éléments à nettoyer."""
    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(p)

    print("\n=== Éléments détectés pour nettoyage ===")

    print(f"- Dossiers __pycache__ : {len(paths['pycache_dirs'])}")
    for p in paths["pycache_dirs"]:
        print(f"  • {_rel(p)}")

    print(f"\n- Fichiers de cache de données (data/cache/*.pkl) : {len(paths['data_cache_files'])}")
    for p in paths["data_cache_files"]:
        print(f"  • {_rel(p)}")

    print(f"\n- Caches Streamlit : {len(paths['streamlit_cache_dirs'])}")
    for p in paths["streamlit_cache_dirs"]:
        print(f"  • {_rel(p)}")

    print("\nAucun autre fichier n'est impacté.")


def perform_cleanup(paths: dict, dry_run: bool = False) -> None:
    """Supprime effectivement les fichiers/dossiers listés."""
    if dry_run:
        print("\n[DRY-RUN] Aucun fichier n'a été supprimé (mode simulation).")
        return

    # Supprimer __pycache__
    for d in paths["pycache_dirs"]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    # Supprimer fichiers de cache pkl
    for f in paths["data_cache_files"]:
        if f.exists():
            try:
                f.unlink()
            except OSError:
                pass

    # Supprimer caches Streamlit
    for d in paths["streamlit_cache_dirs"]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    print("\n✅ Nettoyage terminé.")


def main():
    parser = argparse.ArgumentParser(description="Nettoyage sécurisé des fichiers de cache du projet.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ne supprime rien, affiche seulement ce qui serait supprimé.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Ne demande pas de confirmation avant suppression.",
    )
    args = parser.parse_args()

    print(f"Racine du projet : {PROJECT_ROOT}")
    paths = find_paths_to_clean()
    print_summary(paths)

    total_items = (
        len(paths["pycache_dirs"])
        + len(paths["data_cache_files"])
        + len(paths["streamlit_cache_dirs"])
    )

    if total_items == 0:
        print("\nRien à nettoyer, le projet est déjà propre.")
        return

    if args.dry_run:
        perform_cleanup(paths, dry_run=True)
        return

    if not args.yes:
        answer = input("\nConfirmer la suppression de ces éléments ? [o/N] ").strip().lower()
        if answer not in ("o", "oui", "y", "yes"):
            print("Opération annulée, aucun fichier supprimé.")
            return

    perform_cleanup(paths, dry_run=False)


if __name__ == "__main__":
    main()

