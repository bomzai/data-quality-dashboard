import snowflake.connector
import yaml
import pandas as pd
import streamlit as st
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

LOCAL = True

# Configuration Snowflake
SCHEMA = "DEV_RESULTS.SODA_SCAN_RESULTS"

# Configuration des couleurs
COLORS = {
    "success": "#2ecc71",
    "warning": "#f39c12",
    "danger": "#e74c3c",
    "ok": "#2ca02c",
    "ko": "#d62728"
}

# Seuils de qualité
THRESHOLDS = {
    "good": 70,
    "warning": 50
}

# Configuration des indicateurs booléens
BOOLEAN_INDICATORS = ["Traçabilité", "Pertinence", "Cohérence", "Intégrité"]

# Configuration par défaut
DEFAULT_CONFIG = {
    "layout": "wide",
    "timezone": "Europe/Paris"
}

def connect_to_snowflake():
    # Chargement de la config YAML
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    sf = config["snowflake"]

    # Chargement de la clé privée
    try:
        with open(sf["private_key_path"], "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=sf["private_key_passphrase"].encode() if sf["private_key_passphrase"] else None,
                backend=default_backend()
            )
    except Exception as e:
        st.error(f"Erreur lors du chargement de la clé privée : {e}")
        st.stop()

    # Conversion au format DER
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Connexion à Snowflake
    try:
        conn = snowflake.connector.connect(
            user=sf["user"],
            account=sf["account"],
            private_key=private_key_bytes,
            warehouse=sf["warehouse"],
            database=sf["database"],
            schema=sf["schema"],
            role=sf["role"]
        )
        st.success("✅ Connexion à Snowflake réussie")
    except Exception as e:
        st.error(f"❌ Connexion à Snowflake échouée : {e}")
        st.stop()

    # Exemple de requête
    query = f"SELECT * FROM {SCHEMA}"

    return conn
        
    # Exécution manuelle
    cur = conn.cursor()
    try:
        cur.execute(query)
        results = cur.fetchall()
        #st.success("✅ Requête exécutée avec succès")
        #st.success(results)
        columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(results, columns=columns)
        st.dataframe(df)
    finally:
        cur.close()