import pandas as pd
from snowflake.snowpark.context import get_active_session
from config import SCHEMA, DEFAULT_CONFIG,LOCAL, connect_to_snowflake
import streamlit as st  


def load_data_from_snowflake():
    """Charge les données depuis Snowflake et effectue les transformations de base"""
    if LOCAL:
        conn = connect_to_snowflake()
        cur = conn.cursor()
        query = f"SELECT * FROM {SCHEMA}"
        cur.execute(query)
        results = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(results, columns=columns)
    else:
        session = get_active_session()
        snowpark_df = session.table(SCHEMA)
        df = snowpark_df.to_pandas()
    
    # Transformations de base
    tz = df['SCAN_TIMESTAMP'].dt.tz
    df["SCAN_TIMESTAMP"] = pd.to_datetime(df["SCAN_TIMESTAMP"]).dt.tz_convert(DEFAULT_CONFIG["timezone"])
    df["Indicateur"] = df['CHECK_NAME'].str.split('-').str[0]
    df["Test_booleen"] = 1
    df["Référentiel"] = "Produit"
    df["Résultat"] = df["VALUE"]
    df["Score"] = (df["Résultat"] == 0).mean() * 100
    
    return df, tz


def get_date_range(df):
    """Retourne les dates min et max du DataFrame"""
    min_datetime = df["SCAN_TIMESTAMP"].min().normalize()
    max_datetime = df["SCAN_TIMESTAMP"].max().normalize()
    min_date = min_datetime.date()
    max_date = max_datetime.date()
    return min_date, max_date


# def apply_granularity(df, granularite, colonne="SCAN_TIMESTAMP"):
#     """Applique la granularité temporelle spécifiée"""
#     if granularite == "Jour":
#         return df[colonne].dt.to_period("D").dt.to_timestamp()
#     elif granularite == "Semaine":
#         return df[colonne].dt.to_period("W").dt.start_time
#     elif granularite == "Mois":
#         return df[colonne].dt.to_period("M").dt.to_timestamp()
#     elif granularite == "Trimestre":
#         trimestre = df[colonne].dt.to_period("Q").dt.start_time
#         return pd.to_datetime(trimestre)



def apply_granularity(df, granularite, colonne="SCAN_TIMESTAMP"):
    """Applique la granularité temporelle spécifiée à une colonne datetime"""
    if not pd.api.types.is_datetime64_any_dtype(df[colonne]):
        df[colonne] = pd.to_datetime(df[colonne])

    if granularite == "Jour":
        return df[colonne].dt.to_period("D").dt.to_timestamp()
    elif granularite == "Semaine":
        test = df[colonne].dt.to_period("W").dt.start_time
        st.dataframe(test) 
        return test
    elif granularite == "Mois":
        return df[colonne].dt.to_period("M").dt.to_timestamp()
    elif granularite == "Trimestre":
        return df[colonne].dt.to_period("Q").dt.start_time
    else:
        raise ValueError(f"Granularité non supportée : {granularite}")


def interpret_score(data):
    """Interprète le score de qualité des données"""
    good_data_quality = data.loc[data["Résultat"] == 0]
    good_data_quality_columns = good_data_quality['COLUMN_NAME'].unique()
    bad_data_quality_columns = list(set(data['COLUMN_NAME'].unique()) - set(good_data_quality_columns))
    result = (len(good_data_quality_columns) / len(data['COLUMN_NAME'].unique())) * 100
    return result


def calculate_temporal_score(df_group, all_indicators, poids_indicateurs):
    """Calcule le score temporel pondéré"""
    total, poids_total = 0, 0
    for indic in all_indicators:
        df_ind = df_group[df_group["Indicateur"] == indic]
        if df_ind.empty:
            continue
        poids = poids_indicateurs.get(indic, 1.0)
        score = interpret_score(df_ind)
        total += poids * score
        poids_total += poids
    return total / poids_total if poids_total > 0 else None


def create_pivot_table(filtered_df, group_cols):
    """Crée un tableau croisé dynamique avec les taux de réussite"""
    pivot_table = (
        filtered_df
        .groupby(group_cols)
        .apply(interpret_score)
        .unstack()
    )
    
    pivot_table["Globalité"] = pivot_table.mean(axis=1)
    return pivot_table