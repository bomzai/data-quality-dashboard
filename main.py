import streamlit as st
import pandas as pd
from config import DEFAULT_CONFIG
from data_utils import (
    load_data_from_snowflake, get_date_range, apply_granularity,
    interpret_score, calculate_temporal_score, create_pivot_table
)
from ui_components import (
    setup_sidebar_controls, setup_date_and_granularity_filters,
    setup_referentiel_filter, setup_table_filter,
    setup_field_and_indicator_filters, display_styled_dataframe,
    validate_date_range
)
from viz_components import (
    display_global_score_card, create_evolution_chart,
    display_donut_charts, create_indicator_evolution_chart,
    create_percentage_bar_charts, create_heatmap
)


def main():
    """Fonction principale de l'application"""
    # Configuration de la page
    st.set_page_config(layout=DEFAULT_CONFIG["layout"])
    
    # Titre et description
    st.title("Data Quality Dashboards")
    st.write("""
    Ceci est **un exemple** de visualisations pour illustrer la qualité des données.
    """)
    
    # Chargement des données
    df, tz = load_data_from_snowflake()
    min_date, max_date = get_date_range(df)
    
    # Préparation des données
    timestamp_latest = df["SCAN_TIMESTAMP"].max().normalize()
    df_latest = df[df["SCAN_TIMESTAMP"].dt.normalize() == timestamp_latest]
    all_indicators = sorted(df_latest["Indicateur"].unique())
    
    # Configuration des contrôles de la barre latérale
    poids_indicateurs, seuil = setup_sidebar_controls(all_indicators)
    
    # Calcul du score final
    score_final = calculate_temporal_score(df, all_indicators, poids_indicateurs)
    
    # Affichage de la carte du score global
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            display_global_score_card(score_final, timestamp_latest, poids_indicateurs)
    
    # Filtres de date et granularité
    date_range, granularite = setup_date_and_granularity_filters(min_date, max_date)
    start_datetime, end_datetime = validate_date_range(date_range, tz)
    
    if start_datetime is None or end_datetime is None:
        return
    
    # Application des filtres
    df = df[(df["SCAN_TIMESTAMP"].dt.date >= min_date) & (df["SCAN_TIMESTAMP"].dt.date <= max_date)]
    
    # Évolution du score global dans le temps
    df_filtered = df[df["Indicateur"].isin(all_indicators)]
    df_filtered["Granularité"] = apply_granularity(df_filtered, granularite)
    df_scores = df_filtered.groupby("Granularité").apply(
        lambda x: calculate_temporal_score(x, all_indicators, poids_indicateurs)
    ).reset_index(name="Score global")
    
    # Affichage du graphique d'évolution
    evolution_chart = create_evolution_chart(df_scores, seuil)
    st.altair_chart(evolution_chart, use_container_width=True)
    
    # Filtrage par intervalle de dates
    df_with_interval = df[(df["SCAN_TIMESTAMP"] >= start_datetime) & (df["SCAN_TIMESTAMP"] <= end_datetime)]
    
    # Sélection du référentiel et visualisations par référentiel
    selected_referentiel = setup_referentiel_filter(df)
    df_ref = df_with_interval[df_with_interval['Référentiel'] == selected_referentiel]
    
    # Calcul des scores par indicateur
    indicateurs = df_ref['Indicateur'].unique()
    scores = {}
    global_score = 0
    for i in indicateurs:
        data = df_ref.loc[df_ref["Indicateur"] == i]
        score = interpret_score(data)
        scores[i] = score
        global_score += score
    global_score = global_score / len(indicateurs) if len(indicateurs) > 0 else 0
    
    # Affichage des graphiques en donut
    display_donut_charts(df_ref, scores, global_score)
    
    # Tableaux croisés dynamiques
    filtered_df = df_with_interval[df_with_interval["Référentiel"] == selected_referentiel]
    
    # Tableau par table et indicateur
    pivot_table = create_pivot_table(filtered_df, ["TABLE_NAME", "Indicateur"])
    display_styled_dataframe(
        pivot_table, 
        f"Taux de réussite par table pour le référentiel : {selected_referentiel}"
    )
    
    # Tableau par champ et indicateur
    selected_table = setup_table_filter(filtered_df)
    filtered_table_df = filtered_df[filtered_df["TABLE_NAME"] == selected_table]
    pivot_champ = create_pivot_table(filtered_table_df, ["COLUMN_NAME", "Indicateur"])
    display_styled_dataframe(
        pivot_champ,
        f"Taux de réussite par champ pour la table : {selected_table}"
    )
    
    # Évolution par indicateur spécifique
    indicateurs_disponibles = df["Indicateur"].unique().tolist()
    champ_selectionne, selected_table, selected_ref, indicator_selected = setup_field_and_indicator_filters(
        df, indicateurs_disponibles
    )
    
    # Affichage de l'évolution de l'indicateur
    st.subheader("Évolution par indicateur")
    df_indicator_filtered = df[
        (df["COLUMN_NAME"] == champ_selectionne) &
        (df["Indicateur"] == indicator_selected)
    ]
    
    if df_indicator_filtered.empty:
        st.warning("Aucune donnée disponible pour l'indicateur sélectionné.")
    else:
        df_indicator_filtered["Date"] = apply_granularity(df_indicator_filtered, granularite)
        df_indicator_filtered["Résultat"] = pd.to_numeric(df_indicator_filtered["Résultat"], errors="coerce")
        df_indicator_filtered = df_indicator_filtered.groupby("Date", as_index=False)["Résultat"].mean()
        
        latest_value = df_indicator_filtered[df_indicator_filtered["Date"].dt.date == max_date]["Résultat"].mean()
        st.markdown(f"**Valeur de l'indicateur le {max_date.strftime('%d-%m-%Y')} :** {latest_value:.2f}")
        
        indicator_chart = create_indicator_evolution_chart(
            df_indicator_filtered, indicator_selected, champ_selectionne, seuil
        )
        st.altair_chart(indicator_chart, use_container_width=True)
    
    # Graphiques de pourcentage
    _df_bool = df.copy()
    _df_bool["Date"] = apply_granularity(_df_bool, granularite)
    df_counts_date = _df_bool.groupby(["Date", "OUTCOME"]).size().reset_index(name="counts")
    df_counts_date["percentage"] = df_counts_date.groupby("Date")["counts"].transform(lambda x: x/x.sum())
    
    _df_table = df.copy()
    fct = _df_table.groupby(["TABLE_NAME", "OUTCOME"]).size().reset_index(name="counts")
    fct["percentage"] = fct.groupby("TABLE_NAME")["counts"].transform(lambda x: x/x.sum())
    
    create_percentage_bar_charts(df_counts_date, fct)
    
    # Carte de chaleur
    df_hm = df.copy()
    df_hm["Periode"] = apply_granularity(df_hm, granularite)
    df_hm["Periode"] = pd.to_datetime(df_hm["Periode"]).dt.strftime('%d-%m-%Y')
    df_ok = df_hm[df_hm["OUTCOME"] == "pass"]
    all_p = sorted(df_hm["Periode"].unique(), key=lambda x: pd.to_datetime(x, format='%d-%m-%Y'))
    df_grp = df_ok.groupby(["Periode", "Indicateur"]).size().reset_index(name="Tests_OK")
    _df_full = pd.DataFrame(
        index=pd.MultiIndex.from_product([all_p, df_ok["Indicateur"].unique()], names=["Periode", "Indicateur"])
    )
    df_full = (_df_full.reset_index().merge(df_grp, on=["Periode", "Indicateur"], how="left").fillna(0))
    df_full["Tests_OK"] = df_full["Tests_OK"].astype(int)
    
    create_heatmap(df_full, all_p)


if __name__ == "__main__":
    main()