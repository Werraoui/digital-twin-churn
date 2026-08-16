"""Feature engineering pour l'Agent Prédiction."""
import pandas as pd


def build_features(persona_df: pd.DataFrame) -> pd.DataFrame:
    """Transforme les données du Persona en variables prédictives.

    TODO : ancienneté, ratio dépense trimestre courant/précédent, encodage du contrat, etc.
    """
    raise NotImplementedError
