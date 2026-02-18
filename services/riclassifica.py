import pandas as pd
import numpy as np
from services.data_utils import to_numeric, find_column


def applica_rettifiche(df_db, rettifiche: list, col_conto: str, col_saldo: str, col_data: str):
    """
    Aggiunge righe di rettifica extra-contabile al DB contabile.
    rettifiche: lista di dict {conto, descrizione, importo, data, mese}
    """
    if not rettifiche:
        return df_db

    rows = []
    for r in rettifiche:
        row = {c: None for c in df_db.columns}
        row[col_conto] = r.get('conto', '')
        row[col_saldo] = r.get('importo', 0)
        if col_data in df_db.columns:
            row[col_data] = r.get('data', '')
        row['_rettifica'] = True
        row['_desc_rettifica'] = r.get('descrizione', '')
        rows.append(row)

    df_rtt = pd.DataFrame(rows)
    return pd.concat([df_db, df_rtt], ignore_index=True)


def costruisci_ce_riclassificato(
    df_db: pd.DataFrame,
    df_piano: pd.DataFrame,
    df_ricl: pd.DataFrame,
    mapping: dict,
    schema_config: dict,
    rettifiche: list = None
) -> pd.DataFrame:
    """
    Costruisce il Conto Economico riclassificato mensilizzato.

    Returns:
        DataFrame con index = voci riclassifica, columns = mesi + TOTALE
    """
    # Individua colonne
    col_data = find_column(df_db, ['Data', 'data', 'DATA', 'data_registrazione'])
    col_saldo = find_column(df_db, ['Saldo', 'saldo', 'SALDO', 'Importo', 'importo', 'Valore'])
    col_conto_db = find_column(df_db, ['Conto', 'conto', 'CONTO', 'Codice Conto', 'codice_conto'])

    if not all([col_data, col_saldo, col_conto_db]):
        return None, "Colonne non trovate nel DB contabile (servono: Data, Saldo, Conto)"

    db = df_db.copy()

    # Applica rettifiche
    if rettifiche:
        db = applica_rettifiche(db, rettifiche, col_conto_db, col_saldo, col_data)

    # Pulizia
    db['_saldo_num'] = to_numeric(db[col_saldo])
    db['_data_dt'] = pd.to_datetime(db[col_data], format='%d/%m/%Y', errors='coerce')
    db['_mese'] = db['_data_dt'].dt.to_period('M').astype(str)
    db['_anno'] = db['_data_dt'].dt.year

    # Mappa conto → voce riclassifica
    db['_voce_ricl'] = db[col_conto_db].astype(str).map(mapping)

    # Prendi solo righe mappate
    db_mapped = db[db['_voce_ricl'].notna()].copy()

    if db_mapped.empty:
        return None, "Nessun conto mappato trovato. Configura la mappatura nel Workspace."

    # Pivot mensile
    pivot = pd.pivot_table(
        db_mapped,
        values='_saldo_num',
        index='_voce_ricl',
        columns='_mese',
        aggfunc='sum',
        fill_value=0
    )

    # Ordina colonne per data
    try:
        pivot = pivot[sorted(pivot.columns)]
    except Exception:
        pass

    # Applica segni forzati da schema_config
    if schema_config:
        for voce, cfg in schema_config.items():
            if voce in pivot.index:
                segno = cfg.get('segno', 1)
                if segno == -1:
                    pivot.loc[voce] = pivot.loc[voce] * -1

    # Reindex secondo ordine configurato
    if schema_config:
        ordine = sorted(schema_config.keys(), key=lambda v: schema_config[v].get('ordine', 999))
        ordine_valido = [v for v in ordine if v in pivot.index]
        resto = [v for v in pivot.index if v not in ordine_valido]
        pivot = pivot.reindex(ordine_valido + resto)

    # Colonna totale
    pivot['TOTALE'] = pivot.sum(axis=1)

    return pivot, None


def calcola_ytd(pivot: pd.DataFrame, mesi_sel: list) -> pd.DataFrame:
    """Restituisce la vista YTD per i mesi selezionati."""
    if pivot is None:
        return None
    cols = [c for c in mesi_sel if c in pivot.columns]
    if not cols:
        return pivot[['TOTALE']]
    df = pivot[cols].copy()
    df['YTD'] = df.sum(axis=1)
    return df


def get_mesi_disponibili(pivot: pd.DataFrame) -> list:
    if pivot is None:
        return []
    return [c for c in pivot.columns if c != 'TOTALE']
