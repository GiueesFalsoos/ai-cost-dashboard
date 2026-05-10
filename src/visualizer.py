import plotly.express as px
import pandas as pd
from src.analyzer import total_credits_by_model, total_credits_by_day


def plot_credits_by_model(df: pd.DataFrame) -> None:
    """
    Grafico a barre: crediti totali per modello AI.
    """
    data = total_credits_by_model(df)
    
    fig = px.bar(
        data,
        x="model",
        y="total_credits",
        title="💰 Crediti Consumati per Modello AI",
        color="model",
        labels={"total_credits": "Crediti Totali", "model": "Modello"},
        text="total_credits"
    )
    fig.show()


def plot_credits_by_day(df: pd.DataFrame) -> None:
    """
    Grafico a linea: andamento crediti nel tempo.
    """
    data = total_credits_by_day(df)
    
    fig = px.line(
        data,
        x="date",
        y="total_credits",
        title="📈 Andamento Costi AI nel Tempo",
        labels={"total_credits": "Crediti Totali", "date": "Data"},
        markers=True
    )
    fig.show()