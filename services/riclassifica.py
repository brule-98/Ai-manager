"""
riclassifica.py — Motore di riclassificazione CE + KPI + Trend.
Tutte le funzioni richieste dagli altri moduli sono qui.
"""
import pandas as pd
import numpy as np
from services.data_utils import to_numeric, find_column


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def get_label_map(df_ricl) -> dict:
    """Restituisce {codice_voce: descrizione_voce} dallo schema di riclassifica."""
    if df_ricl is None:
        return {}
    col_cod  = find_column(df_ricl, ['Codice','codice','Voce','voce','ID','id','Codice Voce','CodiceVoce'])
    col_desc = find_column(df_ricl, ['Descrizione','descrizione','Voce','voce','Nome','nome','Label','label'])
    if not col_cod:
        return {}
    result = {}
    for _, row in df_ricl.iterrows():
        cod  = str(row[col_cod]).strip()
        desc = str(row[col_desc]).strip() if col_desc and col_desc != col_cod else cod
        if cod and cod not in ('nan','None',''):
            result[cod] = desc
    return result


def get_conto_label_map(df_piano) -> dict:
    """Restituisce {codice_conto: descrizione_conto} dal piano dei conti."""
    if df_piano is None:
        return {}
    col_cod  = find_column(df_piano, ['Codice','codice','codice conto','Codice Conto','CODICE','Conto','conto'])
    col_desc = find_column(df_piano, ['Descrizione','descrizione','Nome','nome','Conto','conto'])
    if not col_cod:
        return {}
    result = {}
    for _, row in df_piano.iterrows():
        cod  = str(row[col_cod]).strip()
        desc = str(row[col_desc]).strip() if col_desc and col_desc != col_cod else cod
        if cod and cod not in ('nan','None',''):
            result[cod] = desc
    return result


def applica_rettifiche(df_db, rettifiche, col_conto, col_saldo, col_data):
    """Aggiunge le rettifiche attive al DataFrame contabile."""
    if not rettifiche:
        return df_db
    rows = []
    for r in rettifiche:
        if not r.get('attiva', True):
            continue
        row = {c: None for c in df_db.columns}
        row[col_conto] = r.get('conto', '')
        row[col_saldo] = r.get('importo', 0)
        mese = r.get('mese', '')
        if mese and col_data in df_db.columns:
            # Converti YYYY-MM in 01/MM/YYYY
            try:
                parts = mese.split('-')
                row[col_data] = f"01/{parts[1]}/{parts[0]}"
            except Exception:
                if col_data in df_db.columns:
                    row[col_data] = r.get('data', '')
        row['_rettifica'] = True
        rows.append(row)
    if not rows:
        return df_db
    return pd.concat([df_db, pd.DataFrame(rows)], ignore_index=True)


# ─── MOTORE CE ────────────────────────────────────────────────────────────────

def costruisci_ce_riclassificato(df_db, df_piano, df_ricl, mapping, schema_config, rettifiche=None):
    """
    Costruisce Conto Economico riclassificato con drill-down per conto.

    Returns:
        pivot     — DataFrame (index=voce_label, columns=mesi + 'TOTALE')
        dettaglio — dict {voce_label: DataFrame(index=conto_display, columns=mesi+'TOTALE')}
        errore    — str | None
    """
    col_data  = find_column(df_db, ['Data','data','DATA','DataDoc','data_registrazione','DataReg'])
    col_saldo = find_column(df_db, ['Saldo','saldo','SALDO','Importo','importo','Valore','valore','ImportoMovimento','Dare','Avere'])
    col_conto = find_column(df_db, ['Conto','conto','CONTO','Codice Conto','codice_conto','CodConto','CodiceConto'])

    if not all([col_data, col_saldo, col_conto]):
        missing = [n for n, c in [('Data', col_data),('Saldo/Importo', col_saldo),('Conto', col_conto)] if not c]
        return None, None, f"Colonne non trovate nel DB: {', '.join(missing)}"

    db = df_db.copy()
    if rettifiche:
        db = applica_rettifiche(db, rettifiche, col_conto, col_saldo, col_data)

    db['_saldo_num'] = to_numeric(db[col_saldo])
    db['_data_dt']   = pd.to_datetime(db[col_data], format='%d/%m/%Y', errors='coerce')
    db['_mese']      = db['_data_dt'].dt.to_period('M').astype(str)
    db['_conto_str'] = db[col_conto].astype(str).str.strip()

    label_map   = get_label_map(df_ricl)
    conto_label = get_conto_label_map(df_piano)

    # Mapping conto → voce riclassifica
    db['_cod_voce']   = db['_conto_str'].map(mapping)
    db['_voce_label'] = db['_cod_voce'].map(label_map).fillna(db['_cod_voce'])
    db_mapped = db[db['_voce_label'].notna() & db['_voce_label'].ne('None') & db['_voce_label'].ne('nan')].copy()

    if db_mapped.empty:
        return None, None, "Nessun conto mappato. Configura la mappatura nel Workspace."

    db_mapped['_desc_conto']    = db_mapped['_conto_str'].map(conto_label).fillna(db_mapped['_conto_str'])
    db_mapped['_conto_display'] = db_mapped['_conto_str'] + ' — ' + db_mapped['_desc_conto']

    # ── Pivot aggregato per voce ──────────────────────────────────────────────
    pivot = pd.pivot_table(
        db_mapped, values='_saldo_num', index='_voce_label',
        columns='_mese', aggfunc='sum', fill_value=0
    )
    try:
        pivot = pivot[sorted(pivot.columns)]
    except Exception:
        pass

    # Applica segni e ordine da schema_config
    if schema_config:
        for cod, cfg in schema_config.items():
            voce_desc = label_map.get(cod, cod)
            target = voce_desc if voce_desc in pivot.index else (cod if cod in pivot.index else None)
            if target and cfg.get('segno', 1) == -1:
                pivot.loc[target] = pivot.loc[target] * -1

        ordine_cod  = sorted(schema_config.keys(), key=lambda v: schema_config[v].get('ordine', 999))
        ordine_desc = [label_map.get(c, c) for c in ordine_cod]
        validi = [v for v in ordine_desc if v in pivot.index]
        resto  = [v for v in pivot.index if v not in validi]
        pivot  = pivot.reindex(validi + resto)

    pivot['TOTALE'] = pivot.sum(axis=1)

    # ── Dettaglio per conto (drill-down) ─────────────────────────────────────
    dettaglio = {}
    for voce in pivot.index:
        df_v = db_mapped[db_mapped['_voce_label'] == voce]
        if df_v.empty:
            continue
        piv_c = pd.pivot_table(
            df_v, values='_saldo_num', index='_conto_display',
            columns='_mese', aggfunc='sum', fill_value=0
        )
        try:
            piv_c = piv_c[sorted(piv_c.columns)]
        except Exception:
            pass
        piv_c['TOTALE'] = piv_c.sum(axis=1)
        dettaglio[voce] = piv_c

    return pivot, dettaglio, None


