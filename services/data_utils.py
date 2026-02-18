import pandas as pd
import io

def smart_load(file):
    """Carica CSV o Excel gestendo encoding, separatori e BOM."""
    if file is None:
        return None

    name = file.name.lower()

    try:
        if name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            # Prova prima con separatore ;
            raw = file.read()
            file.seek(0)
            for enc in ['utf-8-sig', 'latin1', 'cp1252']:
                try:
                    content = raw.decode(enc)
                    sep = ';' if content.count(';') > content.count(',') else ','
                    df = pd.read_csv(io.StringIO(content), sep=sep, on_bad_lines='skip')
                    break
                except Exception:
                    continue
            else:
                return None

        # Pulizia colonne
        df.columns = (
            df.columns.str.strip()
            .str.replace('ï»¿', '', regex=False)
            .str.replace('\ufeff', '', regex=False)
        )
        return df

    except Exception as e:
        return None


def find_column(df, candidates):
    """Trova la prima colonna che corrisponde a una delle varianti fornite."""
    if df is None:
        return None
    for name in candidates:
        if name in df.columns:
            return name
    # Ricerca case-insensitive
    lower_map = {c.lower().strip(): c for c in df.columns}
    for name in candidates:
        if name.lower().strip() in lower_map:
            return lower_map[name.lower().strip()]
    return None


def to_numeric(series):
    """Converte serie con formato italiano (. migliaia, , decimale) in float."""
    if series is None:
        return series
    if series.dtype == object:
        return (
            series.astype(str)
            .str.strip()
            .str.replace('€', '', regex=False)
            .str.replace('\xa0', '', regex=False)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .pipe(pd.to_numeric, errors='coerce')
            .fillna(0)
        )
    return pd.to_numeric(series, errors='coerce').fillna(0)


def fmt_eur(val, show_sign=False):
    """Formatta un numero come euro con separatori italiani."""
    try:
        v = float(val)
        sign = '+' if (show_sign and v > 0) else ''
        return f"{sign}{v:,.0f} €".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return str(val)


def get_cliente():
    """Restituisce il dict del cliente attivo o None."""
    import streamlit as st
    ca = st.session_state.get('cliente_attivo')
    if ca and ca in st.session_state.get('clienti', {}):
        return st.session_state['clienti'][ca]
    return None


def save_cliente(data: dict):
    """Aggiorna il dict del cliente attivo."""
    import streamlit as st
    ca = st.session_state.get('cliente_attivo')
    if ca and ca in st.session_state.get('clienti', {}):
        st.session_state['clienti'][ca].update(data)
