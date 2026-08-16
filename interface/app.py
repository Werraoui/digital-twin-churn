"""Point d'entrée de l'interface Streamlit — tableau de bord de gestion du churn."""
import streamlit as st

st.set_page_config(page_title="Digital Twin Churn", layout="wide")

st.title("Gestion dynamique de la satisfaction client")
st.caption("Digital Twin & Analyse Prédictive du Churn")

st.info(
    "Utilise le menu de gauche pour naviguer entre les pages : "
    "Clients à risque, Fiche client, Simulateur."
)

# TODO : charger la liste des clients depuis src/utils/db.py et afficher un aperçu global.
