"""riclassifica.py — CE riclassificato con subtotali/totali e voci_include configurabili."""
import pandas as pd
import numpy as np
from services.data_utils import find_column, to_numeric


def get_label_map(df_ricl):
    if df_ricl is None or df_ricl.empty:
        return {}
    col_cod  = find_column(df_ricl, ['Codice','codice','ID','id','Voce','voce'])
    col_desc = find_column(df_ricl, ['Descrizione','descrizione','Nome','nome','Label','label'])
    if not col_cod:
        return {}
    result = {}
    for _, row in df_ricl.iterrows():
        cod  = str(row[col_cod]).strip()
        desc = str(row[col_desc]).strip() if (col_desc and col_desc != col_cod) else cod
        if cod and cod.lower() not in ('nan', 'none', ''):
            result[cod] = desc if desc.lower() not in ('nan', 'none', '') else cod
    return result


def get_conto_label_map(df_piano):
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
            row[col_data] = '01/{}/{}'.format(parts[1], parts[0]) if len(parts) == 2 else r.get('data', '')
        rows.append(row)
    if rows:
        df_db = pd.concat([df_db, pd.DataFrame(rows)], ignore_index=True)
    return df_db


def _parse_date_robust(series):
    s = series.astype(str).str.strip()
    result = pd.to_datetime(s, errors='coerce', dayfirst=True)
    if result.notna().sum() > len(s) * 0.5:
        return result
    for fmt in ['%d/%m/%Y','%d-%m-%Y','%Y-%m-%d','%d/%m/%y','%d-%m-%y',
                '%Y/%m/%d','%d.%m.%Y','%d.%m.%y','%m/%d/%Y','%Y%m%d']:
        try:
            c = pd.to_datetime(s, format=fmt, errors='coerce')
            if c.notna().sum() > result.notna().sum():
                result = c
        except Exception:
            pass
    return result


def _safe_scalar(val):
    """Estrae scalare float sicuro da Series/NaN/any."""
    if isinstance(val, pd.Series):
        val = val.iloc[0] if len(val) > 0 else 0.0
    try:
        f = float(val)
        return 0.0 if (f != f) else f  # NaN check
    except Exception:
        return 0.0


def _safe_str(val):
    if isinstance(val, pd.Series):
        val = val.iloc[0] if len(val) > 0 else ''
    try:
        return str(val)
    except Exception:
        return ''


def _applica_schema_con_totali(pivot_contabili, schema_config, label_map):
    """
    Espande pivot con righe subtotale/totale/separatore.
    voci_include: lista codici specifici da sommare (vuoto = tutti i precedenti).
    Separatori hanno label con zero-width spaces per evitare duplicati.
    """
    if not schema_config:
        pivot_contabili['_tipo'] = 'contabile'
        return pivot_contabili

    mesi_cols = [c for c in pivot_contabili.columns if c != 'TOTALE']
    all_cols  = mesi_cols + ['TOTALE']

    voci_ordinate = sorted(schema_config.keys(), key=lambda v: schema_config[v].get('ordine', 999))

    labels, data_rows, tipi = [], [], []
    _sep_counter = [0]
    accum_sub = {c: 0.0 for c in all_cols}
    accum_tot = {c: 0.0 for c in all_cols}
    voce_vals = {}  # {cod: {col: val}} per voci_include

    for cod in voci_ordinate:
        cfg  = schema_config[cod]
        tipo = cfg.get('tipo', 'contabile')
        desc = cfg.get('descrizione_override', label_map.get(cod, cod))

        if tipo == 'separatore':
            _sep_counter[0] += 1
            labels.append('\u200b' * _sep_counter[0])
            data_rows.append({c: np.nan for c in all_cols})
            tipi.append('separatore')
            continue

        if tipo == 'contabile':
            target = desc if desc in pivot_contabili.index else (cod if cod in pivot_contabili.index else None)
            if target is not None:
                row = pivot_contabili.loc[target]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                row_d = {c: _safe_scalar(row[c]) if c in row.index else 0.0 for c in all_cols}
            else:
                row_d = {c: 0.0 for c in all_cols}

            if cfg.get('segno', 1) == -1:
                row_d = {c: -v for c, v in row_d.items()}

            for c in all_cols:
                accum_sub[c] += row_d.get(c, 0.0)
                accum_tot[c] += row_d.get(c, 0.0)
            voce_vals[cod] = row_d

            labels.append(desc)
            data_rows.append(row_d)
            tipi.append('contabile')

        elif tipo in ('subtotale', 'totale'):
            voci_include = cfg.get('voci_include', [])
            if voci_include:
                sub_d = {c: sum(voce_vals.get(vc, {}).get(c, 0.0) for vc in voci_include) for c in all_cols}
                sub_d['TOTALE'] = sum(sub_d.get(c, 0.0) for c in mesi_cols)
            elif tipo == 'subtotale':
                sub_d = dict(accum_sub)
                sub_d['TOTALE'] = sum(sub_d.get(c, 0.0) for c in mesi_cols)
            else:
                sub_d = dict(accum_tot)
                sub_d['TOTALE'] = sum(sub_d.get(c, 0.0) for c in mesi_cols)

            labels.append(desc)
            data_rows.append(sub_d)
            tipi.append(tipo)
            if tipo == 'subtotale':
                accum_sub = {c: 0.0 for c in all_cols}

    if not labels:
        pivot_contabili['_tipo'] = 'contabile'
        return pivot_contabili

    result = pd.DataFrame(data_rows, index=labels)
    result.index.name = None
    result['_tipo'] = tipi
    return result


