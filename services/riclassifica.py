"""
riclassifica.py — CE riclassificato con subtotali/totali e voci_include.

FIX FONDAMENTALE (v3):
- _applica_schema_con_totali usa label_map.get(cod) per il lookup nel pivot,
  NON il descrizione_override che l'utente può aver cambiato
- Il pivot risultante ha colonna _cod (codice riclassifica originale)
  così il dettaglio drill-down funziona anche con label rinominati
- calcola_kpi_finanziari usa _cod + kpi_role prima del keyword fallback
"""
import pandas as pd
import numpy as np
from services.data_utils import find_column, to_numeric


# ─── LABEL MAP HELPERS ───────────────────────────────────────────────────────

def get_label_map(df_ricl):
    """cod_riclassifica → label descrittivo (da df_ricl)."""
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
    """cod_conto → descrizione conto (da df_piano)."""
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


# ─── RETTIFICHE ──────────────────────────────────────────────────────────────

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


# ─── DATE PARSING ────────────────────────────────────────────────────────────

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


# ─── SCALARI SICURI ──────────────────────────────────────────────────────────

def _safe_scalar(val):
    """float sicuro: gestisce Series/NaN/None."""
    if isinstance(val, pd.Series):
        val = val.iloc[0] if len(val) > 0 else 0.0
    try:
        f = float(val)
        return 0.0 if (f != f) else f   # NaN check: f!=f è True solo per NaN
    except Exception:
        return 0.0


def _safe_str(val):
    if isinstance(val, pd.Series):
        val = val.iloc[0] if len(val) > 0 else ''
    try:
        return str(val)
    except Exception:
        return ''


# ─── SCHEMA → PIVOT ESPANSO ──────────────────────────────────────────────────

def _applica_schema_con_totali(pivot_contabili, schema_config, label_map):
    """
    Espande pivot con subtotale/totale/separatore dallo schema.

    FIX CHIAVE: il lookup usa label_map.get(cod) come chiave primaria
    (= il label originale da df_ricl che è nell'indice di pivot_contabili),
    NON il descrizione_override che potrebbe essere stato rinominato dall'utente.

    Il DataFrame risultante ha colonne aggiuntive:
      _tipo  : contabile / subtotale / totale / separatore
      _cod   : codice riclassifica originale (per lookup successivi)
    """
    if not schema_config:
        pivot_contabili = pivot_contabili.copy()
        pivot_contabili['_tipo'] = 'contabile'
        pivot_contabili['_cod']  = pivot_contabili.index.astype(str)
        return pivot_contabili

    mesi_cols = [c for c in pivot_contabili.columns if c not in ('TOTALE',)]
    all_cols  = mesi_cols + ['TOTALE']

    voci_ordinate = sorted(schema_config.keys(), key=lambda v: schema_config[v].get('ordine', 999))

    labels, data_rows, tipi, cods = [], [], [], []
    _sep_counter = [0]
    accum_sub = {c: 0.0 for c in all_cols}
    accum_tot = {c: 0.0 for c in all_cols}
    voce_vals = {}   # cod → {col: val}

    for cod in voci_ordinate:
        cfg  = schema_config[cod]
        tipo = cfg.get('tipo', 'contabile')
        # Display label (può essere personalizzato dall'utente)
        desc = cfg.get('descrizione_override', label_map.get(cod, cod))
        # Lookup label = il label che è effettivamente nell'indice di pivot_contabili
        # Priorità: label_map[cod] (da df_ricl) > cod > desc
        lookup_label = label_map.get(cod, cod)

        if tipo == 'separatore':
            _sep_counter[0] += 1
            labels.append('\u200b' * _sep_counter[0])   # zero-width spaces = univoci
            data_rows.append({c: np.nan for c in all_cols})
            tipi.append('separatore')
            cods.append('')
            continue

        if tipo == 'contabile':
            # Lookup nel pivot usando il label originale (non l'override!)
            target = None
            for candidate in [lookup_label, cod, desc]:
                if candidate and candidate in pivot_contabili.index:
                    target = candidate
                    break

            if target is not None:
                row = pivot_contabili.loc[target]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                row_d = {c: _safe_scalar(row.get(c, 0.0)) for c in all_cols}
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
            cods.append(cod)

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
            cods.append(cod)

            if tipo == 'subtotale':
                accum_sub = {c: 0.0 for c in all_cols}

    if not labels:
        pivot_contabili = pivot_contabili.copy()
        pivot_contabili['_tipo'] = 'contabile'
        pivot_contabili['_cod']  = pivot_contabili.index.astype(str)
        return pivot_contabili

    result = pd.DataFrame(data_rows, index=labels)
    result.index.name = None
    result['_tipo'] = tipi
    result['_cod']  = cods   # ← codice riclassifica originale, stabile
    return result


