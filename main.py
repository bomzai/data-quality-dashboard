import streamlit as st
import pandas as pd
import matplotlib
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from snowflake.snowpark.context import get_active_session

# Configuration pour utiliser toute la largeur
st.set_page_config(layout="wide")

st.title("Data Quality Dashboards")
st.write("""
Ceci est **un exemple** de visualisations pour illustrer la qualité des données.
""")

SCHEMA = "DEV_RESULTS.SODA_SCAN_RESULTS"

# --- Chargement des données depuis Snowflake ---
session = get_active_session()
snowpark_df = session.table(SCHEMA)
df = snowpark_df.to_pandas()

tz = df['SCAN_TIMESTAMP'].dt.tz
df["SCAN_TIMESTAMP"] = pd.to_datetime(df["SCAN_TIMESTAMP"]).dt.tz_convert('Europe/Paris')
min_datetime = df["SCAN_TIMESTAMP"].min().normalize()
max_datetime = df["SCAN_TIMESTAMP"].max().normalize()
min_date = min_datetime.date()
max_date = max_datetime.date()
df["Indicateur"] = df['CHECK_NAME'].str.split('-').str[0]
df["Test_booleen"] = 1
df["Référentiel"] = "Produit"
df["Résultat"] = df["VALUE"]

df["Score"] = (df["Résultat"] == 0).mean() * 100


# --- Score global pondéré ---
# Calcul sur la dernière date disponible
timestamp_latest = df["SCAN_TIMESTAMP"].max().normalize()
df_latest = df[df["SCAN_TIMESTAMP"].dt.normalize() == timestamp_latest]

# Liste des indicateurs et poids modifiables
all_indicators = sorted(df_latest["Indicateur"].unique())
poids_indicateurs = {}

def interpret_score(data):
    good_data_quality = data.loc[data["Résultat"] == 0]
    good_data_quality_columns = good_data_quality['COLUMN_NAME'].unique()
    bad_data_quality_columns = list(set(data['COLUMN_NAME'].unique() ) - set(good_data_quality_columns))
    result = (len(good_data_quality_columns) / len(data['COLUMN_NAME'].unique())) * 100
    return result


# Calcul des scores par granularité
def calculer_score_temporel(df_group):
    total, poids_total = 0, 0
    for indic in all_indicators:
        df_ind = df_group[df_group["Indicateur"] == indic]
        if df_ind.empty:
            continue
        poids = poids_indicateurs.get(indic, 1.0)
        #score = pd.to_numeric(df_ind["Résultat"], errors="coerce").mean()
        score = interpret_score(df_ind)
        total += poids * score
        poids_total += poids
    return total / poids_total if poids_total > 0 else None

# Ajustement des pondérations dans une zone masquée par défaut
with st.sidebar:
    st.subheader("Pondérations des indicateurs")
    for indic in all_indicators:
        poids_indicateurs[indic] = st.number_input(
            f"Poids pour '{indic}'", min_value=0.0, value=1.0, step=0.1
        )
    st.subheader("Seuil pour l'évolutiuon Score global dans le temps : ")
    seuil = st.slider("Seuil du score global (%)", min_value=0, max_value=100, value=50)


score_final = calculer_score_temporel(df)

# Détermination de la couleur
if score_final < 50:
    color = "#e74c3c"
elif score_final < 70:
    color = "#f39c12"
else:
    color = "#2ecc71"


