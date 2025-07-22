"""Composants de visualisation pour le dashboard de qualité des données"""

import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from config import COLORS, THRESHOLDS, BOOLEAN_INDICATORS


def display_global_score_card(score_final, timestamp_latest, poids_indicateurs):
    """Affiche la carte du score global"""
    # Détermination de la couleur
    if score_final < THRESHOLDS["warning"]:
        color = COLORS["danger"]
    elif score_final < THRESHOLDS["good"]:
        color = COLORS["warning"]
    else:
        color = COLORS["success"]
    
    html_ponds = "<br>".join([f"{k} : {v}" for k, v in poids_indicateurs.items()])
    
    st.components.v1.html(f"""
        <div style='background:#ffffff; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.15); padding:24px; text-align:center; position:relative;'>
          <div style='font-size:96px; font-weight:800; color:{color}; line-height:1;'>{score_final:.1f}%</div>
          <div style='margin-top:8px; color:#555555; font-size:16px;'>calculé le {timestamp_latest.strftime('%d-%m-%Y')}</div>
          <button onclick=\"document.getElementById('info-box').style.display='block'\" style='position:absolute; top:8px; right:8px; background:none; border:none; font-size:14px;'>ℹ️ Méthode & Pondérations</button>
          <div id='info-box' style='display:none; position:absolute; top:50px; right:8px; background:#f9f9f9; border:1px solid #ddd; border-radius:8px; padding:16px; width:320px; z-index:10; text-align:left; font-size:13px;'>
            <strong>Méthode de calcul :</strong><br>
            - <strong>Booléens</strong> : 1 → 100%, 0 → 0%<br>
            - <strong>Non booléens</strong> : valeur brute<br>
            <em>Formule</em> : somme(poids × score) / somme(poids)<br><br>
            <strong>Pondérations :</strong><br>
            {html_ponds}<br><br>
            <button onclick=\"document.getElementById('info-box').style.display='none'\" style='margin-top:8px;'>Fermer</button>
          </div>
        </div>
    """, height=300)


def create_evolution_chart(df_scores, seuil):
    """Crée le graphique d'évolution du score global"""
    line_chart = alt.Chart(df_scores).mark_line(point=True).encode(
        x=alt.X("Granularité:T", title="Date"),
        y=alt.Y("Score global:Q", title="Score global (%)", scale=alt.Scale(domain=[0, 100])),
        tooltip=["Granularité", "Score global"]
    )

    seuil_line = alt.Chart(pd.DataFrame({'y': [seuil]})).mark_rule(
        color='red',
        strokeDash=[4,4]
    ).encode(
        y=alt.Y('y:Q')
    )

    chart = (line_chart + seuil_line).properties(
        title="Évolution du score global dans le temps",
        width="container",
        height=300
    )
    
    return chart


def create_donut_chart(taux_ok, taux_ko, title, size="normal"):
    """Crée un graphique en donut"""
    sizes = {
        "small": {"height": 150, "width": 250, "font_size": 14},
        "normal": {"height": 300, "width": 350, "font_size": 37}
    }
    
    config = sizes[size]
    
    fig = go.Figure(data=[go.Pie(
        labels=["OK", "KO"],
        values=[taux_ok, taux_ko],
        hole=0.7,
        marker_colors=[COLORS["ok"], COLORS["ko"]],
        textinfo='percent'
    )])
    
    fig.update_layout(
        showlegend=(size == "normal"),
        annotations=[dict(
            text=str(round(taux_ok, 2)) + "%",
            x=0.5, y=0.5,
            font=dict(size=config["font_size"], family="Arial Black", color="grey"),
            showarrow=False,
            align='center'
        )],
        title={'text': title, 'x': 0.5, 'xanchor': 'center'},
        margin=dict(t=30, b=30, l=0, r=0),
        height=config["height"],
        width=config["width"]
    )
    
    return fig


