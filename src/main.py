from src.parser import load_csv, preview

# Percorso del file CSV di test
filepath = "data/sample.csv"

# Carica i dati
df = load_csv(filepath)

# Mostra anteprima
preview(df)