# --- Filtres sur la même ligne ---
col1, col2 = st.columns([1, 1])
with col1:
    date_range = st.date_input(
        "Intervalle de temps",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        # 5. Convertir en datetime avec timezone
        start_datetime = pd.Timestamp(start_date).tz_localize(tz)
        end_datetime = pd.Timestamp(end_date).tz_localize(tz) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    else:
        st.warning("Veuillez sélectionner une plage de dates.")

with col2:
    # Choix de la granularité temporelle
    granularite = st.radio("Granularité temporelle :", ["Jour", "Semaine", "Mois", "Trimestre"], horizontal=True)

def appliquer_granularite(df, colonne="SCAN_TIMESTAMP"):
    if granularite == "Jour":
        return df[colonne].dt.to_period("D").dt.to_timestamp()
    elif granularite == "Semaine":
        return df[colonne].dt.to_period("W").dt.start_time
    elif granularite == "Mois":
        return df[colonne].dt.to_period("M").dt.to_timestamp()
    elif granularite == "Trimestre":
        trimestre = df[colonne].dt.to_period("Q").dt.start_time
        return pd.to_datetime(trimestre)


# --- Application du filtre de temps global au DataFrame ---
df = df[(df["SCAN_TIMESTAMP"].dt.date >= min_date) & (df["SCAN_TIMESTAMP"].dt.date <= max_date)]

# --- Évolution du score global dans le temps ---
df_filtered = df[df["Indicateur"].isin(all_indicators)]
df_filtered["Granularité"] = appliquer_granularite(df_filtered)

df_scores = df_filtered.groupby("Granularité").apply(calculer_score_temporel).reset_index(name="Score global")

# Affichage de la carte du score global avec bouton d'infos (via st.markdown et JS)
with st.container():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
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
        
# Affichage du line chart
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

(line_chart+seuil_line).properties(
    title="Évolution du score global dans le temps",
    width="container",
    height=300
)

st.altair_chart((line_chart+seuil_line), use_container_width=True)

# Filtrage du DataFrame selon l’intervalle de dates
df_with_interval = df[(df["SCAN_TIMESTAMP"] >= start_datetime) & (df["SCAN_TIMESTAMP"] <= end_datetime)]

# Filtrer les tests booléens uniquement (puisqu'on s'intéresse à OK/KO)
df_bool_ko = df_with_interval[
    df_with_interval['Résultat'].isin([0, 1])
]

# Ne garder que les tests KO (Résultat == 0)
df_ko_only = df_bool_ko[df_bool_ko['Résultat'] == 0]

# Compter les KO par Référentiel / Table / Champ
df_ko_counts = df_ko_only.groupby(['Référentiel', 'TABLE_NAME', 'COLUMN_NAME']).size().reset_index(name='Tests KO')

# Si aucun KO, ajouter une ligne factice pour éviter une erreur Plotly
if df_ko_counts.empty:
    df_ko_counts = pd.DataFrame({
        'Référentiel': ['Aucun KO'],
        'Table ref': ['Aucune Table'],
        'Champ': ['Aucun Champ'],
        'Tests KO': [1]
    })

# Treemap Plotly
#fig = px.treemap(
#    df_ko_counts,
#    path=['Référentiel', 'TABLE_NAME', 'COLUMN_NAME'],
#    values='Tests KO',
#    color='Tests KO',
#    color_continuous_scale='Reds',
#)
#st.plotly_chart(fig, use_container_width=True)

#Visualisations Antoine pour remplacer les treemap

# 1. Sélection du référentiel
referentiels = df['Référentiel'].dropna().unique()
selected_referentiel = st.selectbox("Sélectionnez le référentiel", referentiels)

# Filtrer le DataFrame sur le référentiel sélectionné
df_ref = df_with_interval[df_with_interval['Référentiel'] == selected_referentiel]


with st.container():
    col1, col2 = st.columns([1, 2])
    indicateurs = df_ref['Indicateur'].unique()
    scores = {}
    global_score = 0
    for i in indicateurs:
        data = df_ref.loc[df_ref["Indicateur"] == i]
        score = interpret_score(data)
        scores[i] = score
        global_score += score
    global_score = global_score / len(indicateurs)
    
    with col1:
        # 1.1 Donut Global (tous indicateurs confondus)
        st.markdown("### QDD global")
 
        tests_ko_global = 100 - global_score       
        taux_ok_global = global_score
        taux_ko_global = 100 - taux_ok_global
        
        fig_global = go.Figure(data=[go.Pie(
            labels=["OK", "KO"],
            values=[taux_ok_global, taux_ko_global],
            hole=0.7,
            marker_colors=["green", "red"],
            textinfo='percent'
        )])
        fig_global.update_layout(
            showlegend=True,
            annotations=[dict(
                text=str(round(taux_ok_global,2))+"%",
                x=0.5, y=0.5,
                font=dict(size=37, family="Arial Black", color="grey"),
                showarrow=False,
                align='center'
            )],
            title={'text': "Global", 'x': 0.5, 'xanchor': 'center'},
            margin=dict(t=30, b=30, l=0, r=0),
            height=300,
            width=350
        )
        
        st.plotly_chart(fig_global)

    with col2:
        # 2. Donut Charts par indicateur
        st.markdown("### Taux de réussite par indicateur")

        for i in range(0, len(indicateurs), 3):
            row_cols = st.columns(3)
            for j in range(3):
                if i + j < len(indicateurs):
                    indicateur = indicateurs[i + j]
                    df_indic = df_ref[df_ref['Indicateur'] == indicateur]
                    taux_ok = scores[indicateur]
                    taux_ko = 100 - taux_ok
                
                    fig = go.Figure(data=[go.Pie(
                        labels=["OK", "KO"],
                        values=[taux_ok, taux_ko],
                        hole=0.7,
                        marker_colors=["green", "red"],
                        textinfo='percent'
                    )])
                    fig.update_layout(
                        showlegend=False,
                        title={'text': indicateur, 'x': 0.5, 'xanchor': 'center'},
                        annotations=[dict(
                            text=str(round(taux_ok,2))+"%",
                            x=0.5, y=0.5,
                            font=dict(size=14, family="Arial Black", color="grey"),
                            showarrow=False,
                            align='center'
                        )],
                        margin=dict(t=30, b=30, l=0, r=0),
                        height=150,
                        width=250
                    )
                    with row_cols[j]:
                        st.plotly_chart(fig)


###Dataframe croisé dynamique

# Fonction de style dégradé rouge -> vert
def gradient_color(val):
    try:
        val = float(val)
        if val <= 50:
            # Dégradé rouge (0–50): rouge pur → rouge clair
            r = 255
            g = int((val / 50) * 50)  # 0 → 50
            b = 0
        elif val <= 60:
            # Orange progressif (50–60): rouge-orange
            r = 255
            g = int(50 + (val - 50) * 11.5)  # 50 → 165
            b = 0
        else:
            # Vert progressif (60–100): orange → vert
            ratio = (val - 60) / 40  # 0 → 1
            r = int(255 * (1 - ratio))       # 255 → 0
            g = int(165 + (90 * ratio))      # 165 → 255
            b = int(0 + (90 * ratio))        # 0 → 90 (léger bleu pour contraste)
        return f'background-color: rgb({r}, {g}, {b}); color: black'
    except:
        return ''
# Calcul du taux de réussite par Table et Indicateur
# 2e visualisation : DataFrame Table vs Indicateurs avec taux de réussite + Globalité réelle (OK==True)
# Filtrage des données sur le référentiel choisi
filtered_df = df_with_interval[df_with_interval["Référentiel"] == selected_referentiel]
# Calcul du taux de réussite par Table ref et Indicateur de qualité
#pivot_table = filtered_df.groupby(["TABLE_NAME", "Indicateur"])["Résultat"].mean().unstack()
pivot_table = (
    filtered_df
    .groupby(["TABLE_NAME", "Indicateur"])
    .apply(interpret_score)
    .unstack()
)

# Calcul de la Globalité : taux global de tests OK==True pour chaque Table ref
#globalite_table = filtered_df.groupby("TABLE_NAME")["Résultat"].mean()
globalite_table = (
    filtered_df
    .groupby(["TABLE_NAME", "Indicateur"])
    .apply(interpret_score)
)
# Ajout de la colonne Globalité dans le pivot
pivot_table["Globalité"] = globalite_table
st.subheader(f"Taux de réussite par table pour le référentiel : {selected_referentiel}")
styled_df = pivot_table.round(2).style.format("{:.2f}%").applymap(gradient_color)
st.dataframe(styled_df, use_container_width=True)

# 3e visualisation : DataFrame Champ vs Indicateurs pour une Table sélectionnée + Globalité réelle (OK==True)
# Filtre sur la table
selected_table = st.selectbox("Sélectionner une table", filtered_df["TABLE_NAME"].unique())
# Filtrage sur la table sélectionnée
filtered_table_df = filtered_df[filtered_df["TABLE_NAME"] == selected_table]
# Calcul du taux de réussite par Champ et Indicateur de qualité
#pivot_champ = filtered_table_df.groupby(["COLUMN_NAME", "Indicateur"])["Résultat"].mean().unstack()
pivot_champ = (
    filtered_table_df
    .groupby(["COLUMN_NAME", "Indicateur"])
    .apply(interpret_score)
    .unstack()
)
# Calcul de la Globalité : taux global de tests OK==True pour chaque Champ
#globalite_champ = filtered_table_df.groupby("COLUMN_NAME")["Résultat"].mean()
globalite_champ = (
    filtered_table_df
    .groupby(["COLUMN_NAME", "Indicateur"])
    .apply(interpret_score)
)
# Ajout de la colonne Globalité dans le pivot
pivot_champ["Globalité"] = globalite_champ
# Affichage
st.subheader(f"Taux de réussite par champ pour la table : {selected_table}")
styled_df = pivot_champ.round(2).style.format("{:.2f}%").applymap(gradient_color)
st.dataframe(styled_df, use_container_width=True)

# --- Filtres sur la même ligne ---
col1, col2 = st.columns([1, 1])
with col1:
    # Création du filtre Champ avec affichage "Référentiel - Table ref - Champ"
    df['Champ Full'] = df['COLUMN_NAME'] + ' - ' + df['TABLE_NAME'] + ' - ' +  df['Référentiel']
    unique_champs = df['Champ Full'].unique()
    champ = st.selectbox("Sélectionner un champ", unique_champs)
    
    # Extraire les composantes pour filtrer ensuite
    champ_selectionne, selected_table, selected_ref = champ.split(' - ')
with col2:
    indicateurs_disponibles = df["Indicateur"].unique().tolist()
    indicator_selected = st.radio(
        "Choisissez un indicateur :",
        indicateurs_disponibles,
        horizontal=True
    )
# --- Application du filtre de temps global au DataFrame ---
df = df[(df["SCAN_TIMESTAMP"].dt.date >= min_date) & (df["SCAN_TIMESTAMP"].dt.date <= max_date)]

# --- Scatter / Line selon indicateur ---
st.subheader("Évolution par indicateur")
df_filtered = df[
    (df["COLUMN_NAME"] == champ_selectionne) &
    (df["Indicateur"] == indicator_selected)
]
if df_filtered.empty:
    st.warning("Aucune donnée disponible pour l’indicateur sélectionné.")
else:
    df_filtered["Date"] = appliquer_granularite(df_filtered)
    df_filtered["Résultat"] = pd.to_numeric(df_filtered["Résultat"], errors="coerce")
    df_filtered = df_filtered.groupby("Date", as_index=False)["Résultat"].mean()
    latest_value = df_filtered[df_filtered["Date"].dt.date == max_date]["Résultat"].mean()
    st.markdown(f"**Valeur de l’indicateur le {max_date.strftime('%d-%m-%Y')} :** {latest_value:.2f}")
    line = alt.Chart(df_filtered).mark_line(point=True).encode(
        x=alt.X("Date:T", title="Date", axis=alt.Axis(format='%d-%m-%Y', labelAngle=-45)),
        y=alt.Y("Résultat:Q", title="Résultat du test"),
        tooltip=[alt.Tooltip("Date:T", format='%d-%m-%Y'), "Résultat"]
    )
    boolean_indicators = ["Traçabilité", "Pertinence", "Cohérence", "Intégrité"]
    if indicator_selected not in boolean_indicators:
        rule = alt.Chart(pd.DataFrame({'y':[seuil]})).mark_rule(color='red', strokeDash=[4,4]).encode(y='y:Q')
        st.altair_chart((line+rule).properties(
            title=f"Évolution de {indicator_selected} pour '{champ_selectionne}'"
        ), use_container_width=True)
    else:
        st.altair_chart(line.properties(
            title=f"Évolution de {indicator_selected} pour '{champ_selectionne}'"
        ), use_container_width=True)


# --- Bar charts pourcentage ---
_df_bool = df.copy()
_df_bool["Date"] = appliquer_granularite(_df_bool)
df_counts_date = _df_bool.groupby(["Date","OUTCOME"]).size().reset_index(name="counts")
df_counts_date["percentage"] = df_counts_date.groupby("Date")["counts"].transform(lambda x: x/x.sum())

_df_table = df.copy()
fct = _df_table.groupby(["TABLE_NAME","OUTCOME"]).size().reset_index(name="counts")
fct["percentage"] = fct.groupby("TABLE_NAME")["counts"].transform(lambda x: x/x.sum())

col1, col2 = st.columns(2)
with col1:
    st.subheader("Pourcentage de tests OK par période")
    st.altair_chart(alt.Chart(df_counts_date).mark_bar().encode(
        x=alt.X("Date:T", axis=alt.Axis(format='%d-%m-%Y', labelAngle=-45)),
        y=alt.Y("percentage:Q", axis=alt.Axis(format='%')),
        color=alt.Color("OUTCOME:N", scale=alt.Scale(domain=[True,False], range=["#2ca02c","#d62728"])),
        tooltip=[alt.Tooltip("Date:T", format='%d-%m-%Y'), "OUTCOME", alt.Tooltip("percentage:Q", format=".1%")]
    ), use_container_width=True)
with col2:
    st.subheader("Pourcentage de tests OK par Table ref")
    st.altair_chart(alt.Chart(fct).mark_bar().encode(
        x="TABLE_NAME:N",
        y=alt.Y("percentage:Q", axis=alt.Axis(format='%')),
        color=alt.Color("OK:N", scale=alt.Scale(domain=[True,False], range=["#2ca02c","#d62728"])),
        tooltip=["TABLE_NAME","OUTCOME", alt.Tooltip("percentage:Q", format=".1%")]
    ), use_container_width=True)


# --- Heatmap des tests OK par jour, semaine ou mois ---
st.subheader("Carte de chaleur : Nombre de tests OK par période et indicateur")
df_hm = df.copy()
df_hm["Periode"] = appliquer_granularite(df_hm)
df_hm["Periode"] = pd.to_datetime(df_hm["Periode"]).dt.strftime('%d-%m-%Y')
df_ok = df_hm[df_hm["OUTCOME"] == "pass"]
all_p = sorted(df_hm["Periode"].unique(), key=lambda x: pd.to_datetime(x, format='%d-%m-%Y'))
df_grp = df_ok.groupby(["Periode","Indicateur"]).size().reset_index(name="Tests_OK")
_df_full = pd.DataFrame(index=pd.MultiIndex.from_product([all_p, df_ok["Indicateur"].unique()], names=["Periode","Indicateur"]))
df_full = (_df_full.reset_index().merge(df_grp, on=["Periode","Indicateur"], how="left").fillna(0))
df_full["Tests_OK"] = df_full["Tests_OK"].astype(int)
st.altair_chart(alt.Chart(df_full).mark_rect().encode(
    x=alt.X("Periode:O", title="Période", sort=all_p),
    y=alt.Y("Indicateur:N", title="Indicateur"),
    color=alt.Color("Tests_OK:Q", scale=alt.Scale(scheme="greenblue")),
    tooltip=["Periode","Indicateur","Tests_OK"]
), use_container_width=True)