# ─── CE RICLASSIFICATO ───────────────────────────────────────────────────────

def costruisci_ce_riclassificato(df_db, df_piano, df_ricl, mapping, schema_config, rettifiche=None):
    """
    Ritorna (pivot, dettaglio, errore).
    pivot: DataFrame con _tipo e _cod
    dettaglio: {voce_label: pivot_conti} per drill-down
    """
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
            'Esempi: {}. Formati supportati: GG/MM/AAAA, AAAA-MM-GG.'
        ).format(sample)

    db['_mese']       = db['_data_dt'].dt.to_period('M').astype(str)
    label_map         = get_label_map(df_ricl)
    conto_label       = get_conto_label_map(df_piano)

    # cod_voce = codice riclassifica (es. "RIC001")
    # voce_label = label leggibile (es. "Ricavi Commerciali") usato come indice pivot
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

    # Pivot base: indice = _voce_label (es. "Ricavi Commerciali")
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

    # Espandi con subtotali/totali
    pivot = _applica_schema_con_totali(pivot_base, schema_config, label_map)

    # Dettaglio drill-down:
    # CHIAVE: usiamo _cod per ritrovare i dati, NON il display label
    # perché il display label può essere stato rinominato dall'utente
    dettaglio = {}

    # Mappa cod → voce_label originale (come è in db_mapped)
    # cod è il codice riclassifica (es. "RIC001"), voce_label è "Ricavi Commerciali"
    cod_to_orig_label = {}
    if schema_config:
        for cod, cfg in schema_config.items():
            orig = label_map.get(cod, cod)
            cod_to_orig_label[cod] = orig

    for i, voce in enumerate(pivot.index):
        tipo_v = _safe_str(pivot.loc[voce, '_tipo']) if '_tipo' in pivot.columns else 'contabile'
        if tipo_v != 'contabile':
            continue

        # Recupera il codice riclassifica di questa riga
        cod_v = _safe_str(pivot.loc[voce, '_cod']) if '_cod' in pivot.columns else ''
        # Da codice → label originale in db_mapped
        orig_label = cod_to_orig_label.get(cod_v, voce)

        # Cerca in db_mapped prima con orig_label, poi con voce (display)
        df_v = db_mapped[db_mapped['_voce_label'] == orig_label]
        if df_v.empty and orig_label != voce:
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


# ─── HELPERS PIVOT ───────────────────────────────────────────────────────────

def get_mesi_disponibili(pivot):
    if pivot is None:
        return []
    return [c for c in pivot.columns if c not in ('TOTALE', '_tipo', '_cod')]


def _find_voce_by_cod(pivot, cod):
    """Cerca riga nel pivot per codice riclassifica (_cod colonna)."""
    if pivot is None or '_cod' not in pivot.columns:
        return None
    for idx in pivot.index:
        if _safe_str(pivot.loc[idx, '_cod']) == cod:
            return idx
    return None


def _find_voce_by_role(pivot, schema_config, role):
    """Cerca riga nel pivot dove schema_config[cod]['kpi_role'] == role."""
    if pivot is None or not schema_config:
        return None
    for cod, cfg in schema_config.items():
        if cfg.get('kpi_role') == role:
            # Trova la riga con _cod == cod
            voce = _find_voce_by_cod(pivot, cod)
            if voce is not None:
                return voce
    return None


def _find_voce_keywords(pivot, keywords):
    """Fallback: cerca per keyword nel label (case-insensitive)."""
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


# ─── KPI FINANZIARI ──────────────────────────────────────────────────────────