# ─── KPI ─────────────────────────────────────────────────────────────────────

def get_mesi_disponibili(pivot) -> list:
    """Restituisce lista mesi ordinati (esclude 'TOTALE')."""
    if pivot is None:
        return []
    return [c for c in pivot.columns if c != 'TOTALE']


def _find_voce_pivot(pivot, keywords: list):
    """Cerca la prima voce nell'indice del pivot che contiene uno dei keyword."""
    if pivot is None:
        return None
    for kw in keywords:
        for v in pivot.index:
            if kw.lower() in str(v).lower():
                return v
    return None


def _sum_voce(pivot, voce, cols) -> float:
    """Somma i valori di una voce sui mesi selezionati."""
    if voce is None or voce not in pivot.index:
        return 0.0
    return float(sum(pivot.loc[voce, c] for c in cols if c in pivot.columns))


def calcola_kpi_finanziari(pivot, mesi_sel: list) -> dict:
    """
    Calcola KPI finanziari principali dal pivot CE per i mesi selezionati.
    Usa ricerca semantica per trovare le voci rilevanti.

    Returns: dict con ricavi, ebitda, ebit, utile_netto, margini...
    """
    if pivot is None or pivot.empty:
        return {}

    cols = [c for c in mesi_sel if c in pivot.columns]
    if not cols:
        # Fallback: tutti i mesi disponibili
        cols = [c for c in pivot.columns if c != 'TOTALE']
    if not cols:
        return {}

    def get(kw_list):
        v = _find_voce_pivot(pivot, kw_list)
        return _sum_voce(pivot, v, cols)

    ricavi          = get(['ricav','fattur','vendite','Revenue','Turnover'])
    costo_venduto   = get(['costo del venduto','acquisti','materie prime','merci','costi diretti'])
    ebitda          = get(['ebitda','mol','margine operativo lordo'])
    ebit            = get(['ebit','reddito operativo','risultato operativo'])
    utile_netto     = get(['utile netto','risultato netto','utile esercizio','reddito netto'])
    costi_personale = get(['personale','lavoro','stipendi','salari','collaboratori'])
    ammortamenti    = get(['ammortamento','ammortamenti','svalutazione'])
    oneri_fin       = get(['oneri finanziari','interessi passivi','interessi'])

    # Gross margin (se disponibile)
    gross_profit = ricavi - costo_venduto if costo_venduto else None

    # Calcola EBITDA da EBIT + ammortamenti se non trovato direttamente
    if ebitda == 0 and ebit != 0 and ammortamenti != 0:
        ebitda = ebit + abs(ammortamenti)

    def margin(num, den):
        if den and abs(den) > 0:
            return round(num / den * 100, 2)
        return None

    n_mesi = len(cols)

    kpi = {
        # Valori assoluti
        'ricavi':           ricavi,
        'ebitda':           ebitda,
        'ebit':             ebit,
        'utile_netto':      utile_netto,
        'costi_personale':  costi_personale,
        'ammortamenti':     ammortamenti,
        'oneri_finanziari': oneri_fin,

        # Margini %
        'ebitda_margin':    margin(ebitda, ricavi),
        'ebit_margin':      margin(ebit, ricavi),
        'net_margin':       margin(utile_netto, ricavi),
        'gross_margin':     margin(gross_profit, ricavi) if gross_profit is not None else None,
        'cost_labor_pct':   margin(costi_personale, ricavi),

        # Derived
        'ricavi_mensili_avg': round(ricavi / n_mesi, 0) if n_mesi > 0 else 0,
        'ebitda_mensile_avg': round(ebitda / n_mesi, 0) if n_mesi > 0 else 0,
        'n_mesi':             n_mesi,

        # Meta
        '_voci': {
            'ricavi':          _find_voce_pivot(pivot, ['ricav','fattur','vendite']),
            'ebitda':          _find_voce_pivot(pivot, ['ebitda','mol']),
            'ebit':            _find_voce_pivot(pivot, ['ebit','reddito operativo']),
            'utile_netto':     _find_voce_pivot(pivot, ['utile netto','risultato netto']),
        }
    }
    return kpi


