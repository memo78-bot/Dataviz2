"""
Map visualization module
Creates interactive maps for displaying franchise zones
"""

import folium
from folium import plugins
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import config
import utils
import plotly.express as px
import plotly.graph_objects as go


def create_base_map(center: list = None, zoom: int = None) -> folium.Map:
    """
    Create base map of France with premium styling

    Args:
        center: [latitude, longitude] for map center
        zoom: Initial zoom level

    Returns:
        Folium Map object
    """
    if center is None:
        center = config.MAP_CENTER
    if zoom is None:
        zoom = config.MAP_ZOOM

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles='CartoDB positron',  # Clean, modern map style
        control_scale=True,
        prefer_canvas=True
    )

    return m


def get_color_for_score(score: float) -> str:
    """
    Get color based on zone score - Premium palette

    Args:
        score: Zone score (0-100)

    Returns:
        Hex color code
    """
    if score >= 80:
        return '#059669'  # Emerald (excellent)
    elif score >= 60:
        return '#10B981'  # Green (very good)
    elif score >= 40:
        return '#F59E0B'  # Amber (good)
    elif score >= 20:
        return '#F97316'  # Orange (fair)
    else:
        return '#EF4444'  # Red (poor)


def create_zone_map(zones_df: pd.DataFrame, top_n: int = None) -> folium.Map:
    """
    Create interactive map with zones
    
    Args:
        zones_df: DataFrame with zone data including lat/lon and scores
        top_n: If specified, highlight only top N zones
        
    Returns:
        Folium Map object
    """
    # Create base map
    m = create_base_map()
    
    # Filter to top N if specified
    if top_n is not None:
        display_zones = zones_df.head(top_n).copy()
    else:
        display_zones = zones_df.copy()
    
    # Add markers for each zone
    for idx, row in display_zones.iterrows():
        # Determine marker properties based on score
        color = get_color_for_score(row['score_total'])
        
        # Marker size based on rank (top zones are bigger)
        if top_n is not None and idx < 20:
            radius = 15 + (20 - idx)  # Top 20 are bigger
            fill_opacity = 0.8
        else:
            radius = 10
            fill_opacity = 0.6
        
        # Create popup content
        popup_html = f"""
        <div style="font-family: Arial; width: 300px;">
            <h4 style="margin: 0; color: {color};">Zone #{int(row['rank'])}</h4>
            <hr style="margin: 5px 0;">
            <p style="margin: 5px 0;"><b>Communes:</b> {row['nom_commune']}</p>
            <p style="margin: 5px 0;"><b>Région:</b> {row['region']}</p>
            <hr style="margin: 5px 0;">
            <p style="margin: 5px 0;"><b>Score Total:</b> {row['score_total']:.1f}/100</p>
            <p style="margin: 5px 0;"><b>Ménages:</b> {utils.format_number(row['nb_menages'])}</p>
            <p style="margin: 5px 0;"><b>Clients potentiels:</b> {utils.format_number(row['potential_clients'], 0)}</p>
            <hr style="margin: 5px 0;">
            <p style="margin: 5px 0; font-size: 11px;"><b>Maisons individuelles:</b> {row['pct_maisons']:.1f}%</p>
            <p style="margin: 5px 0; font-size: 11px;"><b>Revenu médian:</b> {utils.format_number(row['revenu_median'], 0)}€</p>
        </div>
        """
        
        # Add circle marker with commune name in tooltip
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=fill_opacity,
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=f"{row['nom_commune']} - Zone #{int(row['rank'])} - Score: {row['score_total']:.1f}"
        ).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 200px; height: 180px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
        <p style="margin: 0; font-weight: bold; text-align: center;">Score des Zones</p>
        <hr style="margin: 5px 0;">
        <p style="margin: 5px 0;"><span style="background-color: #2E7D32; padding: 3px 10px; margin-right: 5px;"></span> 80-100 (Excellent)</p>
        <p style="margin: 5px 0;"><span style="background-color: #66BB6A; padding: 3px 10px; margin-right: 5px;"></span> 60-80 (Très bon)</p>
        <p style="margin: 5px 0;"><span style="background-color: #FDD835; padding: 3px 10px; margin-right: 5px;"></span> 40-60 (Bon)</p>
        <p style="margin: 5px 0;"><span style="background-color: #FB8C00; padding: 3px 10px; margin-right: 5px;"></span> 20-40 (Moyen)</p>
        <p style="margin: 5px 0;"><span style="background-color: #E53935; padding: 3px 10px; margin-right: 5px;"></span> 0-20 (Faible)</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m


def create_heatmap(zones_df: pd.DataFrame) -> folium.Map:
    """
    Create heatmap visualization of zones
    
    Args:
        zones_df: DataFrame with zone data
        
    Returns:
        Folium Map with heatmap
    """
    # Create base map
    m = create_base_map()
    
    # Prepare heatmap data [lat, lon, weight]
    heat_data = []
    for idx, row in zones_df.iterrows():
        # Use score as weight
        heat_data.append([row['latitude'], row['longitude'], row['score_total']])
    
    # Add heatmap layer
    plugins.HeatMap(
        heat_data,
        min_opacity=0.3,
        max_zoom=13,
        radius=25,
        blur=30,
        gradient={0.0: 'blue', 0.5: 'yellow', 0.75: 'orange', 1.0: 'red'}
    ).add_to(m)
    
    return m


