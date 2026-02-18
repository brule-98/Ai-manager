import pandas as pd
import numpy as np
from services.data_utils import to_numeric, find_column


def filtra_per_sito(df_db: pd.DataFrame, sito: str) -> pd.DataFrame:
    """Filtra il DB per sito/stabilimento. Se 'Globale' restituisce tutto."""
    if not sito or sito == 'Globale':
        return df_db
    col_sito = find_column(df_db, ['Sito', 'sito', 'Stabilimento', 'stabilimento', 'Site', 'Plant'])
    if col_sito:
        return df_db[df_db[col_sito].astype(str) == sito].copy()
    return df_db


def applica_rettifiche(df_db, rettifiche: list, col_conto: str, col_saldo: str, col_data: str):
    if not rettifiche:
        return df_db
    rows = []
    for r in rettifiche:
        if not r.get('attiva', True):
            continue
        row = {c: None for c in df_db.columns}
        row[col_conto] = r.get('conto', '')
        row[col_saldo] = r.get('importo', 0)
        if col_data in df_db.columns:
            row[col_data] = r.get('data', '')
        row['_rettifica'] = True
        row['_desc_rettifica'] = r.get('descrizione', '')
        rows.append(row)
    if not rows:
        return df_db
    return pd.concat([df_db, pd.DataFrame(rows)], ignore_index=True)


def _applica_formule(pivot: pd.DataFrame, schema_config: dict) -> pd.DataFrame:
    """
    Applica eventuali formule custom definite nello schema.
    Una formula è una stringa tipo: "VOCE_A + VOCE_B - VOCE_C"
    """
    if not schema_config:
        return pivot

    for voce, cfg in schema_config.items():
        formula = cfg.get('formula', '')
        if not formula or not formula.strip():
            continue
        try:
            # Parse formula: supporta +, -, nomi voce
            import re
            tokens = re.split(r'([+\-])', formula.replace(' ', ''))
            result = pd.Series(0.0, index=pivot.columns)
            operatore = '+'
            for tok in tokens:
                tok = tok.strip()
                if tok == '+':
                    operatore = '+'
                elif tok == '-':
                    operatore = '-'
                elif tok in pivot.index:
                    if operatore == '+':
                        result = result + pivot.loc[tok]
                    else:
                        result = result - pivot.loc[tok]
            if voce not in pivot.index:
                pivot.loc[voce] = result
            else:
                pivot.loc[voce] = result
        except Exception:
            pass

    return pivot


def costruisci_ce_riclassificato(
    df_db: pd.DataFrame,
    df_piano: pd.DataFrame,
    df_ricl: pd.DataFrame,
    mapping: dict,
    schema_config: dict,
    rettifiche: list = None,
    sito: str = 'Globale'
) -> tuple:
    """
    Costruisce il CE riclassificato mensilizzato.
    Returns: (pivot_df, errore_str)
    """
    col_data    = find_column(df_db, ['Data', 'data', 'DATA', 'data_registrazione'])
    col_saldo   = find_column(df_db, ['Saldo', 'saldo', 'SALDO', 'Importo', 'importo', 'Valore'])
    col_conto_db = find_column(df_db, ['Conto', 'conto', 'CONTO', 'Codice Conto', 'codice_conto'])

    if not all([col_data, col_saldo, col_conto_db]):
        return None, "Colonne non trovate nel DB (servono: Data, Saldo, Conto)"

    db = filtra_per_sito(df_db.copy(), sito)

    if rettifiche:
        db = applica_rettifiche(db, rettifiche, col_conto_db, col_saldo, col_data)

    db['_saldo_num'] = to_numeric(db[col_saldo])
    db['_data_dt']   = pd.to_datetime(db[col_data], format='%d/%m/%Y', errors='coerce')
    db['_mese']      = db['_data_dt'].dt.to_period('M').astype(str)
    db['_anno']      = db['_data_dt'].dt.year
    db['_voce_ricl'] = db[col_conto_db].astype(str).map(mapping)

    db_mapped = db[db['_voce_ricl'].notna()].copy()
    if db_mapped.empty:
        return None, "Nessun conto mappato. Configura la mappatura nel Workspace."

    pivot = pd.pivot_table(
        db_mapped,
        values='_saldo_num',
        index='_voce_ricl',
        columns='_mese',
        aggfunc='sum',
        fill_value=0
    )

    try:
        pivot = pivot[sorted(pivot.columns)]
    except Exception:
        pass

    # Applica formule custom
    pivot = _applica_formule(pivot, schema_config)

    # Applica segni forzati
    if schema_config:
        for voce, cfg in schema_config.items():
            if voce in pivot.index:
                segno = cfg.get('segno', 1)
                if segno == -1:
                    pivot.loc[voce] = pivot.loc[voce] * -1

    # Riordina secondo schema
    if schema_config:
        ordine = sorted(schema_config.keys(), key=lambda v: schema_config[v].get('ordine', 999))
        ordine_valido = [v for v in ordine if v in pivot.index]
        resto = [v for v in pivot.index if v not in ordine_valido]
        pivot = pivot.reindex(ordine_valido + resto)

    pivot['TOTALE'] = pivot.sum(axis=1)
    return pivot, None


def calcola_incidenza(pivot: pd.DataFrame, voce_ricavi: str = None) -> pd.Series:
    """Calcola l'incidenza % sul fatturato per la colonna TOTALE."""
    if pivot is None or 'TOTALE' not in pivot.columns:
        return pd.Series(dtype=float)

    # Cerca automaticamente la voce ricavi
    if voce_ricavi is None:
        for v in pivot.index:
            if any(k in v.lower() for k in ['ricav', 'fattur', 'vendite', 'revenue']):
                voce_ricavi = v
                break

    if voce_ricavi and voce_ricavi in pivot.index:
        base = pivot.loc[voce_ricavi, 'TOTALE']
        if base != 0:
            return (pivot['TOTALE'] / abs(base) * 100).round(1)

    return pd.Series(dtype=float)


def get_mesi_disponibili(pivot: pd.DataFrame) -> list:
    if pivot is None:
        return []
    return [c for c in pivot.columns if c != 'TOTALE']


def calcola_variazione_mensile(pivot: pd.DataFrame) -> pd.DataFrame:
    """Restituisce un DF con la variazione % mese su mese per ogni voce."""
    if pivot is None:
        return None
    mesi = get_mesi_disponibili(pivot)
    if len(mesi) < 2:
        return None
    df_var = pd.DataFrame(index=pivot.index)
    for i in range(1, len(mesi)):
        m_prec = mesi[i - 1]
        m_curr = mesi[i]
        mask = pivot[m_prec] != 0
        var = pd.Series(index=pivot.index, dtype=float)
        var[mask] = (pivot.loc[mask, m_curr] - pivot.loc[mask, m_prec]) / pivot.loc[mask, m_prec].abs() * 100
        df_var[m_curr] = var.round(1)
    return df_var
