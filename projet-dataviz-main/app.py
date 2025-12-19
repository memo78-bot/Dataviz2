"""
Streamlit Application - Poubelles-Propres Franchise Zone Analysis
Interactive dashboard for identifying optimal franchise zones in France
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
import config
import utils
from data_collector import get_data_collector
from zone_analyzer import ZoneAnalyzer
import map_viz


# Page configuration
st.set_page_config(
    page_title="Poubelles-Propres - Analyse de Zones",
    page_icon="🗑️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS from external file
def load_css():
    """Load CSS from external file for better maintainability and Streamlit Cloud compatibility"""
    css_file = "assets/style.css"
    try:
        with open(css_file) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file not found: {css_file}")

# Apply custom CSS
load_css()


def apply_premium_style(fig):
    """
    Apply premium styling to Plotly figures for seamless card integration

    Args:
        fig: Plotly figure object

    Returns:
        Styled figure
    """
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', color='#64748B', size=12),
        title_font=dict(size=18, color='#0F172A', family='Inter'),
        hoverlabel=dict(
            bgcolor='#0F172A',
            font_size=13,
            font_family='Inter'
        ),
        xaxis=dict(
            gridcolor='#E2E8F0',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            gridcolor='#E2E8F0',
            showgrid=True,
            zeroline=False
        )
    )
    return fig


@st.cache_data
def load_data():
    """Load and cache data"""
    collector = get_data_collector()
    data = collector.get_all_data()
    return data


@st.cache_data
def add_region_info(data):
    """Add region information to data - cached to avoid recalculation"""
    data = data.copy()
    if 'code_departement' in data.columns:
        data['region'] = data['code_departement'].apply(utils.get_region_from_department)
    return data


@st.cache_data
def analyze_all_zones(data, max_radius, scoring_weights_tuple):
    """Analyze ALL zones without filtering - results cached by radius and weights

    Args:
        data: DataFrame with all commune data (including regions)
        max_radius: Maximum radius for zone clustering
        scoring_weights_tuple: Tuple with scoring weights (housing, income, market)
    """
    # Convert tuple back to dict for the analyzer
    scoring_weights = {
        'housing': scoring_weights_tuple[0],
        'income': scoring_weights_tuple[1],
        'market': scoring_weights_tuple[2]
    }
    analyzer = ZoneAnalyzer(data)
    zones = analyzer.create_zones(max_radius_km=max_radius)
    scored_zones = analyzer.calculate_scores(scoring_weights=scoring_weights)
    return scored_zones


def filter_zones_by_geography(scored_zones, selected_regions, selected_departments):
    """Fast in-memory filtering of zones - no cache needed, very fast"""
    if not selected_regions and not selected_departments:
        return scored_zones

    filtered = scored_zones.copy()
    if selected_regions and selected_departments:
        filtered = filtered[
            (filtered['region'].isin(selected_regions)) &
            (filtered['code_departement'].isin(selected_departments))
        ]
    elif selected_regions:
        filtered = filtered[filtered['region'].isin(selected_regions)]
    elif selected_departments:
        filtered = filtered[filtered['code_departement'].isin(selected_departments)]

    return filtered.reset_index(drop=True)


def main():
    """Main application"""
    
    # Header
    st.markdown('<h1 class="main-header">🗑️ Poubelles-Propres</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Analyse des Zones de Franchise Potentielles en France</p>', unsafe_allow_html=True)
    
    # Sidebar - Configuration
    st.sidebar.header("⚙️ Configuration")
    
    # Load data - cached, only happens once
    with st.spinner("Chargement des données INSEE..."):
        raw_data = load_data()
        data = add_region_info(raw_data)

    # Sidebar - Geographic filters
    st.sidebar.subheader("🗺️ Filtre Géographique")
    
    # Check if we have the required columns for geographic filtering
    if 'code_departement' in data.columns and 'region' in data.columns:
        # Get unique regions from data
        available_regions = sorted(data['region'].dropna().unique().tolist())
    
        # Single region selectbox - empty by default
        selected_region = st.sidebar.selectbox(
            "Filtrer par région",
            options=["Toutes les régions"] + available_regions,
            index=0,
            help="Sélectionnez une région spécifique ou laissez sur 'Toutes les régions'"
        )
    
        # Convert to list format for compatibility with existing code
        if selected_region == "Toutes les régions":
            selected_regions = available_regions
        else:
            selected_regions = [selected_region]
    
        # Keep all departments (no department filter)
        selected_departments = sorted(data['code_departement'].dropna().unique().tolist())
    else:
        st.sidebar.warning("⚠️ Données géographiques non disponibles")
        selected_regions = []
        selected_departments = []
    
    # City selector (listing + recherche intégrée, dépend de la région sélectionnée)
    if 'nom_commune' in data.columns:
        # Restreindre les villes à la/aux région(s) sélectionnée(s)
        if 'region' in data.columns and selected_regions:
            filtered_for_cities = data[data['region'].isin(selected_regions)]
        else:
            filtered_for_cities = data

        city_options = sorted(filtered_for_cities['nom_commune'].dropna().unique().tolist())
        selected_city = st.sidebar.selectbox(
            "Sélectionner une ville (optionnel)",
            options=["Aucune sélection"] + city_options,
            index=0,
            help="Commencez à taper pour rechercher une commune dans la liste"
        )
    else:
        selected_city = "Aucune sélection"

    st.sidebar.markdown("---")

    # Sidebar filters
    st.sidebar.subheader("Paramètres de Zone")
    max_radius = st.sidebar.slider(
        "Rayon maximum de zone (km)",
        min_value=10,
        max_value=50,
        value=config.MAX_ZONE_RADIUS_KM,
        step=5,
        help="Distance maximale pour regrouper les communes"
    )
    
    min_households = st.sidebar.number_input(
        "Minimum de ménages par zone",
        min_value=500,
        max_value=50000,
        value=config.MIN_HOUSEHOLDS,
        step=500,
        help="Nombre minimum de ménages requis"
    )
    
    st.sidebar.subheader("Critères de Filtrage")
    min_houses_pct = st.sidebar.slider(
        "% minimum de maisons individuelles",
        min_value=0,
        max_value=100,
        value=config.TARGET_CRITERIA['min_pct_maisons'],
        step=5,
        help="Pourcentage minimum de maisons (vs appartements)"
    )

    min_income_percentile = st.sidebar.slider(
        "Niveau de revenu minimum",
        min_value=0,
        max_value=100,
        value=config.TARGET_CRITERIA['min_income_percentile'],
        step=10,
        help="Percentile de revenu minimum (50 = médiane nationale)"
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Pondération du Score")
    st.sidebar.markdown("Ajustez l'importance de chaque critère (total = **100%**)")

    # Define presets
    PRESETS = {
        "Classique (40/30/30)": (40, 30, 30),
        "Équilibré (33/33/33)": (33, 33, 34),  # 34 pour market pour atteindre 100
        "Focus Logement (60/20/20)": (60, 20, 20),
        "Focus Revenus (20/60/20)": (20, 60, 20),
        "Focus Taille (20/20/60)": (20, 20, 60),
        "Marché (20/30/50)": (20, 30, 50),
        "Personnalisé": None
    }

    # Preset selection
    preset = st.sidebar.selectbox(
        "Presets de pondération",
        options=list(PRESETS.keys()),
        help="Choisissez un preset ou personnalisez les pondérations"
    )

    # Initialize session state for weights if not exists
    if 'preset_weights' not in st.session_state:
        st.session_state.preset_weights = PRESETS["Classique (40/30/30)"]

    # Update weights when preset changes
    if preset != "Personnalisé":
        weights = PRESETS[preset]
        if st.session_state.preset_weights != weights:
            st.session_state.preset_weights = weights
            # Force update of the input values
            if 'weight_housing' in st.session_state:
                del st.session_state.weight_housing
            if 'weight_income' in st.session_state:
                del st.session_state.weight_income
            if 'weight_market' in st.session_state:
                del st.session_state.weight_market

    # Set default values based on preset or session state
    if preset == "Personnalisé":
        if 'weight_housing' in st.session_state:
            default_housing = st.session_state.weight_housing
            default_income = st.session_state.weight_income
            default_market = st.session_state.weight_market
        else:
            default_housing, default_income, default_market = 40, 30, 30
    else:
        default_housing, default_income, default_market = PRESETS[preset]

    weight_housing = st.sidebar.number_input(
        "🏠 Logement (%)",
        min_value=0,
        max_value=100,
        value=default_housing,
        step=1,
        disabled=(preset != "Personnalisé"),
        help="Importance du type de logement (maisons, résidences principales)"
    )

    weight_income = st.sidebar.number_input(
        "💰 Revenus (%)",
        min_value=0,
        max_value=100,
        value=default_income,
        step=1,
        disabled=(preset != "Personnalisé"),
        help="Importance du niveau de revenu et pauvreté"
    )

    weight_market = st.sidebar.number_input(
        "📊 Taille marché (%)",
        min_value=0,
        max_value=100,
        value=default_market,
        step=1,
        disabled=(preset != "Personnalisé"),
        help="Importance du nombre de ménages"
    )

    # Calculate total and show status
    total_weight = weight_housing + weight_income + weight_market

    # Display total with color coding and progress bar
    if total_weight == 100:
        st.sidebar.success(f"✅ Total: {total_weight}%")
        st.sidebar.progress(1.0)
    else:
        st.sidebar.error(f"❌ Total: {total_weight}%")
        st.sidebar.progress(min(total_weight / 100, 1.0))
        if total_weight < 100:
            st.sidebar.warning(f"⚠️ Il manque {100 - total_weight}% pour atteindre 100%")
        else:
            st.sidebar.warning(f"⚠️ Vous avez {total_weight - 100}% en trop")

    # Only proceed if total is 100%
    if total_weight != 100:
        st.error("⚠️ **Les pondérations doivent totaliser exactement 100% pour lancer l'analyse.**")

        # Create a visual representation
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🏠 Logement", f"{weight_housing}%")
        with col2:
            st.metric("💰 Revenus", f"{weight_income}%")
        with col3:
            st.metric("📊 Taille marché", f"{weight_market}%")

        # Show difference
        diff = 100 - total_weight
        if diff > 0:
            st.warning(f"📉 Il vous manque **{diff}%** à répartir entre les critères.")
        else:
            st.warning(f"📈 Vous avez **{abs(diff)}%** en trop à retirer des critères.")

        st.info("💡 **Astuce:** Utilisez les presets dans la sidebar pour des configurations prédéfinies, ou ajustez manuellement les valeurs.")
        st.stop()

    # Normalize weights to sum to 1.0 (should always be 1.0 now)
    scoring_weights = {
        'housing': weight_housing / 100,
        'income': weight_income / 100,
        'market': weight_market / 100
    }
    
    # Update config with user inputs
    config.MAX_ZONE_RADIUS_KM = max_radius
    config.MIN_HOUSEHOLDS = min_households
    config.TARGET_CRITERIA['min_pct_maisons'] = min_houses_pct
    config.TARGET_CRITERIA['min_income_percentile'] = min_income_percentile

    # Analyze ALL zones (cached by radius and weights) - slow operation, but cached
    with st.spinner("Analyse des zones en cours..."):
        # Convert weights dict to tuple for caching (dicts are not hashable)
        weights_tuple = (scoring_weights['housing'], scoring_weights['income'], scoring_weights['market'])
        all_scored_zones = analyze_all_zones(data, max_radius, weights_tuple)

    # Apply geographic filters (fast, in-memory operation)
    scored_zones = filter_zones_by_geography(all_scored_zones, selected_regions, selected_departments)
    
    # Optional city-based filter via selector
    if selected_city != "Aucune sélection":
        names = scored_zones['nom_commune'].fillna('')
        centers = scored_zones['center_commune'].fillna('') if 'center_commune' in scored_zones.columns else ""
        mask = names.str.contains(selected_city, case=False) | centers.str.contains(selected_city, case=False)
        scored_zones = scored_zones[mask]

    # Update ranks after filtering
    if len(scored_zones) > 0:
        scored_zones = scored_zones.sort_values('score_total', ascending=False).reset_index(drop=True)
        scored_zones['rank'] = range(1, len(scored_zones) + 1)

    # Display info about filtered data
    if 'code_departement' in data.columns and 'region' in data.columns:
        if len(scored_zones) > 0:
            st.sidebar.info(f"📍 {len(scored_zones)} zones après filtrage")
        else:
            st.sidebar.warning("⚠️ Aucune zone ne correspond aux filtres géographiques")
    
    # Check if we have results
    if len(scored_zones) == 0:
        st.error("Aucune zone ne correspond aux critères sélectionnés. Essayez d'assouplir les filtres.")
        return
    
    # Display number of zones filter
    st.sidebar.subheader("Affichage")
    
    # Adjust slider range based on available zones
    if len(scored_zones) >= 10:
        # Normal case: enough zones for a proper slider
        top_n = st.sidebar.slider(
            "Nombre de zones à afficher",
            min_value=10,
            max_value=min(100, len(scored_zones)),
            value=min(50, len(scored_zones)),
            step=10,
            help="Nombre de meilleures zones à visualiser"
        )
    elif len(scored_zones) > 1:
        # Few zones: use all available as range
        top_n = st.sidebar.slider(
            "Nombre de zones à afficher",
            min_value=1,
            max_value=len(scored_zones),
            value=len(scored_zones),
            step=1,
            help="Nombre de meilleures zones à visualiser"
        )
    else:
        # Only one zone or none
        top_n = len(scored_zones)
        st.sidebar.info(f"Affichage de {top_n} zone(s) disponible(s)")
    
    # Display current scoring weights
    st.info(f"🎯 **Pondération actuelle:** Logement {weight_housing}% | Revenus {weight_income}% | Taille marché {weight_market}%")

    # Main content tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Vue d'ensemble",
        "🗺️ Carte Interactive",
        "🏆 Top Zones",
        "🏅 Top 50 Communes",
        "📈 Analyses",
        "📚 Méthodologie & Données",
        "🧩 Architecture technique",
    ])
    
    # Tab 1: Overview
    with tab1:
        # Key metrics in premium cards
        st.markdown('<div class="custom-card-gradient">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Zones identifiées",
                value=len(scored_zones),
                help="Nombre total de zones respectant les critères"
            )

        with col2:
            avg_score = scored_zones['score_total'].mean()
            st.metric(
                label="Score moyen",
                value=f"{avg_score:.1f}/100",
                help="Score moyen de toutes les zones"
            )

        with col3:
            total_households = scored_zones['nb_menages'].sum()
            st.metric(
                label="Ménages totaux",
                value=utils.format_number(total_households),
                help="Total de ménages dans toutes les zones"
            )

        with col4:
            total_potential = scored_zones['potential_clients'].sum()
            st.metric(
                label="Clients potentiels",
                value=utils.format_number(total_potential, 0),
                help=f"Estimation basée sur {config.TARGET_CONVERSION_RATE*100}% de conversion"
            )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("")  # Spacing

        # Overview charts in premium cards
        col1, col2 = st.columns(2, gap="medium")

        with col1:
            with st.container():
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                fig_dist = map_viz.create_score_distribution(scored_zones)
                st.plotly_chart(fig_dist, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            with st.container():
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                fig_regional = map_viz.create_regional_bar_chart(scored_zones, top_n=top_n)
                st.plotly_chart(fig_regional, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        # Regional averages
        st.markdown('<h2 class="section-header">📊 Moyennes par Région</h2>', unsafe_allow_html=True)

        # Calculate regional statistics
        regional_stats = scored_zones.groupby('region').agg({
            'score_total': 'mean',
            'score_housing': 'mean',
            'score_income': 'mean',
            'score_market_size': 'mean',
            'nb_menages': 'sum',
            'potential_clients': 'sum',
            'zone_id': 'count'  # Number of zones per region
        }).reset_index()

        regional_stats.columns = ['Région', 'Score Total Moyen', 'Score Logement Moyen',
                                  'Score Revenus Moyen', 'Score Taille Moyen',
                                  'Total Ménages', 'Total Clients Potentiels', 'Nombre de Zones']

        # Sort by average total score
        regional_stats = regional_stats.sort_values('Score Total Moyen', ascending=False)

        # Display in two columns
        col1, col2 = st.columns(2, gap="medium")

        with col1:
            with st.container():
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                # Bar chart of average scores by region
                fig_avg_scores = px.bar(
                    regional_stats,
                    x='Région',
                    y='Score Total Moyen',
                    title='<b>Score Total Moyen par Région</b>',
                    color='Score Total Moyen',
                    color_continuous_scale=[[0, '#EF4444'], [0.3, '#F59E0B'], [0.5, '#EAB308'], [0.7, '#10B981'], [1, '#059669']],
                    labels={'Score Total Moyen': 'Score Moyen'}
                )
                fig_avg_scores = apply_premium_style(fig_avg_scores)
                fig_avg_scores.update_layout(
                    xaxis_tickangle=-45,
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig_avg_scores, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            with st.container():
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                # Display table with regional statistics
                display_regional_stats = regional_stats.copy()
                display_regional_stats['Score Total Moyen'] = display_regional_stats['Score Total Moyen'].apply(lambda x: f"{x:.1f}")
                display_regional_stats['Score Logement Moyen'] = display_regional_stats['Score Logement Moyen'].apply(lambda x: f"{x:.1f}")
                display_regional_stats['Score Revenus Moyen'] = display_regional_stats['Score Revenus Moyen'].apply(lambda x: f"{x:.1f}")
                display_regional_stats['Score Taille Moyen'] = display_regional_stats['Score Taille Moyen'].apply(lambda x: f"{x:.1f}")
                display_regional_stats['Total Ménages'] = display_regional_stats['Total Ménages'].apply(lambda x: utils.format_number(x))
                display_regional_stats['Total Clients Potentiels'] = display_regional_stats['Total Clients Potentiels'].apply(lambda x: utils.format_number(x, 0))

                st.dataframe(
                    display_regional_stats,
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
                st.markdown('</div>', unsafe_allow_html=True)

        # Breakdown of score components by region
        st.markdown('<h3 class="section-header">📈 Détail des Composantes par Région</h3>', unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            # Prepare data for grouped bar chart
            score_components = regional_stats[['Région', 'Score Logement Moyen', 'Score Revenus Moyen', 'Score Taille Moyen']].copy()
            score_components = score_components.melt(id_vars=['Région'], var_name='Composante', value_name='Score')
            score_components['Composante'] = score_components['Composante'].str.replace(' Moyen', '')

            fig_components = px.bar(
                score_components,
                x='Région',
                y='Score',
                color='Composante',
                barmode='group',
                title='<b>Comparaison des Composantes de Score par Région</b>',
                color_discrete_map={
                    'Score Logement': '#10B981',
                    'Score Revenus': '#3B82F6',
                    'Score Taille': '#F59E0B'
                }
            )
            fig_components = apply_premium_style(fig_components)
            fig_components.update_layout(
                xaxis_tickangle=-45,
                height=500,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor='rgba(255,255,255,0.9)',
                    bordercolor='#E2E8F0',
                    borderwidth=1
                )
            )
            st.plotly_chart(fig_components, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        # Top 20 zones quick view
        st.markdown('<h2 class="section-header">🏆 Top 20 Zones par Score</h2>', unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            top_20 = scored_zones.head(20)[['rank', 'nom_commune', 'region', 'nb_communes',
                                             'nb_menages', 'potential_clients', 'score_total']]
            top_20_display = top_20.copy()
            top_20_display['nb_menages'] = top_20_display['nb_menages'].apply(lambda x: utils.format_number(x))
            top_20_display['potential_clients'] = top_20_display['potential_clients'].apply(lambda x: utils.format_number(x, 0))
            top_20_display['score_total'] = top_20_display['score_total'].apply(lambda x: f"{x:.1f}")
            top_20_display.columns = ['Rang', 'Communes (échantillon)', 'Région', 'Nb Communes',
                                      'Ménages', 'Clients Pot.', 'Score']

            st.dataframe(top_20_display, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Tab 2: Interactive Map
    with tab2:
        st.subheader(f"🗺️ Carte des {top_n} Meilleures Zones")
        
        # Map type selection
        map_type = st.radio(
            "Type de carte",
            options=["Carte interactive (Folium)", "Carte scatter (Plotly)", "Heatmap"],
            horizontal=True
        )
        
        if map_type == "Carte interactive (Folium)":
            folium_map = map_viz.create_zone_map(scored_zones, top_n=top_n)
            st_folium(folium_map, width=1200, height=700)
            
        elif map_type == "Carte scatter (Plotly)":
            plotly_map = map_viz.create_plotly_scatter_map(scored_zones, top_n=top_n)
            st.plotly_chart(plotly_map, use_container_width=True)
            
        else:  # Heatmap
            heatmap = map_viz.create_heatmap(scored_zones.head(top_n))
            st_folium(heatmap, width=1200, height=700)
        
        st.info("💡 Cliquez sur les marqueurs pour voir les détails de chaque zone")
    
    # Tab 3: Top Zones Detailed View
    with tab3:
        st.subheader("🏆 Détails des Meilleures Zones")
        
        # Display top zones with detailed information
        for idx, zone in scored_zones.head(20).iterrows():
            with st.expander(f"#{int(zone['rank'])} - {zone['nom_commune']} ({zone['region']}) - Score: {zone['score_total']:.1f}/100"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("### 📍 Informations Générales")
                    st.write(f"**Région:** {zone['region']}")
                    st.write(f"**Département:** {zone['code_departement']}")
                    st.write(f"**Nombre de communes:** {int(zone['nb_communes'])}")
                    st.write(f"**Population totale:** {utils.format_number(zone['population_totale'])}")
                    st.write(f"**Nombre de ménages:** {utils.format_number(zone['nb_menages'])}")
                
                with col2:
                    st.markdown("### 🏠 Logements")
                    st.write(f"**Maisons individuelles:** {zone['pct_maisons']:.1f}%")
                    st.write(f"**Résidences principales:** {zone['pct_residences_principales']:.1f}%")
                
                with col3:
                    st.markdown("### 💰 Revenus & Potentiel")
                    st.write(f"**Revenu médian:** {utils.format_number(zone['revenu_median'], 0)}€")
                    st.write(f"**Niveau de vie médian:** {utils.format_number(zone['niveau_vie_median'], 0)}€")
                    st.write(f"**Taux de pauvreté:** {zone['taux_pauvrete']:.1f}%")
                    st.write(f"**Clients potentiels:** {utils.format_number(zone['potential_clients'], 0)}")
                
                # Score breakdown
                st.markdown("### 📊 Détail des Scores")
                score_cols = st.columns(3)
                with score_cols[0]:
                    st.metric("Logement", f"{zone['score_housing']:.1f}/100")
                with score_cols[1]:
                    st.metric("Revenus", f"{zone['score_income']:.1f}/100")
                with score_cols[2]:
                    st.metric("Taille marché", f"{zone['score_market_size']:.1f}/100")

    # Tab 4: Top 50 Communes
    with tab4:
        st.markdown('<h1 class="section-header">🏅 Top 50 Communes - Potentiel Business</h1>', unsafe_allow_html=True)

        st.markdown("""
        Ce classement présente les **50 meilleures communes individuelles** de France pour implanter
        une franchise Poubelles-Propres, basé sur un scoring business optimisé.
        """)

        # Calculate commune-level scores
        @st.cache_data
        def calculate_top50_communes(_data, weights_tuple):
            """Calculate top 50 communes with business scores"""
            import math

            weights = {'housing': weights_tuple[0], 'income': weights_tuple[1], 'market': weights_tuple[2]}
            communes = _data.copy()

            # Filter eligible communes
            communes = communes[
                (communes['pct_maisons'] >= 50) &
                (communes['pct_residences_principales'] >= 70) &
                (communes['nb_menages'] >= 1000) &
                (communes['revenu_median'] >= 24000)
            ].copy()

            # Calculate scores
            revenu_national = 26000

            communes['score_housing'] = (
                (communes['pct_maisons'] / 100) * 0.6 +
                (communes['pct_residences_principales'] / 100) * 0.4
            ) * 100

            communes['score_income'] = (
                communes['revenu_median'].apply(lambda x: min(x / (revenu_national * 1.5), 1)) * 0.7 +
                communes['taux_pauvrete'].apply(lambda x: max(0, (100 - x) / 100)) * 0.3
            ) * 100

            communes['score_market'] = communes['nb_menages'].apply(
                lambda x: min(100, (math.log(x + 1) / math.log(50000)) * 100)
            )

            communes['score_total'] = (
                communes['score_housing'] * weights['housing'] +
                communes['score_income'] * weights['income'] +
                communes['score_market'] * weights['market']
            )

            communes['potential_clients'] = (communes['nb_menages'] * config.TARGET_CONVERSION_RATE).astype(int)

            # Top 50
            top50 = communes.nlargest(50, 'score_total').reset_index(drop=True)
            top50['rank'] = range(1, 51)

            return top50

        with st.spinner("Calcul du Top 50 communes..."):
            weights_tuple = (scoring_weights['housing'], scoring_weights['income'], scoring_weights['market'])
            top50_communes = calculate_top50_communes(data, weights_tuple)

        # Key metrics for Top 50
        st.markdown('<div class="custom-card-gradient">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Score moyen Top 50",
                value=f"{top50_communes['score_total'].mean():.1f}/100"
            )

        with col2:
            st.metric(
                label="Ménages totaux",
                value=utils.format_number(top50_communes['nb_menages'].sum())
            )

        with col3:
            st.metric(
                label="Clients potentiels",
                value=utils.format_number(top50_communes['potential_clients'].sum(), 0)
            )

        with col4:
            st.metric(
                label="Régions représentées",
                value=top50_communes['region'].nunique()
            )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("")  # Spacing

        # Top 50 Table
        st.markdown('<h2 class="section-header">📋 Classement Détaillé</h2>', unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)

            display_top50 = top50_communes[[
                'rank', 'nom_commune', 'code_departement', 'region',
                'nb_menages', 'potential_clients', 'pct_maisons', 'revenu_median',
                'score_total'
            ]].copy()

            display_top50['nb_menages'] = display_top50['nb_menages'].apply(lambda x: utils.format_number(x))
            display_top50['potential_clients'] = display_top50['potential_clients'].apply(lambda x: utils.format_number(x, 0))
            display_top50['pct_maisons'] = display_top50['pct_maisons'].apply(lambda x: f"{x:.1f}%")
            display_top50['revenu_median'] = display_top50['revenu_median'].apply(lambda x: f"{utils.format_number(x, 0)}€")
            display_top50['score_total'] = display_top50['score_total'].apply(lambda x: f"{x:.1f}")

            display_top50.columns = [
                'Rang', 'Commune', 'Dép.', 'Région',
                'Ménages', 'Clients Pot.', '% Maisons', 'Revenu Médian', 'Score'
            ]

            st.dataframe(
                display_top50,
                use_container_width=True,
                hide_index=True,
                height=600
            )

            st.markdown('</div>', unsafe_allow_html=True)

        # Regional distribution
        col1, col2 = st.columns(2, gap="medium")

        with col1:
            st.markdown('<h3 class="section-header">🗺️ Répartition Géographique</h3>', unsafe_allow_html=True)

            with st.container():
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)

                region_counts = top50_communes['region'].value_counts().reset_index()
                region_counts.columns = ['Région', 'Nombre']

                fig_regions = px.bar(
                    region_counts,
                    x='Nombre',
                    y='Région',
                    orientation='h',
                    title='<b>Top 50 Communes par Région</b>',
                    color='Nombre',
                    color_continuous_scale=[[0, '#10B981'], [1, '#059669']]
                )
                fig_regions = apply_premium_style(fig_regions)
                fig_regions.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig_regions, use_container_width=True)

                st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<h3 class="section-header">📊 Distribution des Scores</h3>', unsafe_allow_html=True)

            with st.container():
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)

                fig_scores = go.Figure(data=[
                    go.Histogram(
                        x=top50_communes['score_total'],
                        nbinsx=15,
                        marker=dict(color='#10B981', line=dict(color='#059669', width=1), opacity=0.85),
                        hovertemplate='Score: %{x:.1f}<br>Communes: %{y}<extra></extra>'
                    )
                ])

                fig_scores.update_layout(
                    title=dict(text='<b>Distribution des Scores Top 50</b>', font=dict(size=18, color='#0F172A', family='Inter')),
                    xaxis=dict(title='Score Total', gridcolor='#E2E8F0', showgrid=True),
                    yaxis=dict(title='Nombre de communes', gridcolor='#E2E8F0', showgrid=True),
                    height=400,
                    margin={"r": 20, "t": 60, "l": 20, "b": 40},
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Inter', color='#64748B')
                )
                st.plotly_chart(fig_scores, use_container_width=True)

                st.markdown('</div>', unsafe_allow_html=True)

        # Export button
        st.markdown("---")
        st.markdown('<h3 class="section-header">💾 Export des Données</h3>', unsafe_allow_html=True)

        export_communes = top50_communes[[
            'rank', 'nom_commune', 'code_commune', 'code_departement', 'region',
            'nb_menages', 'population_totale', 'potential_clients',
            'pct_maisons', 'pct_residences_principales', 'revenu_median',
            'score_housing', 'score_income', 'score_market', 'score_total',
            'latitude', 'longitude'
        ]].copy()

        csv = export_communes.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 Télécharger le Top 50 Communes (CSV)",
            data=csv,
            file_name='top50_communes_poubelles_propres.csv',
            mime='text/csv',
        )

    # Tab 5: Analysis
    with tab5:
        st.markdown('<h1 class="section-header">📈 Analyses Complémentaires</h1>', unsafe_allow_html=True)

        # Display scoring weights as pie chart
        st.markdown('<h2 class="section-header">🎯 Pondération du Scoring</h2>', unsafe_allow_html=True)

        col1, col2 = st.columns([1, 2], gap="medium")

        with col1:
            st.markdown('<div class="custom-card-gradient">', unsafe_allow_html=True)
            st.markdown("**Poids actuels:**")
            st.metric("Logement", f"{weight_housing}%")
            st.metric("Revenus", f"{weight_income}%")
            st.metric("Taille marché", f"{weight_market}%")
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            with st.container():
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                # Pie chart of weights
                weights_df = pd.DataFrame({
                    'Critère': ['Logement', 'Revenus', 'Taille marché'],
                    'Pondération': [weight_housing, weight_income, weight_market]
                })
                fig_weights = px.pie(
                    weights_df,
                    values='Pondération',
                    names='Critère',
                    title='<b>Distribution des pondérations</b>',
                    color_discrete_sequence=['#10B981', '#3B82F6', '#F59E0B'],
                    hole=0.4
                )
                fig_weights = apply_premium_style(fig_weights)
                fig_weights.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    textfont_size=14
                )
                st.plotly_chart(fig_weights, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        # Score components correlation
        st.markdown('<h2 class="section-header">📊 Corrélation entre les Composantes du Score</h2>', unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            score_cols = ['score_housing', 'score_income', 'score_market_size', 'score_total']
            corr_matrix = scored_zones[score_cols].corr()

            fig_corr = px.imshow(
                corr_matrix,
                labels=dict(x="Composante", y="Composante", color="Corrélation"),
                x=['Logement', 'Revenus', 'Taille', 'Total'],
                y=['Logement', 'Revenus', 'Taille', 'Total'],
                color_continuous_scale=[[0, '#EF4444'], [0.5, '#F3F4F6'], [1, '#10B981']],
                aspect='auto',
                text_auto='.2f'
            )
            fig_corr = apply_premium_style(fig_corr)
            fig_corr.update_layout(height=500)
            fig_corr.update_traces(textfont_size=14, textfont_color='#0F172A')
            st.plotly_chart(fig_corr, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Scatter plots
        st.markdown('<h2 class="section-header">🔍 Relations entre Variables Clés</h2>', unsafe_allow_html=True)

        col1, col2 = st.columns(2, gap="medium")

        with col1:
            with st.container():
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                fig_scatter1 = px.scatter(
                    scored_zones.head(50),
                    x='revenu_median',
                    y='score_total',
                    size='nb_menages',
                    color='region',
                    hover_data=['nom_commune', 'rank'],
                    title='<b>Score vs Revenu Médian</b>',
                    labels={'revenu_median': 'Revenu Médian (€)', 'score_total': 'Score Total'},
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig_scatter1 = apply_premium_style(fig_scatter1)
                fig_scatter1.update_traces(marker=dict(line=dict(width=0.5, color='#E2E8F0')))
                st.plotly_chart(fig_scatter1, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            with st.container():
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                fig_scatter2 = px.scatter(
                    scored_zones.head(50),
                    x='pct_maisons',
                    y='score_total',
                    size='nb_menages',
                    color='region',
                    hover_data=['nom_commune', 'rank'],
                    title='<b>Score vs % Maisons Individuelles</b>',
                    labels={'pct_maisons': '% Maisons Individuelles', 'score_total': 'Score Total'},
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig_scatter2 = apply_premium_style(fig_scatter2)
                fig_scatter2.update_traces(marker=dict(line=dict(width=0.5, color='#E2E8F0')))
                st.plotly_chart(fig_scatter2, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Export data
        st.markdown("### 💾 Export des Données")
        
        # Prepare export data
        export_data = scored_zones[[
            'rank', 'zone_id', 'nom_commune', 'region', 'code_departement',
            'nb_communes', 'nb_menages', 'population_totale', 'potential_clients',
            'pct_maisons', 'pct_residences_principales', 'revenu_median',
            'score_housing', 'score_income', 'score_market_size', 'score_total',
            'latitude', 'longitude'
        ]].copy()
        
        # Download button
        csv = export_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger les résultats (CSV)",
            data=csv,
            file_name='poubelles_propres_zones_analyse.csv',
            mime='text/csv',
        )

    # Tab 6: Methodology & Data
    with tab6:
        st.title("📚 Méthodologie & Données")

        # Introduction
        st.markdown("""
        Cette page détaille les **sources de données**, la **méthodologie de calcul**,
        et les **limites** de l'analyse pour assurer la transparence et la reproductibilité.
        """)

        st.markdown("---")

        # Section 1: Sources de Données
        st.header("📊 1. Sources de Données")

        st.markdown("""
        L'analyse s'appuie sur des **données officielles INSEE** et **DGFiP** (Direction Générale des Finances Publiques),
        garantissant fiabilité et exhaustivité sur l'ensemble du territoire français.
        """)

        # Dataset 1: Population et Ménages
        with st.expander("📍 **Dataset 1: Population & Ménages (2021)**", expanded=True):
            st.markdown("""
            **Source:** Base logement INSEE 2021 (`base-cc-logement-2021.CSV`)

            **Données collectées:**
            - 🏘️ **Nombre de ménages** par commune (`P21_MEN`)
            - 👥 **Population totale** par commune (`P21_POP`)
            - 📍 **Code commune** (CODGEO) et nom (LIBGEO)

            **Traitement:**
            - Si population manquante : estimation à partir des ménages (2,2 personnes/ménage)
            - Agrégation au niveau zone après création des clusters

            **Couverture:** ~35 000 communes françaises

            **Limites:**
            - ⚠️ Données de 2021 (possibles évolutions depuis)
            - ⚠️ Estimation population si données manquantes
            """)

        # Dataset 2: Logements
        with st.expander("🏠 **Dataset 2: Logements (2021)**"):
            st.markdown("""
            **Source:** Base logement INSEE 2021 (`base-cc-logement-2021.CSV`)

            **Données collectées:**
            - 🏡 **Nombre de maisons individuelles** (`P21_MAISON`)
            - 🏢 **Nombre total de logements** (`P21_LOG`)
            - 🔑 **Résidences principales** (`P21_RP`)

            **Calculs dérivés:**
            ```python
            % Maisons = (Nb Maisons / Nb Logements) × 100
            % Résidences Principales = (Nb Rés. Principales / Nb Logements) × 100
            ```

            **Pertinence pour Poubelles-Propres:**
            - ✅ **Maisons individuelles** : Poubelles individuelles à gérer
            - ✅ **Résidences principales** : Clients réguliers (vs résidences secondaires)

            **Limites:**
            - ⚠️ Pas de distinction maisons avec/sans jardin
            - ⚠️ Résidences secondaires peuvent générer de la demande saisonnière
            """)

        # Dataset 3: Revenus
        with st.expander("💰 **Dataset 3: Revenus & Niveau de Vie (2013 → ajusté 2024)**"):
            st.markdown("""
            **Source:** Fichier Filosofi 2013 - Niveau de vie communal (DGFiP)

            **⚠️ IMPORTANT: Ajustement Inflation**
            Les données de revenus datent de **2013**. Pour garantir leur pertinence en 2024,
            un **ajustement automatique de +18%** est appliqué lors du chargement.

            **Formule appliquée:**
            ```python
            INFLATION_ADJUSTMENT = 1.18  # +18% inflation cumulée 2013-2024
            Revenu_2024 = Revenu_2013 × 1.18
            ```

            **Exemple concret:**
            | Métrique | Valeur 2013 | Valeur ajustée 2024 |
            |----------|-------------|---------------------|
            | Revenu médian France | 22 000 € | **25 960 €** (+18%) |
            | Niveau de vie médian | 29 000 € | **34 220 €** (+18%) |

            **Données collectées:**
            - 💵 **Revenu médian** par commune (ajusté)
            - 📊 **Niveau de vie médian** par commune (ajusté)
            - 📉 **Taux de pauvreté** (estimé à 14% si non disponible)

            **Limites:**
            - ⚠️ **Données obsolètes** : 11 ans d'ancienneté (2013)
            - ⚠️ **Ajustement uniforme** : L'inflation a pu varier selon les territoires
            - ⚠️ **Taux de pauvreté fixe** : Valeur par défaut si données manquantes
            - 💡 **Recommandation** : Intégrer API INSEE Filosofi 2020-2022 (Phase 3)
            """)

        # Dataset 4: Géographie
        with st.expander("🗺️ **Dataset 4: Données Géographiques**"):
            st.markdown("""
            **Source:** GeoJSON des communes françaises (france-geojson.gregoiredavid.fr)

            **Données collectées:**
            - 📍 **Latitude/Longitude** (centroïde de chaque commune)
            - 🏛️ **Code département** (2 premiers chiffres du code commune)
            - 🌍 **Géométrie** (polygones pour cartographie)

            **Traitement:**
            - Calcul du centroïde pour communes MultiPolygon
            - Mapping département → région (13 régions métropolitaines)

            **Utilisation:**
            - Attribution des communes aux zones (distance Haversine)
            - Affichage sur les cartes interactives

            **Limites:**
            - ⚠️ Centroïde ≠ centre-ville exact
            - ⚠️ Distance "à vol d'oiseau" (pas de routes)
            """)

        st.markdown("---")

        # Section 2: Méthodologie de Création des Zones
        st.header("⚙️ 2. Méthodologie de Création des Zones")

        st.markdown("""
        Les zones sont créées selon une **approche géographique centrée sur les villes**,
        garantissant des regroupements cohérents et sans chevauchement.
        """)

        # Étape 1: Filtrage
        with st.expander("🔍 **Étape 1: Filtrage des Communes Éligibles**", expanded=True):
            st.markdown(f"""
            **Objectif:** Sélectionner les communes répondant aux critères minimums

            **Critères d'éligibilité (au niveau commune):**
            ```python
            ✅ % Maisons individuelles     ≥ 20%
            ✅ % Résidences principales    ≥ 50%
            ✅ Nombre de ménages           ≥ 100
            ```

            **Justification:**
            - **20% maisons** : Critère souple pour inclure zones périurbaines
            - **50% résidences principales** : Éviter zones touristiques pures
            - **100 ménages** : Taille minimale pour être significatif

            **Résultat actuel:** ~{len(scored_zones):,} zones créées après filtrage et agrégation

            **Note:** Les critères **stricts** sont appliqués après agrégation (voir Étape 4)
            """)

        # Étape 2: Identification des centres
        with st.expander("🏙️ **Étape 2: Identification des Centres de Zones**"):
            st.markdown("""
            **Objectif:** Identifier les communes qui serviront de centres de zones

            **Critère:** Communes avec **≥ 1 000 habitants**

            **Logique:**
            - Les villes de taille moyenne/grande sont des centres naturels d'attractivité
            - Elles disposent généralement d'infrastructures et de main-d'œuvre
            - Facilitent la logistique pour le service Poubelles-Propres

            **Fallback:** Si < 100 centres trouvés, utiliser les 100 communes les plus peuplées

            **Exemple de centres:** Paris, Lyon, Marseille, Toulouse, Bordeaux, etc.
            """)

        # Étape 3: Attribution (KD-Tree)
        with st.expander("⚡ **Étape 3: Attribution des Communes aux Zones (Optimisé avec KD-Tree)**"):
            st.markdown(f"""
            **Objectif:** Rattacher chaque commune éligible au centre le plus proche

            **Algorithme: KD-Tree (Arbre de recherche spatiale)**

            **Principe:**
            1. Construction d'un **arbre KD-Tree** avec les centres de zones
            2. Pour chaque commune, **recherche du centre le plus proche** en temps logarithmique
            3. Assignation si distance ≤ **{max_radius} km** (rayon max configurable)

            **Avantages KD-Tree:**
            - ⚡ **50-80% plus rapide** que méthode brute force
            - 🔬 Complexité **O(n log m)** vs O(n × m) (n=communes, m=centres)
            - 📊 ~100 000 opérations vs ~35 millions de calculs

            **Distance calculée:** Haversine (distance "à vol d'oiseau" sur sphère terrestre)

            **Formule Haversine:**
            ```python
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)² + cos(lat1) × cos(lat2) × sin(dlon/2)²
            distance = 2 × 6371 × arcsin(√a)  # 6371 km = rayon Terre
            ```

            **Résultat:** Chaque commune appartient à **exactement UNE zone** (pas de chevauchement)

            **Limites:**
            - ⚠️ Distance aérienne ≠ distance routière (peut différer de 20-40%)
            - ⚠️ Ne prend pas en compte les obstacles géographiques (montagnes, fleuves)
            """)

        # Étape 4: Agrégation
        with st.expander("📊 **Étape 4: Agrégation au Niveau Zone**"):
            st.markdown("""
            **Objectif:** Calculer les statistiques au niveau de chaque zone

            **Métriques agrégées:**

            | Métrique | Méthode d'agrégation |
            |----------|---------------------|
            | **Population** | Somme des populations |
            | **Ménages** | Somme des ménages |
            | **Maisons individuelles** | Somme |
            | **% Maisons** | Moyenne pondérée |
            | **% Rés. principales** | Moyenne pondérée |
            | **Revenu médian** | Médiane des médianes |
            | **Taux de pauvreté** | Moyenne |
            | **Latitude/Longitude** | Moyenne (centre de la zone) |

            **Filtrage final des zones (critères stricts):**
            ```python
            ✅ % Maisons (zone)            ≥ 50%
            ✅ % Résidences principales    ≥ 70%
            ✅ Nombre de communes          ≥ 2
            ```

            **Justification critères stricts:**
            - **50% maisons** : Zone majoritairement pavillonnaire (cible Poubelles-Propres)
            - **70% résidences principales** : Clients réguliers, demande stable
            - **≥ 2 communes** : Éviter les zones isolées, favoriser économies d'échelle
            """)

        st.markdown("---")

        # Section 3: Système de Scoring
        st.header("🎯 3. Système de Scoring")

        st.markdown(f"""
        Chaque zone reçoit un **score total sur 100** basé sur 3 composantes,
        avec une **pondération personnalisable** selon la stratégie commerciale.

        **Pondération actuelle:**
        - 🏠 Logement: **{weight_housing}%**
        - 💰 Revenus: **{weight_income}%**
        - 📊 Taille marché: **{weight_market}%**
        """)

        # Score Logement
        with st.expander("🏠 **Score Logement** (0-100 points)"):
            st.markdown("""
            **Objectif:** Évaluer l'adéquation du parc immobilier avec le service

            **Calcul:**
            ```python
            Score_Maisons = normalize(% Maisons, min_zone, max_zone) × 60%
            Score_Rés_Principales = normalize(% Rés. Principales, min_zone, max_zone) × 40%

            Score_Logement = Score_Maisons + Score_Rés_Principales
            ```

            **Normalisation:** Min-Max entre toutes les zones
            ```python
            normalize(value, min, max) = ((value - min) / (max - min)) × 100
            ```

            **Interprétation:**
            - **80-100** : Zone très pavillonnaire (≥70% maisons)
            - **60-80** : Zone majoritairement pavillonnaire (50-70% maisons)
            - **40-60** : Zone mixte (40-50% maisons)
            - **<40** : Zone majoritairement collective

            **Poids dans le score total:** Variable selon pondération (par défaut 40%)
            """)

        # Score Revenus
        with st.expander("💰 **Score Revenus** (0-100 points)"):
            st.markdown("""
            **Objectif:** Mesurer le pouvoir d'achat et la capacité à payer le service

            **Calcul:**
            ```python
            Score_Revenu = normalize(Revenu_médian, 80% national, 150% national) × 70%
            Score_Anti_Pauvreté = normalize(-Taux_pauvreté, -max, -min) × 30%

            Score_Revenus = Score_Revenu + Score_Anti_Pauvreté
            ```

            **Benchmarks:**
            - Revenu médian national : ~25 960 € (ajusté 2024)
            - Borne basse : 20 768 € (80% du national)
            - Borne haute : 38 940 € (150% du national)

            **Interprétation:**
            - **80-100** : Zone aisée (revenus >130% national)
            - **60-80** : Zone au-dessus de la moyenne (100-130% national)
            - **40-60** : Zone moyenne (80-100% national)
            - **<40** : Zone sous la moyenne (<80% national)

            **Poids dans le score total:** Variable selon pondération (par défaut 30%)

            **Limites:**
            - ⚠️ Données 2013 ajustées (+18%) - Précision limitée
            - ⚠️ Taux de pauvreté parfois estimé (valeur par défaut 14%)
            """)

        # Score Taille Marché
        with st.expander("📊 **Score Taille du Marché** (0-100 points)"):
            st.markdown("""
            **Objectif:** Évaluer le potentiel commercial en termes de volume

            **Calcul:**
            ```python
            Score_Taille = normalize(log(Nb_ménages + 1), log(500), log(max_ménages))
            ```

            **Pourquoi une échelle logarithmique ?**
            - Évite que les très grandes zones (Paris, Lyon) écrasent les autres
            - Rend compte des **rendements décroissants** (doubler les ménages ≠ doubler le potentiel)
            - Favorise un équilibre entre grandes et moyennes zones

            **Exemple de scores:**
            | Nb ménages | Score Taille (approx.) |
            |------------|------------------------|
            | 500        | 0 (minimum)            |
            | 1 000      | 15                     |
            | 2 500      | 35                     |
            | 5 000      | 50                     |
            | 10 000     | 65                     |
            | 25 000     | 80                     |
            | 50 000+    | 90-100 (maximum)       |

            **Poids dans le score total:** Variable selon pondération (par défaut 30%)
            """)

        # Score Total
        with st.expander("🎯 **Score Total** (0-100 points)", expanded=True):
            st.markdown(f"""
            **Formule finale:**
            ```python
            Score_Total = (Score_Logement × W_Logement) +
                         (Score_Revenus × W_Revenus) +
                         (Score_Taille × W_Taille)

            où W_Logement + W_Revenus + W_Taille = 100%
            ```

            **Configuration actuelle:**
            - 🏠 W_Logement = **{weight_housing}%**
            - 💰 W_Revenus = **{weight_income}%**
            - 📊 W_Taille = **{weight_market}%**

            **Interprétation du score total:**
            | Score | Catégorie | Signification |
            |-------|-----------|---------------|
            | 80-100 | 🟢 Excellent | Zone prioritaire, potentiel maximal |
            | 60-80 | 🟢 Très bon | Zone très attractive |
            | 40-60 | 🟡 Bon | Zone prometteuse |
            | 20-40 | 🟠 Moyen | À considérer selon stratégie |
            | 0-20 | 🔴 Faible | Peu prioritaire |

            **Personnalisation:** Utilisez les presets dans la sidebar ou le mode Personnalisé
            pour ajuster les pondérations selon votre stratégie commerciale.
            """)

        st.markdown("---")

        # Section 4: Limites et Recommandations
        st.header("⚠️ 4. Limites de l'Analyse & Recommandations")

        # Limites des données
        with st.expander("📉 **Limites des Données**", expanded=True):
            st.markdown("""
            **1. Obsolescence des données de revenus**
            - ⚠️ **Données de 2013** (11 ans d'ancienneté)
            - ✅ Ajustement inflation +18% appliqué automatiquement
            - 💡 **Recommandation:** Intégrer API INSEE Filosofi 2020-2022 (Phase 3 roadmap)

            **2. Simplifications géographiques**
            - ⚠️ Distance aérienne ≠ distance routière (écart 20-40%)
            - ⚠️ Centroïde ≠ centre-ville exact
            - ⚠️ Pas de prise en compte des obstacles (montagnes, fleuves, autoroutes)
            - 💡 **Recommandation:** Intégrer API routière (Google Maps, HERE) pour distances réelles

            **3. Données démographiques figées**
            - ⚠️ Snapshot à une date donnée (2021)
            - ⚠️ Pas de projection des évolutions (nouveaux lotissements, exode rural)
            - 💡 **Recommandation:** Mise à jour annuelle avec nouvelles données INSEE

            **4. Simplification des ménages**
            - ⚠️ Tous les ménages traités de manière identique
            - ⚠️ Pas de distinction : familles, couples, célibataires, seniors
            - ⚠️ Pas de prise en compte de la taille du foyer
            - 💡 **Recommandation:** Affiner avec données démographiques détaillées (INSEE RP)
            """)

        # Limites méthodologiques
        with st.expander("🔬 **Limites Méthodologiques**"):
            st.markdown("""
            **1. Hypothèse d'homogénéité intra-zone**
            - ⚠️ Toutes les communes d'une zone sont traitées uniformément
            - ⚠️ Peut masquer des disparités locales importantes
            - 💡 **Recommandation:** Analyse de sensibilité au niveau infra-communal

            **2. Absence de prise en compte de la compétition**
            - ⚠️ Ne considère pas la présence de concurrents existants
            - ⚠️ Ne tient pas compte de la saturation du marché local
            - 💡 **Recommandation:** Ajouter couche "compétition" (Phase 3 - Scoring avancé)

            **3. Pas de synergie géographique**
            - ⚠️ Chaque zone évaluée indépendamment
            - ⚠️ Ne favorise pas les zones proches (économies d'échelle)
            - 💡 **Recommandation:** Bonus de synergie pour zones adjacentes (Phase 3)

            **4. Taux de conversion fixe**
            - ⚠️ Taux de 2% appliqué uniformément (estimation)
            - ⚠️ Peut varier significativement selon le contexte local
            - 💡 **Recommandation:** Modèle prédictif basé sur données réelles de conversion

            **5. Pas de saisonnalité**
            - ⚠️ Résidences secondaires traitées comme des non-clients
            - ⚠️ Ne considère pas la demande saisonnière (été, vacances)
            - 💡 **Recommandation:** Coefficient de saisonnalité pour zones touristiques
            """)

        # Recommandations d'utilisation
        with st.expander("💡 **Recommandations d'Utilisation**"):
            st.markdown("""
            **1. Utiliser l'analyse comme outil de pré-sélection**
            - ✅ Identifier les **20-30 zones les plus prometteuses**
            - ✅ Prioriser les investigations terrain
            - ⚠️ Ne pas se baser uniquement sur le score pour une décision finale

            **2. Compléter avec des données terrain**
            - 🔍 Visite sur place des zones top-scorées
            - 🔍 Enquête auprès des mairies locales
            - 🔍 Étude de la concurrence existante
            - 🔍 Évaluation de l'accessibilité réelle (routes, parkings)

            **3. Ajuster les pondérations selon la stratégie**
            - 🎯 **Focus Logement (60/20/20)** : Zones résidentielles pavillonnaires
            - 🎯 **Focus Revenus (20/60/20)** : Zones aisées, services premium
            - 🎯 **Focus Taille (20/20/60)** : Volume maximal, stratégie agressive
            - 🎯 **Marché (20/30/50)** : Optimisation chiffre d'affaires

            **4. Croiser avec d'autres sources**
            - 📊 Données cadastrales (taille des parcelles)
            - 📊 Données de l'ADEME (production de déchets)
            - 📊 Études de marché sectorielles
            - 📊 Retours d'expérience d'autres franchises

            **5. Réévaluer périodiquement**
            - 🔄 Mise à jour annuelle avec nouvelles données INSEE
            - 🔄 Intégration des retours terrain
            - 🔄 Ajustement des pondérations selon les résultats réels
            """)

        st.markdown("---")

        # Section 5: Évolutions Prévues
        st.header("🚀 5. Évolutions Prévues (Roadmap)")

        st.markdown("""
        **Phase 2 - Stabilisation (en cours)**
        - ✅ Optimisation performance (KD-Tree) - **FAIT**
        - ✅ Gestion d'erreurs robuste - **FAIT**
        - ✅ Ajustement inflation revenus - **FAIT**
        - 🔄 Tests unitaires automatisés
        - 🔄 Logging structuré

        **Phase 3 - Enrichissement des Données**
        - 📅 Intégration API INSEE Filosofi 2020-2022 (revenus récents)
        - 📅 Scoring avancé avec synergie géographique
        - 📅 Pénalité de compétition
        - 📅 Analyses prédictives (CA estimé, ROI, break-even)

        **Phase 4 - Professionnalisation**
        - 📅 Export Excel avec formatage conditionnel
        - 📅 Onglet "Qualité des Données" avec KPIs de fiabilité
        - 📅 Versioning des datasets
        - 📅 Documentation auto-générée
        """)

        st.markdown("---")

        # Section 6: Transparence & Reproductibilité
        st.header("🔬 6. Transparence & Reproductibilité")

        st.markdown("""
        **Open Source:** Le code source est disponible dans le repository du projet.

        **Reproductibilité:** Toutes les étapes de calcul sont documentées et peuvent être reproduites.

        **Auditabilité:** Les paramètres de configuration et les pondérations sont traçables.

        **Fichiers clés:**
        - `zone_analyzer.py` : Logique de création des zones et scoring
        - `data_collector.py` : Collecte et cache des données
        - `simple_insee_parser.py` : Parsing des fichiers INSEE
        - `config.py` : Paramètres de configuration
        - `AMELIORATIONS.md` : Détails techniques des optimisations

        **Contact:** Pour toute question sur la méthodologie ou les données, consultez la documentation
        technique ou créez une issue sur le repository.
        """)

        # Résumé visuel
        st.markdown("---")
        st.info("""
        **📌 En Résumé:**

        Cette analyse combine **données officielles INSEE**, **algorithmes géographiques optimisés**
        et **scoring personnalisable** pour identifier les zones de franchise les plus prometteuses.

        ⚠️ **Important:** Utilisez cette analyse comme **outil d'aide à la décision**,
        en complément d'investigations terrain et d'études de marché approfondies.

        🎯 **Objectif:** Maximiser l'efficacité du développement de votre réseau de franchises
        Poubelles-Propres en ciblant les zones à plus fort potentiel.
        """)

    # Tab 7: Technical Architecture
    with tab7:
        st.title("🧩 Architecture technique")

        st.markdown("""
        Cette page présente une **vue synthétique de l'architecture** de l'application :
        composants principaux, responsabilités, et flux de données.
        """)

        st.markdown("---")

        st.header("🏗️ 1. Vue d'ensemble")
        st.markdown("""
        L'application est structurée en **couches clairement séparées** :

        - **Interface utilisateur (`app.py`)** : application Streamlit, gestion des onglets, des filtres et de l'affichage.
        - **Couche données (`data_collector.py`, parseurs INSEE)** : chargement, nettoyage et mise en cache des données de base.
        - **Moteur métier (`zone_analyzer.py`)** : création des zones, calcul des agrégations et des scores.
        - **Visualisation (`map_viz.py`)** : génération des cartes et graphiques Plotly/Folium.
        - **Utilitaires & configuration (`utils.py`, `config.py`)** : fonctions transverses et paramètres centralisés.
        """)

        st.markdown("#### Schéma simplifié du flux de données")
        st.markdown("""
        ```text
        Fichiers INSEE / GeoJSON
                │
                ▼
        simple_insee_parser.py  →  data_collector.py  →  cache Streamlit (@st.cache_data)
                │
                ▼
            DataFrame complet (communes)
                │
                ▼
           add_region_info() (app.py)
                │
                ▼
           ZoneAnalyzer (zone_analyzer.py)
        (création zones + scoring)
                │
                ▼
           scored_zones (DataFrame zones)
                │
                ▼
        map_viz.py / composants Streamlit (onglets)
        ```
        """)

        st.markdown("---")

        st.header("🧠 2. Rôle des principaux modules")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("app.py (UI & orchestration)")
            st.markdown("""
            - Initialise la page Streamlit et les onglets.
            - Définit les filtres (géographiques, critères, pondérations).
            - Appelle les fonctions d'analyse (`analyze_all_zones`) et de filtrage.
            - Passe les `DataFrame` préparés aux fonctions de visualisation.
            """)

            st.subheader("data_collector.py (collecte des données)")
            st.markdown("""
            - Centralise le chargement des fichiers INSEE / DGFiP / GeoJSON.
            - Applique les premiers nettoyages et jointures.
            - Exposé via `get_data_collector()` et utilisé dans `load_data()` (caché).
            """)

            st.subheader("zone_analyzer.py (moteur de zones)")
            st.markdown("""
            - Crée les centres de zones à partir des communes.
            - Affecte les communes aux zones (KD-Tree + distance Haversine).
            - Agrège les indicateurs au niveau zone.
            - Calcule les scores par composante et le score total.
            """)

        with col2:
            st.subheader("map_viz.py (cartographie & graphiques)")
            st.markdown("""
            - Construit les cartes Folium (zones, heatmaps).
            - Construit les cartes Plotly (scatter geo, distributions).
            - Fournit les figures prêtes à être rendues dans les onglets.
            """)

            st.subheader("utils.py (utilitaires)")
            st.markdown("""
            - Fonctions de formatage (nombres, montants, pourcentages).
            - Fonctions de mapping (département → région, etc.).
            - Fonctions mathématiques communes (normalisation, etc.).
            """)

            st.subheader("config.py (paramétrage)")
            st.markdown("""
            - Paramètres par défaut (rayon max, seuils de filtrage, taux de conversion).
            - Constantes métiers (critères cibles, presets).
            - Point d'entrée pour surcharger la configuration sans modifier le cœur du code.
            """)

        st.markdown("---")

        st.header("⚙️ 3. Performances & cache")
        st.markdown("""
        - **`@st.cache_data`** est utilisé pour :
          - `load_data()` : chargement des données brutes (très coûteux, fait une seule fois).
          - `add_region_info()` : enrichissement des communes avec l'information de région.
          - `analyze_all_zones()` : création et scoring de toutes les zones pour un couple *(rayon, pondérations)*.
        - Les filtres (région, nombre de zones affichées, type de carte) agissent **en mémoire** sur les `DataFrame` déjà calculés.
        - Cette approche sépare :
          - les **calculs lourds** (cachés),
          - de l'**interaction utilisateur** (rapide, sans recalcul inutile).
        """)

        st.markdown("---")

        st.header("🧱 4. Découplage fonctionnel")
        st.markdown("""
        - L'interface (`app.py`) ne connaît que des **fonctions publiques** (ex. `ZoneAnalyzer`, `create_zone_map`, `create_score_distribution`),
          ce qui facilite :
          - le **remplacement** d'un module (ex : nouvelle implémentation de `ZoneAnalyzer`),
          - l'**ajout** de nouveaux onglets / visualisations,
          - l'écriture de **tests unitaires** ciblés sur chaque brique.
        - Les constantes métiers sont **centralisées dans `config.py`**, évitant la duplication et rendant l'application plus maintenable.
        """)

        st.markdown("---")

        st.header("🚀 5. Pistes d'évolution architecture")
        st.markdown("""
        - Extraire la logique Streamlit vers un **package Python** réutilisable (librairie interne).
        - Ajouter une **couche API** (FastAPI/Flask) pour exposer les calculs à d'autres frontends.
        - Introduire un **système de logging structuré** (par exemple `logging` + handlers JSON).
        - Mettre en place des **tests automatiques** pour `zone_analyzer`, `data_collector` et `map_viz`.
        """)

    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p><b>Poubelles-Propres.fr</b> - Analyse de Zones de Franchise</p>
        <p style="font-size: 0.9rem;">Données: INSEE | Scoring personnalisable: Logements ({weight_housing}%), Revenus ({weight_income}%), Taille marché ({weight_market}%)</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