def create_plotly_scatter_map(zones_df: pd.DataFrame, top_n: int = None) -> go.Figure:
    """
    Create interactive Plotly scatter map
    
    Args:
        zones_df: DataFrame with zone data
        top_n: If specified, show only top N zones
        
    Returns:
        Plotly Figure object
    """
    # Filter to top N if specified
    if top_n is not None:
        display_zones = zones_df.head(top_n).copy()
    else:
        display_zones = zones_df.copy()
    
    # Create custom hover text with commune name prominently displayed
    display_zones['hover_text'] = display_zones.apply(
        lambda row: f"<b>{row['nom_commune']}</b><br>" +
                    f"Zone #{int(row['rank'])} - Score: {row['score_total']:.1f}/100<br>" +
                    f"Région: {row['region']}<br>" +
                    f"Ménages: {utils.format_number(row['nb_menages'])}<br>" +
                    f"Clients potentiels: {utils.format_number(row['potential_clients'], 0)}<br>" +
                    f"Maisons: {row['pct_maisons']:.1f}%<br>" +
                    f"Revenu: {utils.format_number(row['revenu_median'], 0)}€",
        axis=1
    )

    # Create scatter map
    fig = px.scatter_mapbox(
        display_zones,
        lat='latitude',
        lon='longitude',
        size='nb_menages',
        color='score_total',
        hover_name='nom_commune',
        hover_data={
            'latitude': False,
            'longitude': False,
            'nb_menages': False,
            'score_total': False,
            'nom_commune': False,
            'hover_text': True
        },
        color_continuous_scale=['#E53935', '#FB8C00', '#FDD835', '#66BB6A', '#2E7D32'],
        size_max=30,
        zoom=5,
        mapbox_style='open-street-map',
        title='Zones de Chalandise Potentielles - Poubelles-Propres'
    )
    
    fig.update_layout(
        height=700,
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        coloraxis_colorbar=dict(
            title="Score",
            tickvals=[0, 25, 50, 75, 100],
            ticktext=['0', '25', '50', '75', '100']
        )
    )
    
    return fig


def create_regional_bar_chart(zones_df: pd.DataFrame, top_n: int = 50) -> go.Figure:
    """
    Create bar chart showing zones by region - Premium style

    Args:
        zones_df: DataFrame with zone data
        top_n: Number of top zones to include

    Returns:
        Plotly Figure object
    """
    # Get top zones
    top_zones = zones_df.head(top_n)

    # Count zones by region
    region_counts = top_zones.groupby('region').size().reset_index(name='count')
    region_counts = region_counts.sort_values('count', ascending=True)

    # Create bar chart with gradient
    fig = go.Figure(data=[
        go.Bar(
            y=region_counts['region'],
            x=region_counts['count'],
            orientation='h',
            marker=dict(
                color=region_counts['count'],
                colorscale=[[0, '#10B981'], [1, '#059669']],
                line=dict(width=0)
            ),
            text=region_counts['count'],
            textposition='auto',
            textfont=dict(size=13, color='white', family='Inter'),
            hovertemplate='<b>%{y}</b><br>Zones: %{x}<extra></extra>'
        )
    ])

    fig.update_layout(
        title=dict(
            text=f'<b>Distribution des Top {top_n} Zones par Région</b>',
            font=dict(size=18, color='#0F172A', family='Inter')
        ),
        xaxis=dict(
            title='Nombre de zones',
            gridcolor='#E2E8F0',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            title='',
            showgrid=False
        ),
        height=400,
        margin={"r": 20, "t": 60, "l": 20, "b": 40},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', color='#64748B'),
        hoverlabel=dict(
            bgcolor='#0F172A',
            font_size=13,
            font_family='Inter'
        )
    )

    return fig


def create_score_distribution(zones_df: pd.DataFrame) -> go.Figure:
    """
    Create histogram of zone scores - Premium style

    Args:
        zones_df: DataFrame with zone data

    Returns:
        Plotly Figure object
    """
    fig = go.Figure(data=[
        go.Histogram(
            x=zones_df['score_total'],
            nbinsx=20,
            marker=dict(
                color='#10B981',
                line=dict(color='#059669', width=1),
                opacity=0.85
            ),
            hovertemplate='Score: %{x:.1f}<br>Zones: %{y}<extra></extra>'
        )
    ])

    fig.update_layout(
        title=dict(
            text='<b>Distribution des Scores de Zones</b>',
            font=dict(size=18, color='#0F172A', family='Inter')
        ),
        xaxis=dict(
            title='Score Total',
            gridcolor='#E2E8F0',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            title='Nombre de zones',
            gridcolor='#E2E8F0',
            showgrid=True,
            zeroline=False
        ),
        height=400,
        margin={"r": 20, "t": 60, "l": 20, "b": 40},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', color='#64748B'),
        hoverlabel=dict(
            bgcolor='#0F172A',
            font_size=13,
            font_family='Inter'
        )
    )

    return fig