def costruisci_ce_riclassificato(df_db, df_piano, df_ricl, mapping, schema_config, rettifiche=None):
    if df_db is None or df_db.empty:
        return None, None, 'DB Contabile vuoto o non caricato.'
    if not mapping:
        return None, None, 'Nessuna mappatura configurata. Vai in Workspace → Mappatura Conti.'

    col_data  = find_column(df_db, ['Data','data','DATA','DataDoc','DataRegistrazione',
                                     'data_registrazione','DataReg','Competenza','Date'])
    col_saldo = find_column(df_db, ['Saldo','saldo','SALDO','Importo','importo',
                                     'Valore','valore','ImportoMovimento','Totale','Amount'])
    col_conto = find_column(df_db, ['Conto','conto','CONTO','CodConto','CodiceConto',
                                     'codice_conto','Mastro','mastro','Account'])

    missing = [n for n, c in [('Data', col_data),('Saldo/Importo', col_saldo),('Conto', col_conto)] if not c]
    if missing:
        return None, None, (
            'Colonne non trovate nel DB: {}.\nColonne presenti: {}\n'
            'Rinomina in: Data, CodConto (o Conto), Importo (o Saldo).'
        ).format(', '.join(missing), list(df_db.columns)[:12])

    db = df_db.copy()
    if rettifiche:
        db = applica_rettifiche(db, rettifiche, col_conto, col_saldo, col_data)

    db['_saldo_num'] = to_numeric(db[col_saldo])
    db['_data_dt']   = _parse_date_robust(db[col_data])
    db['_conto_str'] = db[col_conto].astype(str).str.strip()

    db = db[db['_data_dt'].notna() & (db['_conto_str'] != '') & (db['_conto_str'] != 'nan')]
    if db.empty:
        sample = df_db[col_data].dropna().head(3).tolist()
        return None, None, (
            'Nessuna riga valida dopo parsing date. '
            'Esempi date: {}. Formati supportati: GG/MM/AAAA, AAAA-MM-GG.'
        ).format(sample)

    db['_mese']      = db['_data_dt'].dt.to_period('M').astype(str)
    label_map        = get_label_map(df_ricl)
    conto_label      = get_conto_label_map(df_piano)

    db['_cod_voce']   = db['_conto_str'].map(mapping)
    db['_voce_label'] = db['_cod_voce'].map(label_map).fillna(db['_cod_voce'])

    db_mapped = db[
        db['_voce_label'].notna() &
        ~db['_voce_label'].astype(str).isin(['nan','None','NaN',''])
    ].copy()

    if db_mapped.empty:
        return None, None, (
            'Nessun conto del DB risulta mappato.\n'
            'Conti DB (es.): {}\nConti mapping (es.): {}'
        ).format(list(db['_conto_str'].unique())[:5], list(mapping.keys())[:5])

    db_mapped['_desc_conto']    = db_mapped['_conto_str'].map(conto_label).fillna(db_mapped['_conto_str'])
    db_mapped['_conto_display'] = db_mapped['_conto_str'] + ' — ' + db_mapped['_desc_conto']

    pivot_base = pd.pivot_table(
        db_mapped, values='_saldo_num',
        index='_voce_label', columns='_mese',
        aggfunc='sum', fill_value=0
    )
    try:
        pivot_base = pivot_base[sorted(pivot_base.columns)]
    except Exception:
        pass
    pivot_base['TOTALE'] = pivot_base.sum(axis=1)

    pivot = _applica_schema_con_totali(pivot_base, schema_config, label_map)

    dettaglio = {}
    for voce in pivot.index:
        tipo_v = _safe_str(pivot.loc[voce, '_tipo']) if '_tipo' in pivot.columns else 'contabile'
        if tipo_v != 'contabile':
            continue
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
    return [c for c in pivot.columns if c not in ('TOTALE', '_tipo')]


