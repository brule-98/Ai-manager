"""riclassifica.py — Costruzione CE riclassificato, KPI, statistiche."""
import pandas as pd
import numpy as np
from services.data_utils import find_column, to_numeric


def get_label_map(df_ricl):
    """Restituisce {codice: descrizione} dallo schema di riclassifica."""
    if df_ricl is None or df_ricl.empty:
        return {}
    col_cod  = find_column(df_ricl, ['Codice','codice','ID','id','Voce','voce','Conto'])
    col_desc = find_column(df_ricl, ['Descrizione','descrizione','Nome','nome','Label','label'])
    if not col_cod:
        return {}
    result = {}
    for _, row in df_ricl.iterrows():
        cod  = str(row[col_cod]).strip()
        desc = str(row[col_desc]).strip() if (col_desc and col_desc != col_cod) else cod
        if cod and cod.lower() not in ('nan', 'none', ''):
            clean_desc = desc if desc.lower() not in ('nan', 'none', '') else cod
            result[cod] = clean_desc
    return result


def get_conto_label_map(df_piano):
    """Restituisce {codice_conto: descrizione}."""
    if df_piano is None or df_piano.empty:
        return {}
    col_cod  = find_column(df_piano, ['Codice','codice','CodConto','Conto','conto','ID'])
    col_desc = find_column(df_piano, ['Descrizione','descrizione','Nome','nome','Conto','conto'])
    if not col_cod:
        return {}
    result = {}
    for _, row in df_piano.iterrows():
        cod  = str(row[col_cod]).strip()
        desc = str(row[col_desc]).strip() if (col_desc and col_desc != col_cod) else cod
        if cod and cod.lower() not in ('nan', 'none', ''):
            result[cod] = desc if desc.lower() not in ('nan', 'none', '') else cod
    return result


def applica_rettifiche(df_db, rettifiche, col_conto, col_saldo, col_data):
    if not rettifiche:
        return df_db
    rows = []
    for r in rettifiche:
        row = {c: '' for c in df_db.columns}
        row[col_conto] = str(r.get('conto', ''))
        row[col_saldo] = str(r.get('importo', 0))
        mese = r.get('mese', '')
        if mese and col_data in df_db.columns:
            parts = mese.split('-')
            if len(parts) == 2:
                row[col_data] = '01/{}/{}'.format(parts[1], parts[0])
            else:
                row[col_data] = r.get('data', '')
        rows.append(row)
    if rows:
        df_extra = pd.DataFrame(rows)
        df_db = pd.concat([df_db, df_extra], ignore_index=True)
    return df_db


def _parse_date_robust(series):
    """Prova tutti i formati data comuni italiani e internazionali."""
    s = series.astype(str).str.strip()
    # Prova prima con pandas auto-detect (dayfirst=True per italiano)
    result = pd.to_datetime(s, errors='coerce', dayfirst=True)
    if result.notna().sum() > len(s) * 0.5:
        return result

    # Prova formati espliciti
    formats = [
        '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y',
        '%d-%m-%y', '%Y/%m/%d', '%d.%m.%Y', '%d.%m.%y',
        '%m/%d/%Y', '%Y%m%d',
    ]
    best_result = result.copy()
    best_count  = result.notna().sum()

    for fmt in formats:
        try:
            candidate = pd.to_datetime(s, format=fmt, errors='coerce')
            cnt = candidate.notna().sum()
            if cnt > best_count:
                best_count  = cnt
                best_result = candidate
        except Exception:
            continue

    return best_result


