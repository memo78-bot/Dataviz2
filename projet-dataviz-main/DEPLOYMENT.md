# Guide de Déploiement - Streamlit Cloud

## 📋 Prérequis
- Compte GitHub
- Compte Streamlit Cloud (gratuit sur https://streamlit.io/cloud)

## 🚀 Étapes de Déploiement

### 1. Préparer le Repository GitHub

```bash
# Initialiser git (si ce n'est pas déjà fait)
git init

# Ajouter tous les fichiers
git add .

# Créer le premier commit
git commit -m "Initial commit - Poubelles-Propres App"

# Créer un repository sur GitHub et le lier
git remote add origin https://github.com/VOTRE_USERNAME/VOTRE_REPO.git
git branch -M main
git push -u origin main
```

### 2. Déployer sur Streamlit Cloud

1. Allez sur https://share.streamlit.io/
2. Cliquez sur "New app"
3. Sélectionnez votre repository GitHub
4. Branch: `main`
5. Main file path: `app.py`
6. Cliquez sur "Deploy!"

### 3. Configuration Avancée (si nécessaire)

Si vous avez des variables d'environnement :
1. Dans Streamlit Cloud, allez dans "Advanced settings"
2. Ajoutez vos secrets dans la section "Secrets"
3. Format TOML :
```toml
[database]
user = "your_user"
password = "your_password"
```

## 📁 Structure des Fichiers Importants

```
projet-dataviz-main/
├── .streamlit/
│   └── config.toml          # Configuration du thème
├── assets/
│   └── style.css            # Styles CSS personnalisés
├── data/                    # Données (assurez-vous qu'elles sont sur GitHub)
├── app.py                   # Application principale
├── requirements.txt         # Dépendances Python
└── .gitignore              # Fichiers à ignorer
```

## ✅ Checklist Avant Déploiement

- [ ] Tous les fichiers sont commités sur GitHub
- [ ] Le dossier `data/` contient bien toutes les données nécessaires
- [ ] Le fichier `requirements.txt` est à jour
- [ ] Le dossier `.streamlit/` et `assets/` sont bien inclus
- [ ] L'application fonctionne en local : `streamlit run app.py`

## 🔧 Résolution de Problèmes

### Les styles CSS ne s'affichent pas
✅ **Corrigé** : Le CSS est maintenant dans un fichier externe `assets/style.css`

### Erreur de dépendances
- Vérifiez que toutes les dépendances dans `requirements.txt` sont installables
- Streamlit Cloud utilise Python 3.9+ par défaut

### Données manquantes
- Assurez-vous que le dossier `data/` est bien commité dans Git
- Vérifiez les chemins relatifs dans le code

### Police personnalisée ne charge pas
- La police Inter est chargée via Google Fonts dans le CSS
- Fallback sur les polices système si Google Fonts est bloqué

## 🎨 Personnalisation du Thème

Le thème est configuré dans [.streamlit/config.toml](.streamlit/config.toml):
- `primaryColor`: Couleur principale (#10B981 - vert émeraude)
- `backgroundColor`: Fond de page (#F8FAFC)
- `secondaryBackgroundColor`: Fond de la sidebar (#FFFFFF)
- `textColor`: Couleur du texte (#0F172A)

## 📞 Support

En cas de problème :
1. Vérifiez les logs dans Streamlit Cloud (bouton "Manage app" > "Logs")
2. Testez en local : `streamlit run app.py`
3. Consultez la documentation : https://docs.streamlit.io/

## 🔗 Liens Utiles

- [Documentation Streamlit](https://docs.streamlit.io/)
- [Streamlit Cloud](https://streamlit.io/cloud)
- [Community Forum](https://discuss.streamlit.io/)