def _find_voce_pivot(pivot, keywords):
    if pivot is None:
        return None
    for idx in pivot.index:
        s = str(idx).lower()
        if any(str(k).lower() in s for k in keywords):
            tipo = _safe_str(pivot.loc[idx, '_tipo']) if '_tipo' in pivot.columns else 'contabile'
            if tipo in ('contabile', 'subtotale', 'totale'):
                return idx
    return None


def _sum_voce(pivot, voce, cols):
    if voce is None or voce not in pivot.index:
        return 0.0
    valid = [c for c in cols if c in pivot.columns]
    if not valid:
        return 0.0
    try:
        row = pivot.loc[voce, valid]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        return float(row.sum())
    except Exception:
        return 0.0


def calcola_kpi_finanziari(pivot, mesi_sel):
    if pivot is None or not mesi_sel:
        return {}
    cols = [c for c in mesi_sel if c in pivot.columns and c not in ('TOTALE', '_tipo')]
    if not cols:
        return {}

    def get(kw):
        return _sum_voce(pivot, _find_voce_pivot(pivot, kw), cols)
    def margin(num, den):
        return round(num / den * 100, 2) if den and abs(float(den)) > 0.01 else 0.0

    ricavi      = get(['ricav','fattur','vendite','revenue'])
    ebitda      = get(['ebitda','mol','margine operativo lordo'])
    ebit        = get(['ebit','reddito operativo','risultato operativo'])
    utile_netto = get(['utile netto','risultato netto','utile d','risultato esercizio'])
    personale   = get(['personale','lavoro','salari','stipendi'])
    acquisti    = get(['acquisti','materie prime','merci'])

    return {
        'ricavi': ricavi, 'ebitda': ebitda, 'ebit': ebit,
        'utile_netto': utile_netto, 'personale': personale, 'acquisti': acquisti,
        'ebitda_margin':  margin(ebitda, ricavi),
        'ebit_margin':    margin(ebit,   ricavi),
        'net_margin':     margin(utile_netto, ricavi),
        'cost_labor_pct': margin(abs(personale), ricavi),
        'n_mesi': len(cols), 'mesi': cols,
    }


def calcola_trend(pivot, voce, n_mesi=6):
    if pivot is None or voce not in pivot.index:
        return None
    mesi_ord = sorted([c for c in pivot.columns if c not in ('TOTALE', '_tipo')])
    if len(mesi_ord) < 2:
        return None
    mesi_used = mesi_ord[-n_mesi:] if len(mesi_ord) >= n_mesi else mesi_ord
    vals = [_safe_scalar(pivot.loc[voce, m]) for m in mesi_used]
    if len(vals) < 2:
        return None
    media = float(np.mean(vals))
    std   = float(np.std(vals))
    last3 = vals[-3:] if len(vals) >= 3 else vals
    direction = ('up'   if all(last3[i] < last3[i+1] for i in range(len(last3)-1)) else
                 'down' if all(last3[i] > last3[i+1] for i in range(len(last3)-1)) else 'flat')
    prec = vals[-2]
    mom  = ((vals[-1] - prec) / abs(prec) * 100) if prec != 0 else 0.0
    return {'vals': vals, 'mesi': mesi_used, 'media': media, 'std': std,
            'cv': abs(std/media*100) if media != 0 else 0.0,
            'mom': mom, 'direction': direction, 'ultimo': vals[-1]}


def calcola_statistiche_mensili(pivot):
    if pivot is None:
        return {}
    mesi = [c for c in pivot.columns if c not in ('TOTALE', '_tipo')]
    result = {}
    for voce in pivot.index:
        tipo = _safe_str(pivot.loc[voce, '_tipo']) if '_tipo' in pivot.columns else 'contabile'
        if tipo == 'separatore':
            continue
        vals = [_safe_scalar(pivot.loc[voce, m]) for m in mesi if m in pivot.columns]
        if not vals:
            continue
        media = float(np.mean(vals))
        std   = float(np.std(vals))
        result[voce] = {'media': media, 'std': std,
                        'min': float(min(vals)), 'max': float(max(vals)),
                        'cv': abs(std/media*100) if media != 0 else 0.0,
                        'vals': vals, 'mesi': mesi}
    return result
