import pandas as pd
import os

def load_csv(filepath: str) -> pd.DataFrame:
    """
    Carica un file CSV e restituisce un DataFrame pandas.
    
    Args:
        filepath: percorso del file CSV
    
    Returns:
        DataFrame con i dati caricati
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File non trovato: {filepath}")
    
    df = pd.read_csv(filepath)
    print(f"✅ File caricato: {filepath}")
    print(f"📊 Righe: {len(df)} | Colonne: {list(df.columns)}")
    return df


def preview(df: pd.DataFrame, rows: int = 5) -> None:
    """
    Mostra un'anteprima del DataFrame.
    """
    print("\n--- ANTEPRIMA DATI ---")
    print(df.head(rows))
    print(f"\nTipi di dati:")
    print(df.dtypes)