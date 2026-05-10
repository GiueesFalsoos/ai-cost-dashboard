from src.parser import load_csv, preview
from src.analyzer import summary
from src.visualizer import plot_credits_by_model, plot_credits_by_day

# Carica i dati
df = load_csv("data/sample.csv")

# Anteprima
preview(df)

# Analisi
summary(df)

# Grafici
plot_credits_by_model(df)
plot_credits_by_day(df)