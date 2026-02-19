"""data_utils.py — Utility core. Zero type hints moderni per max compatibilità."""
import pandas as pd
import numpy as np
import io
import streamlit as st


def smart_load(file):
    """
    Carica CSV/Excel da UploadedFile Streamlit.
    Gestisce: utf-8, utf-8-sig, latin1, cp1252; separatori ; , tab;
    formati Excel .xlsx .xls; BOM; encoding italiani.
    """
    if file is None:
        return None
    try:
        name = getattr(file, 'name', '') or ''
        name = name.lower().strip()

        # ── Excel ──────────────────────────────────────────────────────────
        if name.endswith(('.xlsx', '.xls', '.xlsm')):
            try:
                # reset file position
                if hasattr(file, 'seek'):
                    file.seek(0)
                df = pd.read_excel(file, dtype=str)
            except Exception as e1:
                try:
                    if hasattr(file, 'seek'):
                        file.seek(0)
                    raw = file.read()
                    df = pd.read_excel(io.BytesIO(raw), dtype=str)
                except Exception:
                    return None

        # ── CSV / TXT ──────────────────────────────────────────────────────
        else:
            if hasattr(file, 'seek'):
                file.seek(0)
            raw = file.read()
            if not raw:
                return None

            df = None
            for enc in ['utf-8-sig', 'utf-8', 'latin1', 'cp1252', 'iso-8859-15']:
                try:
                    text = raw.decode(enc)
                except Exception:
                    continue

                lines = [l for l in text.split('\n') if l.strip()]
                if len(lines) < 2:
                    continue

                # Detect separator from first 10 lines
                sample = '\n'.join(lines[:10])
                counts = {
                    ';': sample.count(';'),
                    ',': sample.count(','),
                    '\t': sample.count('\t'),
                    '|': sample.count('|'),
                }
                sep = max(counts, key=counts.get)
                if counts[sep] == 0:
                    sep = ','

                try:
                    candidate = pd.read_csv(
                        io.StringIO(text), sep=sep, dtype=str,
                        on_bad_lines='skip', skip_blank_lines=True,
                        low_memory=False
                    )
                    if len(candidate.columns) >= 2 and len(candidate) >= 1:
                        df = candidate
                        break
                except Exception:
                    continue

            if df is None:
                return None

        # ── Pulizia colonne ────────────────────────────────────────────────
        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.replace('\ufeff', '', regex=False)  # BOM
            .str.replace('\u200b', '', regex=False)  # zero-width space
            .str.replace('\xa0', ' ', regex=False)   # non-breaking space
        )
        # Rimuovi colonne "Unnamed"
        df = df.loc[:, ~df.columns.str.startswith('Unnamed')]

        # Rimuovi righe completamente vuote
        df = df.dropna(how='all')
        df = df[~df.apply(lambda r: r.astype(str).str.strip().eq('').all(), axis=1)]
        df = df.reset_index(drop=True)

        return df if not df.empty else None

    except Exception:
        return None


def find_column(df, candidates):
    """
    Trova colonna per nome. Prova: esatto → case-insensitive → partial.
    """
    if df is None or df.empty:
        return None
    cols = list(df.columns)

    # 1. Esatto
    for c in candidates:
        if c in cols:
            return c

    # 2. Case-insensitive
    lower_map = {str(col).lower().strip(): col for col in cols}
    for c in candidates:
        k = str(c).lower().strip()
        if k in lower_map:
            return lower_map[k]

    # 3. Partial match (candidato contenuto nel nome colonna)
    for c in candidates:
        k = str(c).lower().strip()
        for col in cols:
            if k in str(col).lower().strip():
                return col

    return None