def calcola_trend(pivot, voce: str, n_mesi: int = 6) -> dict | None:
    """
    Calcola statistiche di trend per una voce specifica.

    Returns:
        dict con media, std, cv (coeff. variazione), mom (MoM%), yoy (YoY%), vals
    """
    if pivot is None or voce not in pivot.index:
        return None

    all_mesi = [c for c in pivot.columns if c != 'TOTALE']
    mesi_an  = all_mesi[-n_mesi:]
    vals     = [float(pivot.loc[voce, m]) for m in mesi_an if m in pivot.columns]

    if len(vals) < 2:
        return None

    media = float(np.mean(vals))
    std   = float(np.std(vals))
    cv    = float(std / abs(media) * 100) if media != 0 else 0.0
    mom   = float((vals[-1] - vals[-2]) / abs(vals[-2]) * 100) if vals[-2] != 0 else 0.0

    yoy = None
    if len(all_mesi) >= 13:
        all_vals = [float(pivot.loc[voce, m]) for m in all_mesi if m in pivot.columns]
        if len(all_vals) >= 13 and all_vals[-13] != 0:
            yoy = float((all_vals[-1] - all_vals[-13]) / abs(all_vals[-13]) * 100)

    # Trend direction: cresita/calo per ultimi 3 mesi
    if len(vals) >= 3:
        last3 = vals[-3:]
        if all(last3[i] >= last3[i-1] for i in range(1, 3)):
            direction = 'up'
        elif all(last3[i] <= last3[i-1] for i in range(1, 3)):
            direction = 'down'
        else:
            direction = 'flat'
    else:
        direction = 'flat'

    return {
        'media':     media,
        'std':       std,
        'cv':        cv,
        'mom':       mom,
        'yoy':       yoy,
        'vals':      vals,
        'mesi':      mesi_an,
        'direction': direction,
        'ultimo':    vals[-1] if vals else 0,
    }


def calcola_ebitda_bridge(pivot, mesi_att: list, mesi_prec: list) -> dict:
    """
    Calcola EBITDA Bridge tra due periodi.
    Returns: dict con componenti del bridge.
    """
    if pivot is None:
        return {}

    def get_period(mesi):
        cols = [c for c in mesi if c in pivot.columns]
        result = {}
        for voce in pivot.index:
            result[voce] = sum(float(pivot.loc[voce, c]) for c in cols if c in pivot.columns)
        return result

    att  = get_period(mesi_att)
    prec = get_period(mesi_prec)

    bridge = {}
    for voce in pivot.index:
        v_att  = att.get(voce, 0)
        v_prec = prec.get(voce, 0)
        bridge[voce] = {
            'attuale':    v_att,
            'precedente': v_prec,
            'delta':      v_att - v_prec,
            'delta_pct':  ((v_att - v_prec) / abs(v_prec) * 100) if v_prec != 0 else None
        }

    return bridge


def calcola_statistiche_mensili(pivot) -> dict:
    """
    Calcola statistiche mensili per tutte le voci: media, std, min, max, trend.
    """
    if pivot is None:
        return {}
    mesi = [c for c in pivot.columns if c != 'TOTALE']
    result = {}
    for voce in pivot.index:
        vals = [float(pivot.loc[voce, m]) for m in mesi if m in pivot.columns]
        if not vals:
            continue
        result[voce] = {
            'media': float(np.mean(vals)),
            'std':   float(np.std(vals)),
            'min':   float(np.min(vals)),
            'max':   float(np.max(vals)),
            'cv':    float(np.std(vals) / abs(np.mean(vals)) * 100) if np.mean(vals) != 0 else 0,
            'vals':  vals,
            'mesi':  mesi,
        }
    return result
