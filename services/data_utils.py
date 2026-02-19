import pandas as pd
import numpy as np
import io
import streamlit as st


def smart_load(file):
    if file is None:
        return None
    try:
        name = getattr(file, 'name', '').lower()
        if name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file, dtype=str)
        else:
            raw = file.read()
            df = None
            for enc in ['utf-8-sig', 'utf-8', 'latin1', 'cp1252']:
                try:
                    content = raw.decode(enc)
                    first_lines = '\n'.join(content.split('\n')[:5])
                    sep = ';' if first_lines.count(';') >= first_lines.count(',') else ','
                    df = pd.read_csv(
                        io.StringIO(content), sep=sep,
                        dtype=str, on_bad_lines='skip',
                        skip_blank_lines=True
                    )
                    break
                except Exception:
                    continue
            if df is None:
                return None
        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.replace('\ufeff', '', regex=False)
            .str.replace('ï»¿', '', regex=False)
            .str.replace('\xa0', ' ', regex=False)
        )
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        return df
    except Exception:
        return None


def find_column(df, candidates):
    if df is None or df.empty:
        return None
    cols = list(df.columns)
    for c in candidates:
        if c in cols:
            return c
    lower_map = {col.lower().strip(): col for col in cols}
    for c in candidates:
        key = c.lower().strip()
        if key in lower_map:
            return lower_map[key]
    for c in candidates:
        key = c.lower().strip()
        for col in cols:
            if key in col.lower().strip():
                return col
    return None


def to_numeric(series):
    if series is None:
        return pd.Series([], dtype=float)
    if series.dtype in [np.float64, np.float32, np.int64, np.int32]:
        return series.astype(float)
    s = series.astype(str).str.strip()
    s = s.str.replace('€', '', regex=False)
    s = s.str.replace('\xa0', '', regex=False)
    s = s.str.replace(' ', '', regex=False)
    mask_neg = s.str.startswith('(') & s.str.endswith(')')
    s = s.str.replace('(', '', regex=False).str.replace(')', '', regex=False)
    s_it = s.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    s_dot_only = s.str.replace('.', '', regex=False)
    result = pd.to_numeric(s_it, errors='coerce')
    mask_nan = result.isna()
    result[mask_nan] = pd.to_numeric(s_dot_only[mask_nan], errors='coerce')
    result = result.fillna(0)
    result[mask_neg] = result[mask_neg] * -1
    return result


def fmt_eur(val, show_sign=False, decimals=0):
    try:
        v = float(val)
        fmt = "{:,." + str(decimals) + "f}"
        s = fmt.format(abs(v)).replace(',', 'X').replace('.', ',').replace('X', '.')
        if v < 0:
            return "({} €)".format(s)
        sign = '+' if show_sign and v > 0 else ''
        return "{}{} €".format(sign, s)
    except Exception:
        return str(val)


def fmt_pct(val, show_sign=True):
    try:
        v = float(val)
        sign = '+' if show_sign and v > 0 else ''
        return "{}{:.1f}%".format(sign, v)
    except Exception:
        return "—"


def fmt_k(val):
    try:
        v = float(val)
        neg = v < 0
        av = abs(v)
        if av >= 1000000:
            s = "{:.1f}M".format(av / 1000000)
        elif av >= 1000:
            s = "{:.0f}K".format(av / 1000)
        else:
            s = "{:.0f}".format(av)
        return "({})".format(s) if neg else s
    except Exception:
        return "—"


def get_cliente():
    ca = st.session_state.get('cliente_attivo')
    if ca and ca in st.session_state.get('clienti', {}):
        return st.session_state['clienti'][ca]
    return None


def save_cliente(data):
    ca = st.session_state.get('cliente_attivo')
    if ca and ca in st.session_state.get('clienti', {}):
        st.session_state['clienti'][ca].update(data)


def get_api_key():
    k = st.session_state.get('anthropic_api_key', '')
    if k:
        return k
    try:
        k = st.secrets.get('ANTHROPIC_API_KEY', '')
        if k:
            st.session_state['anthropic_api_key'] = k
        return k
    except Exception:
        return ''


def cliente_vuoto():
    return {
        'df_piano': None,
        'df_db': None,
        'df_ricl': None,
        'rettifiche': [],
        'mapping': {},
        'schemi': {},
        'schema_attivo': None,
        'budget': {},
        'email_config': {},
        'report_history': [],
        'cfo_settings': {
            'lingua': 'italiano',
            'stile': 'executive',
            'settore': '',
            'destinatari': [],
            'auto_report': False,
        }
    }