def to_numeric(series):
    """
    Converte serie testuale a float. Gestisce:
    - Formato italiano: 1.234,56 → 1234.56
    - Formato US: 1,234.56 → 1234.56
    - Negativi in parentesi: (1.234) → -1234
    - Simbolo euro, spazi, NBSP
    """
    if series is None:
        return pd.Series([], dtype=float)

    # Se già numerica
    if hasattr(series, 'dtype'):
        if series.dtype in [np.float64, np.float32, np.int64, np.int32, int, float]:
            return series.astype(float)

    s = series.astype(str).str.strip()
    # Rimuovi caratteri non numerici non significativi
    s = s.str.replace('€', '', regex=False)
    s = s.str.replace('\xa0', '', regex=False)
    s = s.str.replace('\u202f', '', regex=False)
    s = s.str.replace('\u00a0', '', regex=False)
    s = s.str.replace(' ', '', regex=False)

    # Identifica negativi tra parentesi: (100) → -100
    mask_paren = s.str.match(r'^\(.*\)$')
    s = s.str.replace('(', '', regex=False).str.replace(')', '', regex=False)

    # Identificare il formato: se ci sono punti E virgole, quale è il decimale?
    # Italiano: 1.234,56 → rimuovi punto, sostituisci virgola con punto
    # US:       1,234.56 → rimuovi virgola
    # Solo virgola: 1234,56 → sostituisci virgola con punto
    # Solo punto:   1234.56 → ok così
    has_dot   = s.str.contains(r'\.', regex=True)
    has_comma = s.str.contains(',', regex=False)

    s_it = s.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    s_en = s.str.replace(',', '', regex=False)

    result = pd.to_numeric(s_it, errors='coerce')
    # Dove it-parse fallisce, prova en
    bad = result.isna() & (s != '') & (s.str.lower() != 'nan') & (s != '0')
    if bad.any():
        result[bad] = pd.to_numeric(s_en[bad], errors='coerce')

    result = result.fillna(0.0)

    # Applica segno negativo per parentesi
    result[(mask_paren) & (result > 0)] *= -1

    return result


def fmt_eur(val, show_sign=False, decimals=0):
    try:
        v = float(val)
        fmt_str = '{:,.' + str(decimals) + 'f}'
        s = fmt_str.format(abs(v)).replace(',', 'X').replace('.', ',').replace('X', '.')
        if v < 0:
            return '({} €)'.format(s)
        prefix = '+' if show_sign and v > 0 else ''
        return '{}{} €'.format(prefix, s)
    except Exception:
        return str(val)


def fmt_pct(val, show_sign=True):
    try:
        v = float(val)
        prefix = '+' if show_sign and v > 0 else ''
        return '{}{:.1f}%'.format(prefix, v)
    except Exception:
        return '—'


def fmt_k(val):
    try:
        v = float(val)
        av = abs(v)
        if av >= 1_000_000:
            s = '{:.1f}M'.format(av / 1_000_000)
        elif av >= 1_000:
            s = '{:.0f}K'.format(av / 1_000)
        else:
            s = '{:.0f}'.format(av)
        return '({})'.format(s) if v < 0 else s
    except Exception:
        return '—'


def get_cliente():
    ca = st.session_state.get('cliente_attivo')
    if ca and ca in st.session_state.get('clienti', {}):
        return st.session_state['clienti'][ca]
    return None


def save_cliente(data):
    """Salva dati nel cliente attivo in session_state."""
    ca = st.session_state.get('cliente_attivo')
    if ca and ca in st.session_state.get('clienti', {}):
        st.session_state['clienti'][ca].update(data)


def get_mapping():
    """Legge mapping DIRETTAMENTE da session_state (non copia)."""
    ca = st.session_state.get('cliente_attivo')
    if ca and ca in st.session_state.get('clienti', {}):
        return st.session_state['clienti'][ca].setdefault('mapping', {})
    return {}


def set_mapping(mapping_dict):
    """Scrive mapping DIRETTAMENTE in session_state."""
    ca = st.session_state.get('cliente_attivo')
    if ca and ca in st.session_state.get('clienti', {}):
        st.session_state['clienti'][ca]['mapping'] = mapping_dict


def get_api_key():
    k = st.session_state.get('anthropic_api_key', '')
    if k:
        return k
    try:
        k = st.secrets.get('ANTHROPIC_API_KEY', '') or ''
        if k:
            st.session_state['anthropic_api_key'] = k
        return k
    except Exception:
        return ''


def cliente_vuoto():
    return {
        'df_piano': None, 'df_db': None, 'df_ricl': None,
        'mapping': {}, 'rettifiche': [],
        'schemi': {}, 'schema_attivo': None,
        'budget': {}, 'email_config': {}, 'report_history': [],
        'cfo_settings': {
            'lingua': 'italiano', 'stile': 'executive',
            'settore': '', 'destinatari': [], 'auto_report': False,
        }
    }
