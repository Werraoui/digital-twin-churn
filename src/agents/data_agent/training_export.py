# à ajouter, ex. dans un nouveau data_agent/training_export.py
def get_labeled_training_table() -> pd.DataFrame:
    """Retourne Telco nettoyé AVEC Churn, réservé à l'entraînement — jamais utilisé
    par le Persona ni exposé aux autres agents."""
    return clean_telco(load_telco())