def calcola_kpi_finanziari(pivot, mesi_sel, schema_config=None):
    """
    Calcola KPI finanziari dal pivot.

    Priorità lookup per ogni KPI:
    1. kpi_role esplicito nello schema (più affidabile)
    2. Keyword matching sul label della voce (fallback)

    schema_config opzionale: se passato abilita lookup per kpi_role.
    """
    if pivot is None or not mesi_sel:
        return {}
    cols = [c for c in mesi_sel if c in pivot.columns and c not in ('TOTALE', '_tipo', '_cod')]
    if not cols:
        return {}

    def find(role, keywords):
        """Cerca prima per kpi_role, poi per keyword."""
        if schema_config:
            v = _find_voce_by_role(pivot, schema_config, role)
            if v is not None:
                return v
        return _find_voce_keywords(pivot, keywords)

    def get(role, keywords):
        return _sum_voce(pivot, find(role, keywords), cols)

    def margin(num, den):
        return round(num / den * 100, 2) if den and abs(float(den)) > 0.01 else 0.0

    ricavi      = get('ricavi',      ['ricav','fattur','vendite','revenue','proventi'])
    ebitda      = get('ebitda',      ['ebitda','mol','margine operativo lordo','margine lordo'])
    ebit        = get('ebit',        ['ebit','reddito operativo','risultato operativo'])
    utile_netto = get('utile_netto', ['utile netto','risultato netto','utile d','risultato esercizio','utile'])
    personale   = get('personale',   ['personale','lavoro','salari','stipendi','costo del lavoro'])
    acquisti    = get('acquisti',    ['acquisti','materie prime','merci','costo merci'])

    return {
        'ricavi':        ricavi,
        'ebitda':        ebitda,
        'ebit':          ebit,
        'utile_netto':   utile_netto,
        'personale':     personale,
        'acquisti':      acquisti,
        'ebitda_margin':  margin(ebitda, ricavi),
        'ebit_margin':    margin(ebit,   ricavi),
        'net_margin':     margin(utile_netto, ricavi),
        'cost_labor_pct': margin(abs(personale), ricavi),
        'n_mesi': len(cols),
        'mesi':   cols,
    }


# ─── TREND & STATISTICHE ─────────────────────────────────────────────────────

def calcola_trend(pivot, voce, n_mesi=6):
    if pivot is None or voce not in pivot.index:
        return None
    mesi_ord  = sorted([c for c in pivot.columns if c not in ('TOTALE', '_tipo', '_cod')])
    mesi_used = mesi_ord[-n_mesi:] if len(mesi_ord) >= n_mesi else mesi_ord
    if len(mesi_used) < 2:
        return None
    vals = [_safe_scalar(pivot.loc[voce, m]) for m in mesi_used]
    media = float(np.mean(vals))
    std   = float(np.std(vals))
    last3 = vals[-3:] if len(vals) >= 3 else vals
    direction = ('up'   if all(last3[i] < last3[i+1] for i in range(len(last3)-1)) else
                 'down' if all(last3[i] > last3[i+1] for i in range(len(last3)-1)) else 'flat')
    prec = vals[-2]
    mom  = ((vals[-1] - prec) / abs(prec) * 100) if prec != 0 else 0.0
    return {
        'vals': vals, 'mesi': mesi_used,
        'media': media, 'std': std,
        'cv': abs(std / media * 100) if media != 0 else 0.0,
        'mom': mom, 'direction': direction, 'ultimo': vals[-1],
    }


def calcola_statistiche_mensili(pivot):
    if pivot is None:
        return {}
    mesi = [c for c in pivot.columns if c not in ('TOTALE', '_tipo', '_cod')]
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
        result[voce] = {
            'media': media, 'std': std,
            'min': float(min(vals)), 'max': float(max(vals)),
            'cv': abs(std / media * 100) if media != 0 else 0.0,
            'vals': vals, 'mesi': mesi,
        }
    return result


def calcola_ebitda_bridge(pivot, mesi_att, mesi_prec, schema_config=None):
    if pivot is None:
        return {}
    def get_period(mesi):
        cols = [c for c in mesi if c in pivot.columns and c not in ('TOTALE', '_tipo', '_cod')]
        def s(role, kw): return _sum_voce(pivot, (_find_voce_by_role(pivot, schema_config, role) if schema_config else None) or _find_voce_keywords(pivot, kw), cols)
        return {
            'ricavi':    s('ricavi',    ['ricav','fattur']),
            'personale': s('personale', ['personale','lavoro']),
            'acquisti':  s('acquisti',  ['acquisti','materie']),
            'ebitda':    s('ebitda',    ['ebitda','mol']),
        }
    att  = get_period(mesi_att)
    prec = get_period(mesi_prec)
    d_ric = att['ricavi']      - prec['ricavi']
    d_per = -(att['personale'] - prec['personale'])
    d_acq = -(att['acquisti']  - prec['acquisti'])
    d_alt = (att['ebitda'] - prec['ebitda']) - d_ric - d_per - d_acq
    return {
        'ebitda_prec':       prec['ebitda'],
        'ebitda_att':        att['ebitda'],
        'delta_ricavi':      d_ric,
        'delta_personale':   d_per,
        'delta_acquisti':    d_acq,
        'delta_altri':       d_alt,
    }
