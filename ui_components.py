"""Composants d'interface utilisateur pour le dashboard"""

import streamlit as st
import pandas as pd


def setup_sidebar_controls(all_indicators):
    """Configure les contrôles de la barre latérale"""
    with st.sidebar:
        st.subheader("Pondérations des indicateurs")
        poids_indicateurs = {}
        for indic in all_indicators:
            poids_indicateurs[indic] = st.number_input(
                f"Poids pour '{indic}'", min_value=0.0, value=1.0, step=0.1
            )
        
        st.subheader("Seuil pour l'évolution Score global dans le temps :")
        seuil = st.slider("Seuil du score global (%)", min_value=0, max_value=100, value=50)
    
    return poids_indicateurs, seuil


def setup_date_and_granularity_filters(min_date, max_date):
    """Configure les filtres de date et de granularité"""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        date_range = st.date_input(
            "Intervalle de temps",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
    
    with col2:
        granularite = st.radio(
            "Granularité temporelle :", 
            ["Jour", "Semaine", "Mois", "Trimestre"], 
            horizontal=True
        )
    
    return date_range, granularite


def setup_referentiel_filter(df):
    """Configure le filtre de référentiel"""
    referentiels = df['Référentiel'].dropna().unique()
    selected_referentiel = st.selectbox("Sélectionnez le référentiel", referentiels)
    return selected_referentiel


def setup_table_filter(filtered_df):
    """Configure le filtre de table"""
    selected_table = st.selectbox("Sélectionner une table", filtered_df["TABLE_NAME"].unique())
    return selected_table


def setup_field_and_indicator_filters(df, indicateurs_disponibles):
    """Configure les filtres de champ et d'indicateur"""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Création du filtre Champ avec affichage "Référentiel - Table ref - Champ"
        df['Champ Full'] = df['COLUMN_NAME'] + ' - ' + df['TABLE_NAME'] + ' - ' + df['Référentiel']
        unique_champs = df['Champ Full'].unique()
        champ = st.selectbox("Sélectionner un champ", unique_champs)
        
        # Extraire les composantes pour filtrer ensuite
        champ_selectionne, selected_table, selected_ref = champ.split(' - ')
    
    with col2:
        indicator_selected = st.radio(
            "Choisissez un indicateur :",
            indicateurs_disponibles,
            horizontal=True
        )
    
    return champ_selectionne, selected_table, selected_ref, indicator_selected


def display_styled_dataframe(pivot_table, title):
    """Affiche un DataFrame stylé avec des couleurs dégradées"""
    from viz_components import gradient_color
    
    st.subheader(title)
    styled_df = pivot_table.round(2).style.format("{:.2f}%").applymap(gradient_color)
    st.dataframe(styled_df, use_container_width=True)


def validate_date_range(date_range, tz):
    """Valide et convertit la plage de dates"""
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        start_datetime = pd.Timestamp(start_date).tz_localize(tz)
        end_datetime = pd.Timestamp(end_date).tz_localize(tz) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        return start_datetime, end_datetime
    else:
        st.warning("Veuillez sélectionner une plage de dates.")
        return None, None