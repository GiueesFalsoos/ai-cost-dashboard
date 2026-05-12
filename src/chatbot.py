"""
Chatbot su telemetria CSV: domande in linguaggio naturale (italiano) su crediti e consumi,
con filtri per intervallo date e modello.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Optional

import pandas as pd
from dateutil import parser as date_parser

from src.analyzer import total_credits_by_day, total_credits_by_model
from src.parser import load_csv

REQUIRED_COLUMNS = ("date", "model", "credits")


@dataclass
class ParsedQuery:
    """Parametri estratti dalla domanda."""

    date_from: Optional[date] = None
    date_to: Optional[date] = None
    models: Optional[list[str]] = None  # None = tutti i modelli presenti nei dati
    agg: str = "sum"  # sum | mean | max | min | count | by_day | by_model


def _parse_single_date(token: str) -> date:
    token = token.strip()
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", token):
        return datetime.strptime(token, "%Y-%m-%d").date()
    dt = date_parser.parse(token, dayfirst=True)
    return dt.date()


def _extract_iso_dates(text: str) -> list[date]:
    found: list[date] = []
    for m in re.finditer(r"\b\d{4}-\d{1,2}-\d{1,2}\b", text):
        found.append(_parse_single_date(m.group(0)))
    return found


def _extract_slash_dates(text: str) -> list[date]:
    found: list[date] = []
    for m in re.finditer(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", text):
        found.append(_parse_single_date(m.group(0)))
    return found


def _extract_dates(text: str) -> list[date]:
    dates = _extract_iso_dates(text) + _extract_slash_dates(text)
    # dedup preserving order
    seen: set[date] = set()
    out: list[date] = []
    for d in dates:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _dal_al_dates(lower: str) -> tuple[Optional[date], Optional[date]]:
    d_from: Optional[date] = None
    d_to: Optional[date] = None
    m1 = re.search(
        r"\bdal\s+(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        lower,
    )
    m2 = re.search(
        r"\bal\s+(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        lower,
    )
    if m1:
        d_from = _parse_single_date(m1.group(1))
    if m2:
        d_to = _parse_single_date(m2.group(1))
    return d_from, d_to


def _infer_models_in_text(text_lower: str, known_models: list[str]) -> Optional[list[str]]:
    hits: list[str] = []
    for m in sorted(known_models, key=len, reverse=True):
        if m.lower() in text_lower:
            hits.append(m)
    if not hits:
        return None
    return hits


def _detect_agg(lower: str) -> str:
    if re.search(
        r"\b(per giorno|giorno per giorno|ogni giorno|distribuzione giornaliera)\b",
        lower,
    ):
        return "by_day"
    if re.search(r"\b(per modello|ogni modello|suddivisi per modello)\b", lower):
        return "by_model"
    if re.search(r"\b(media|medio|medie)\b", lower):
        return "mean"
    if re.search(r"\b(massimo|massima|picco|max)\b", lower):
        return "max"
    if re.search(r"\b(minimo|minima|min)\b", lower):
        return "min"
    if re.search(
        r"\b(quante righe|quanti eventi|conteggio|quante chiamate|quanti run)\b",
        lower,
    ):
        return "count"
    return "sum"


def parse_natural_language(question: str, known_models: list[str]) -> ParsedQuery:
    lower = question.lower().strip()
    pq = ParsedQuery(agg=_detect_agg(lower))

    d_from, d_to = _dal_al_dates(lower)
    all_dates = _extract_dates(question)

    if d_from is not None or d_to is not None:
        pq.date_from = d_from
        pq.date_to = d_to
        if pq.date_from and pq.date_to and pq.date_from > pq.date_to:
            pq.date_from, pq.date_to = pq.date_to, pq.date_from
    elif len(all_dates) >= 2:
        pq.date_from, pq.date_to = min(all_dates[:2]), max(all_dates[:2])
    elif len(all_dates) == 1:
        if re.search(r"\b(dal|dopo|da)\b", lower):
            pq.date_from = all_dates[0]
        elif re.search(r"\b(al|fino|entro)\b", lower):
            pq.date_to = all_dates[0]
        else:
            pq.date_from = pq.date_to = all_dates[0]

    pq.models = _infer_models_in_text(lower, known_models)
    return pq


def prepare_telemetry(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Colonne mancanti nel CSV: {missing}. Richieste: {REQUIRED_COLUMNS}")
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.normalize()
    out["credits"] = pd.to_numeric(out["credits"], errors="coerce")
    out = out.dropna(subset=["date", "credits", "model"])
    if out.empty:
        raise ValueError("Nessuna riga valida dopo la normalizzazione di date e crediti.")
    return out


def apply_filters(
    df: pd.DataFrame,
    date_from: Optional[date],
    date_to: Optional[date],
    models: Optional[list[str]],
) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if date_from is not None:
        mask &= df["date"].dt.date >= date_from
    if date_to is not None:
        mask &= df["date"].dt.date <= date_to
    if models:
        mask &= df["model"].isin(models)
    return df.loc[mask].copy()


def _fmt_filters(pq: ParsedQuery) -> str:
    parts: list[str] = []
    if pq.date_from and pq.date_to and pq.date_from == pq.date_to:
        parts.append(f"data {pq.date_from.isoformat()}")
    else:
        if pq.date_from:
            parts.append(f"dal {pq.date_from.isoformat()}")
        if pq.date_to:
            parts.append(f"al {pq.date_to.isoformat()}")
    if pq.models:
        parts.append("modelli: " + ", ".join(pq.models))
    return "; ".join(parts) if parts else "nessun filtro (tutto il dataset)"


def answer_question(df: pd.DataFrame, question: str) -> str:
    df = prepare_telemetry(df)
    models_known = sorted(df["model"].astype(str).unique().tolist())
    pq = parse_natural_language(question, models_known)
    filt = apply_filters(df, pq.date_from, pq.date_to, pq.models)
    filt_desc = _fmt_filters(pq)

    if filt.empty:
        return (
            f"Non ci sono righe che soddisfano i filtri ({filt_desc}). "
            f"Periodo disponibile nei dati: {df['date'].min().date()} → {df['date'].max().date()}. "
            f"Modelli: {', '.join(models_known)}."
        )

    n = len(filt)
    credits = filt["credits"]

    if pq.agg == "by_day":
        sub = total_credits_by_day(filt)
        lines = []
        for _, row in sub.iterrows():
            d = row["date"]
            d_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
            lines.append(f"{d_str} → {int(row['total_credits'])} crediti")
        body = "\n".join(lines) if lines else "(nessun dato)"
        return f"Filtri: {filt_desc}.\nCrediti per giorno ({n} righe):\n{body}"

    if pq.agg == "by_model":
        sub = total_credits_by_model(filt)
        lines = [f"{row['model']}: {int(row['total_credits'])} crediti" for _, row in sub.iterrows()]
        body = "\n".join(lines) if lines else "(nessun dato)"
        return f"Filtri: {filt_desc}.\nCrediti per modello ({n} righe):\n{body}"

    ops: dict[str, tuple[str, Callable[[pd.Series], float]]] = {
        "sum": ("Totale crediti", float(credits.sum())),
        "mean": ("Media crediti per riga", float(credits.mean())),
        "max": ("Valore massimo di crediti (singola riga)", float(credits.max())),
        "min": ("Valore minimo di crediti (singola riga)", float(credits.min())),
        "count": ("Numero di righe (eventi)", float(n)),
    }
    label, value = ops[pq.agg]
    if pq.agg == "count":
        msg = f"{label}: {int(value)}."
    else:
        msg = f"{label}: {value:.2f}."
    return f"Filtri: {filt_desc}.\n{msg} (su {n} righe filtrate.)"


def run_chat(csv_path: str) -> None:
    df = load_csv(csv_path)
    print(
        "Chatbot telemetria — chiedi in italiano su crediti/consumi.\n"
        "Esempi: 'Totale crediti dal 2024-01-01 al 2024-01-02 per GPT-5'; "
        "'Media crediti il 2024-01-03'; 'Crediti per giorno per GPT-4.1'.\n"
        "Comandi: esci | quit"
    )
    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ("esci", "quit", "exit", "q"):
            break
        try:
            print(answer_question(df, line))
        except Exception as e:  # noqa: BLE001 — REPL user-facing
            print(f"Errore: {e}", file=sys.stderr)


def main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Chatbot su CSV di telemetria (crediti, date, modello).")
    p.add_argument(
        "csv",
        nargs="?",
        default="data/sample.csv",
        help="Percorso al CSV (default: data/sample.csv)",
    )
    args = p.parse_args(argv)
    run_chat(args.csv)


if __name__ == "__main__":
    main()
