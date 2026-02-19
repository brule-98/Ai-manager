"""
data_utils.py — Utility fondamentali per caricamento, pulizia e accesso dati.
Gestisce encoding italiano, separatori CSV multipli, formati data e numerici.
"""
import pandas as pd
import numpy as np
import io
import streamlit as st


# ─── CARICAMENTO FILE ─────────────────────────────────────────────────────────

def smart_load(file) -> pd.DataFrame | None:
    """
    Carica CSV o Excel con gestione automatica di:
    - Encoding: utf-8-sig, latin1, cp1252
    - Separatori: ; o ,
    - BOM (Byte Order Mark)
    - Caratteri speciali italiani
    """
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
                    # Rileva separatore
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

        # Pulizia colonne
        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.replace('\ufeff', '', regex=False)  # BOM
            .str.replace('ï»¿', '', regex=False)     # BOM latin
            .str.replace('\xa0', ' ', regex=False)   # NBSP
        )
        # Rimuovi righe completamente vuote
        df = df.dropna(how='all')
        # Rimuovi colonne completamente vuote
        df = df.dropna(axis=1, how='all')
        return df
    except Exception:
        return None


# ─── RILEVAMENTO COLONNE ──────────────────────────────────────────────────────

def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """
    Trova la prima colonna corrispondente tra le varianti fornite.
    Prima cerca match esatto, poi case-insensitive, poi partial match.
    """
    if df is None or df.empty:
        return None
    cols = list(df.columns)

    # 1. Match esatto
    for c in candidates:
        if c in cols:
            return c

    # 2. Match case-insensitive
    lower_map = {col.lower().strip(): col for col in cols}
    for c in candidates:
        key = c.lower().strip()
        if key in lower_map:
            return lower_map[key]

    # 3. Partial match (il candidato è contenuto nel nome colonna)
    for c in candidates:
        key = c.lower().strip()
        for col in cols:
            if key in col.lower().strip():
                return col

    return None


# ─── CONVERSIONE NUMERICA ─────────────────────────────────────────────────────

def to_numeric(series: pd.Series) -> pd.Series:
    """
    Converte serie con formato contabile italiano in float.
    Gestisce: 1.234,56 → 1234.56, (1.234) → -1234, (1.234,56) → -1234.56
    """
    if series is None:
        return pd.Series([], dtype=float)
    if series.dtype in [np.float64, np.float32, np.int64, np.int32]:
        return series.astype(float)

    s = series.astype(str).str.strip()
    # Rimuovi simboli valuta e spazi
    s = s.str.replace('€', '', regex=False)
    s = s.str.replace('\xa0', '', regex=False)
    s = s.str.replace(' ', '', regex=False)

    # Gestisci negativi tra parentesi: (1.234,56) → -1234.56
    mask_neg = s.str.startswith('(') & s.str.endswith(')')
    s = s.str.replace('(', '', regex=False).str.replace(')', '', regex=False)

    # Formato italiano: punto = migliaia, virgola = decimale
    # Distingui dal formato anglosassone: virgola = migliaia, punto = decimale
    has_both = s.str.contains(r'\.') & s.str.contains(',')
    it_format = s.str.count(',') == 1  # Una sola virgola → probabilmente decimale

    # Applica conversione italiana
    s_it = s.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    # Per valori senza virgola ma con punto (es: 1.234 inteso come 1234)
    s_dot_only = s.str.replace('.', '', regex=False)

    result = pd.to_numeric(s_it, errors='coerce')
    # Dove s_it fallisce, prova s_dot_only
    mask_nan = result.isna()
    result[mask_nan] = pd.to_numeric(s_dot_only[mask_nan], errors='coerce')
    result = result.fillna(0)

    # Applica segno negativo per valori tra parentesi
    result[mask_neg] = result[mask_neg] * -1

    return result


# ─── FORMATTAZIONE ────────────────────────────────────────────────────────────

def fmt_eur(val, show_sign: bool = False, decimals: int = 0) -> str:
    """Formatta valore come euro con separatori italiani."""
    try:
        v = float(val)
        fmt = f"{{:,.{decimals}f}}"
        s = fmt.format(abs(v)).replace(',', 'X').replace('.', ',').replace('X', '.')
        if v < 0:
            return f"({s} €)"
        sign = '+' if show_sign and v > 0 else ''
        return f"{sign}{s} €"
    except Exception:
        return str(val)


def fmt_pct(val, show_sign: bool = True) -> str:
    """Formatta valore come percentuale."""
    try:
        v = float(val)
        sign = '+' if show_sign and v > 0 else ''
        return f"{sign}{v:.1f}%"
    except Exception:
        return "—"


def fmt_k(val) -> str:
    """Formatta in migliaia (K) o milioni (M)."""
    try:
        v = float(val)
        neg = v < 0
        av = abs(v)
        if av >= 1_000_000:
            s = f"{av/1_000_000:.1f}M"
        elif av >= 1_000:
            s = f"{av/1_000:.0f}K"
        else:
            s = f"{av:.0f}"
        return f"({s})" if neg else s
    except Exception:
        return "—"


# ─── ACCESSO STATO SESSIONE ───────────────────────────────────────────────────

def get_cliente() -> dict | None:
    """Restituisce il dict del cliente attivo o None."""
    ca = st.session_state.get('cliente_attivo')
    if ca and ca in st.session_state.get('clienti', {}):
        return st.session_state['clienti'][ca]
    return None


def save_cliente(data: dict):
    """Aggiorna il dict del cliente attivo in session_state."""
    ca = st.session_state.get('cliente_attivo')
    if ca and ca in st.session_state.get('clienti', {}):
        st.session_state['clienti'][ca].update(data)


def get_api_key() -> str:
    """Recupera Anthropic API Key da session_state o secrets."""
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


def cliente_vuoto() -> dict:
    """Restituisce la struttura iniziale di un cliente."""
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