def display_donut_charts(df_ref, scores, global_score):
    """Affiche les graphiques en donut pour chaque indicateur"""
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### QDD global")
        taux_ok_global = global_score
        taux_ko_global = 100 - taux_ok_global
        
        fig_global = create_donut_chart(taux_ok_global, taux_ko_global, "Global", "normal")
        st.plotly_chart(fig_global)

    with col2:
        st.markdown("### Taux de réussite par indicateur")
        indicateurs = df_ref['Indicateur'].unique()
        
        for i in range(0, len(indicateurs), 3):
            row_cols = st.columns(3)
            for j in range(3):
                if i + j < len(indicateurs):
                    indicateur = indicateurs[i + j]
                    taux_ok = scores[indicateur]
                    taux_ko = 100 - taux_ok
                    
                    fig = create_donut_chart(taux_ok, taux_ko, indicateur, "small")
                    with row_cols[j]:
                        st.plotly_chart(fig)


def gradient_color(val):
    """Fonction de style dégradé rouge -> vert pour les DataFrames"""
    try:
        val = float(val)
        if val <= 50:
            r = 255
            g = int((val / 50) * 50)
            b = 0
        elif val <= 60:
            r = 255
            g = int(50 + (val - 50) * 11.5)
            b = 0
        else:
            ratio = (val - 60) / 40
            r = int(255 * (1 - ratio))
            g = int(165 + (90 * ratio))
            b = int(0 + (90 * ratio))
        return f'background-color: rgb({r}, {g}, {b}); color: black'
    except:
        return ''


def create_indicator_evolution_chart(df_filtered, indicator_selected, champ_selectionne, seuil):
    """Crée le graphique d'évolution pour un indicateur spécifique"""
    line = alt.Chart(df_filtered).mark_line(point=True).encode(
        x=alt.X("Date:T", title="Date", axis=alt.Axis(format='%d-%m-%Y', labelAngle=-45)),
        y=alt.Y("Résultat:Q", title="Résultat du test"),
        tooltip=[alt.Tooltip("Date:T", format='%d-%m-%Y'), "Résultat"]
    )
    
    if indicator_selected not in BOOLEAN_INDICATORS:
        rule = alt.Chart(pd.DataFrame({'y': [seuil]})).mark_rule(
            color='red', strokeDash=[4, 4]
        ).encode(y='y:Q')
        chart = (line + rule).properties(
            title=f"Évolution de {indicator_selected} pour '{champ_selectionne}'"
        )
    else:
        chart = line.properties(
            title=f"Évolution de {indicator_selected} pour '{champ_selectionne}'"
        )
    
    return chart


def create_percentage_bar_charts(df_counts_date, fct):
    """Crée les graphiques en barres de pourcentage"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Pourcentage de tests OK par période")
        chart1 = alt.Chart(df_counts_date).mark_bar().encode(
            x=alt.X("Date:T", axis=alt.Axis(format='%d-%m-%Y', labelAngle=-45)),
            y=alt.Y("percentage:Q", axis=alt.Axis(format='%')),
            color=alt.Color("OUTCOME:N", scale=alt.Scale(domain=[True, False], range=[COLORS["ok"], COLORS["ko"]])),
            tooltip=[alt.Tooltip("Date:T", format='%d-%m-%Y'), "OUTCOME", alt.Tooltip("percentage:Q", format=".1%")]
        )
        st.altair_chart(chart1, use_container_width=True)
    
    with col2:
        st.subheader("Pourcentage de tests OK par Table ref")
        chart2 = alt.Chart(fct).mark_bar().encode(
            x="TABLE_NAME:N",
            y=alt.Y("percentage:Q", axis=alt.Axis(format='%')),
            color=alt.Color("OUTCOME:N", scale=alt.Scale(domain=[True, False], range=[COLORS["ok"], COLORS["ko"]])),
            tooltip=["TABLE_NAME", "OUTCOME", alt.Tooltip("percentage:Q", format=".1%")]
        )
        st.altair_chart(chart2, use_container_width=True)


def create_heatmap(df_full, all_p):
    """Crée la carte de chaleur"""
    st.subheader("Carte de chaleur : Nombre de tests OK par période et indicateur")
    chart = alt.Chart(df_full).mark_rect().encode(
        x=alt.X("Periode:O", title="Période", sort=all_p),
        y=alt.Y("Indicateur:N", title="Indicateur"),
        color=alt.Color("Tests_OK:Q", scale=alt.Scale(scheme="greenblue")),
        tooltip=["Periode", "Indicateur", "Tests_OK"]
    )
    st.altair_chart(chart, use_container_width=True)