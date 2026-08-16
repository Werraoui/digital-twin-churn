"""Exemple de DAG Airflow automatisant une étape du pipeline (semaine 5 du planning).

À placer dans le dossier dags/ de ton installation Airflow locale pour le tester.
"""
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator


def refresh_vectorstore():
    """Ré-indexe le corpus RAG (à appeler périodiquement si le corpus évolue)."""
    from src.agents.generator_agent.vectorstore import index_documents
    # TODO : recharger les nouveaux tickets et les indexer.
    pass


with DAG(
    dag_id="refresh_rag_vectorstore",
    start_date=datetime(2026, 1, 1),
    schedule="@weekly",
    catchup=False,
) as dag:
    refresh_task = PythonOperator(
        task_id="refresh_vectorstore",
        python_callable=refresh_vectorstore,
    )