def costruisci_ce_riclassificato(df_db, df_piano, df_ricl, mapping, schema_config, rettifiche=None):
    """
    Costruisce CE riclassificato con drill-down per conto.
    Returns: (pivot_df, dettaglio_dict, errore_str)
    """
    if df_db is None or df_db.empty:
        return None, None, 'DB Contabile vuoto o non caricato.'

    if not mapping:
        return None, None, 'Nessuna mappatura configurata. Vai in Workspace → Mappatura Conti.'

    # Trova colonne nel DB
    col_data  = find_column(df_db, ['Data','data','DATA','DataDoc','DataRegistrazione',
                                     'data_registrazione','DataReg','Competenza','Date'])
    col_saldo = find_column(df_db, ['Saldo','saldo','SALDO','Importo','importo',
                                     'Valore','valore','ImportoMovimento','Totale','Amount'])
    col_conto = find_column(df_db, ['Conto','conto','CONTO','CodConto','CodiceConto',
                                     'codice_conto','Mastro','mastro','Account'])

    missing = [nome for nome, col in [('Data', col_data), ('Saldo/Importo', col_saldo), ('Conto', col_conto)] if not col]
    if missing:
        sample_cols = list(df_db.columns)[:12]
        return None, None, (
            'Colonne non trovate nel DB: {}.\n'
            'Colonne presenti: {}\n'
            'Rinomina le colonne in: Data, CodConto (o Conto), Importo (o Saldo).'
        ).format(', '.join(missing), sample_cols)

    db = df_db.copy()
    if rettifiche:
        db = applica_rettifiche(db, rettifiche, col_conto, col_saldo, col_data)

    db['_saldo_num'] = to_numeric(db[col_saldo])
    db['_data_dt']   = _parse_date_robust(db[col_data])
    db['_conto_str'] = db[col_conto].astype(str).str.strip()

    # Rimuovi righe con data nulla o conto vuoto
    n_before = len(db)
    db = db[db['_data_dt'].notna() & (db['_conto_str'] != '') & (db['_conto_str'] != 'nan')]
    n_after = len(db)

    if db.empty:
        n_null_dates = (df_db[col_data].isna() | pd.to_datetime(df_db[col_data], errors='coerce').isna()).sum()
        sample_dates = df_db[col_data].dropna().head(3).tolist()
        return None, None, (
            'Nessuna riga valida dopo parsing date. '
            'Esempi date nel file: {}. '
            'Formati supportati: GG/MM/AAAA, AAAA-MM-GG, GG-MM-AAAA, GG.MM.AAAA.'
        ).format(sample_dates)

    db['_mese'] = db['_data_dt'].dt.to_period('M').astype(str)

    label_map   = get_label_map(df_ricl)
    conto_label = get_conto_label_map(df_piano)

    # Mapping: conto → codice voce → label voce
    db['_cod_voce']   = db['_conto_str'].map(mapping)
    db['_voce_label'] = db['_cod_voce'].map(label_map).fillna(db['_cod_voce'])

    db_mapped = db[
        db['_voce_label'].notna() &
        ~db['_voce_label'].astype(str).isin(['nan', 'None', 'NaN', ''])
    ].copy()

    if db_mapped.empty:
        conti_db      = set(db['_conto_str'].unique())
        conti_mapping = set(mapping.keys())
        overlap       = conti_db & conti_mapping
        sample_db     = list(conti_db)[:5]
        sample_map    = list(conti_mapping)[:5]
        return None, None, (
            'Nessun conto del DB risulta mappato.\n'
            'Conti nel DB (es.): {}\n'
            'Conti nel mapping (es.): {}\n'
            'Codici in comune: {}.\n'
            'Verifica che i codici conto nel DB corrispondano al Piano dei Conti.'
        ).format(sample_db, sample_map, list(overlap)[:5])

    db_mapped['_desc_conto']    = db_mapped['_conto_str'].map(conto_label).fillna(db_mapped['_conto_str'])
    db_mapped['_conto_display'] = db_mapped['_conto_str'] + ' — ' + db_mapped['_desc_conto']

    # Pivot per voce × mese
    pivot = pd.pivot_table(
        db_mapped, values='_saldo_num',
        index='_voce_label', columns='_mese',
        aggfunc='sum', fill_value=0
    )
    try:
        pivot = pivot[sorted(pivot.columns)]
    except Exception:
        pass

    # Applica segni e ordine da schema_config
    if schema_config:
        for cod, cfg in schema_config.items():
            voce_desc = label_map.get(cod, cod)
            target = None
            if voce_desc in pivot.index:
                target = voce_desc
            elif cod in pivot.index:
                target = cod
            if target and cfg.get('segno', 1) == -1:
                pivot.loc[target] = pivot.loc[target] * -1

        ordine  = sorted(schema_config.keys(), key=lambda v: schema_config[v].get('ordine', 999))
        ordine_desc = [label_map.get(c, c) for c in ordine]
        validi  = [v for v in ordine_desc if v in pivot.index]
        resto   = [v for v in pivot.index  if v not in validi]
        pivot   = pivot.reindex(validi + resto)

    pivot['TOTALE'] = pivot.sum(axis=1)

    # Dettaglio per conto (drill-down)
    dettaglio = {}
    for voce in pivot.index:
        df_v = db_mapped[db_mapped['_voce_label'] == voce]
        if df_v.empty:
            continue
        piv_c = pd.pivot_table(
            df_v, values='_saldo_num',
            index='_conto_display', columns='_mese',
            aggfunc='sum', fill_value=0
        )
        try:
            piv_c = piv_c[sorted(piv_c.columns)]
        except Exception:
            pass
        piv_c['TOTALE'] = piv_c.sum(axis=1)
        dettaglio[voce] = piv_c

    return pivot, dettaglio, None


def get_mesi_disponibili(pivot):
    if pivot is None:
        return []
    return [c for c in pivot.columns if c != 'TOTALE']


def _find_voce_pivot(pivot, keywords):
    if pivot is None:
        return None
    for idx in pivot.index:
        s = str(idx).lower()
        if any(str(k).lower() in s for k in keywords):
            return idx
    return None


def _sum_voce(pivot, voce, cols):
    if voce is None or voce not in pivot.index:
        return 0.0
    valid = [c for c in cols if c in pivot.columns]
    return float(pivot.loc[voce, valid].sum()) if valid else 0.0


