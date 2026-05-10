import pandas as pd

def total_credits_by_model(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola il totale dei crediti consumati per ogni modello AI.
    """
    result = df.groupby("model")["credits"].sum().reset_index()
    result.columns = ["model", "total_credits"]
    result = result.sort_values("total_credits", ascending=False)
    return result


def total_credits_by_day(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola il totale dei crediti consumati per ogni giorno.
    """
    result = df.groupby("date")["credits"].sum().reset_index()
    result.columns = ["date", "total_credits"]
    return result


def summary(df: pd.DataFrame) -> None:
    """
    Stampa un riepilogo generale dei dati.
    """
    print("\n===== 📊 RIEPILOGO COSTI AI =====")
    print(f"Totale crediti consumati : {df['credits'].sum()}")
    print(f"Media crediti per run    : {df['credits'].mean():.1f}")
    print(f"Picco massimo            : {df['credits'].max()} ({df.loc[df['credits'].idxmax(), 'model']})")
    print(f"Periodo analizzato       : {df['date'].min()} → {df['date'].max()}")
    
    print("\n--- Crediti per Modello ---")
    print(total_credits_by_model(df).to_string(index=False))
    
    print("\n--- Crediti per Giorno ---")
    print(total_credits_by_day(df).to_string(index=False))