def calcola_kpi_finanziari(pivot, mesi_sel):
    if pivot is None or not mesi_sel:
        return {}
    cols = [c for c in mesi_sel if c in pivot.columns]
    if not cols:
        return {}

    def get(kw):
        return _sum_voce(pivot, _find_voce_pivot(pivot, kw), cols)
    def margin(num, den):
        return round(num / den * 100, 2) if den and abs(float(den)) > 0.01 else 0.0

    ricavi      = get(['ricav', 'fattur', 'vendite', 'revenue'])
    ebitda      = get(['ebitda', 'mol', 'margine operativo lordo'])
    ebit        = get(['ebit', 'reddito operativo', 'risultato operativo'])
    utile_netto = get(['utile netto', 'risultato netto', 'utile d', 'risultato esercizio'])
    personale   = get(['personale', 'lavoro', 'salari', 'stipendi'])
    acquisti    = get(['acquisti', 'materie prime', 'merci'])

    return {
        'ricavi': ricavi, 'ebitda': ebitda, 'ebit': ebit,
        'utile_netto': utile_netto, 'personale': personale, 'acquisti': acquisti,
        'ebitda_margin':  margin(ebitda,  ricavi),
        'ebit_margin':    margin(ebit,    ricavi),
        'net_margin':     margin(utile_netto, ricavi),
        'cost_labor_pct': margin(abs(personale), ricavi),
        'n_mesi': len(cols),
        'mesi':   cols,
    }


def calcola_trend(pivot, voce, n_mesi=6):
    if pivot is None or voce not in pivot.index:
        return None
    mesi_ord = sorted([c for c in pivot.columns if c != 'TOTALE'])
    if len(mesi_ord) < 2:
        return None
    mesi_used = mesi_ord[-n_mesi:] if len(mesi_ord) >= n_mesi else mesi_ord
    vals = [float(pivot.loc[voce, m]) for m in mesi_used]
    if len(vals) < 2:
        return None
    media  = float(np.mean(vals))
    std    = float(np.std(vals))
    cv     = abs(std / media * 100) if media != 0 else 0.0
    ultimo = vals[-1]
    prec   = vals[-2]
    mom    = ((ultimo - prec) / abs(prec) * 100) if prec != 0 else 0.0
    yoy    = 0.0
    if len(mesi_ord) >= 13:
        yoy_mese = mesi_ord[-13]
        if yoy_mese in pivot.columns:
            yoy_v = float(pivot.loc[voce, yoy_mese])
            yoy = ((ultimo - yoy_v) / abs(yoy_v) * 100) if yoy_v != 0 else 0.0
    last3 = vals[-3:] if len(vals) >= 3 else vals
    direction = ('up'   if all(last3[i] < last3[i+1] for i in range(len(last3)-1)) else
                 'down' if all(last3[i] > last3[i+1] for i in range(len(last3)-1)) else 'flat')
    return {'vals': vals, 'mesi': mesi_used, 'media': media, 'std': std,
            'cv': cv, 'mom': mom, 'yoy': yoy, 'direction': direction, 'ultimo': ultimo}


def calcola_ebitda_bridge(pivot, mesi_att, mesi_prec):
    if pivot is None:
        return {}
    def get_period(mesi):
        cols = [c for c in mesi if c in pivot.columns]
        def s(kw): return _sum_voce(pivot, _find_voce_pivot(pivot, kw), cols)
        return {'ricavi': s(['ricav','fattur']), 'personale': s(['personale','lavoro']),
                'acquisti': s(['acquisti','materie']), 'ebitda': s(['ebitda','mol'])}
    att  = get_period(mesi_att)
    prec = get_period(mesi_prec)
    d_ric = att['ricavi']    - prec['ricavi']
    d_per = -(att['personale'] - prec['personale'])
    d_acq = -(att['acquisti']  - prec['acquisti'])
    d_alt = (att['ebitda'] - prec['ebitda']) - d_ric - d_per - d_acq
    return {'ebitda_prec': prec['ebitda'], 'ebitda_att': att['ebitda'],
            'delta_ricavi': d_ric, 'delta_personale': d_per,
            'delta_acquisti': d_acq, 'delta_altri': d_alt}


def calcola_statistiche_mensili(pivot):
    if pivot is None:
        return {}
    mesi = [c for c in pivot.columns if c != 'TOTALE']
    result = {}
    for voce in pivot.index:
        vals = [float(pivot.loc[voce, m]) for m in mesi if m in pivot.columns]
        if not vals:
            continue
        media = float(np.mean(vals))
        std   = float(np.std(vals))
        result[voce] = {
            'media': media, 'std': std,
            'min': float(min(vals)), 'max': float(max(vals)),
            'cv': abs(std / media * 100) if media != 0 else 0.0,
            'vals': vals, 'mesi': mesi,
        }
    return result
