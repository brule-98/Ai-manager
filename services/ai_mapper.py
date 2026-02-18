import anthropic
import json
import streamlit as st


def get_api_key():
    """Recupera la chiave API da st.secrets o session_state."""
    if 'anthropic_api_key' in st.session_state and st.session_state['anthropic_api_key']:
        return st.session_state['anthropic_api_key']
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return None


def ai_suggest_mapping(df_piano, df_ricl, existing_mapping: dict = None) -> dict:
    """
    Usa Claude per suggerire la mappatura conto → voce di riclassifica.

    Args:
        df_piano: DataFrame piano dei conti (colonne: codice, descrizione)
        df_ricl:  DataFrame schema riclassifica (colonne: codice_ricl, descrizione_ricl)
        existing_mapping: mapping già esistente da escludere o da usare come contesto

    Returns:
        dict {codice_conto: codice_voce_ricl}
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("API Key Anthropic non configurata.")

    client = anthropic.Anthropic(api_key=api_key)

    # Prepara dati per il prompt
    piano_list = df_piano.to_dict(orient='records')
    ricl_list = df_ricl.to_dict(orient='records')

    piano_str = json.dumps(piano_list[:200], ensure_ascii=False, indent=2)
    ricl_str = json.dumps(ricl_list, ensure_ascii=False, indent=2)

    existing_str = ""
    if existing_mapping:
        existing_str = f"\n\nMappatura già esistente (da NON ripetere, usa come contesto):\n{json.dumps(existing_mapping, ensure_ascii=False)}"

    prompt = f"""Sei un esperto di contabilità e controllo di gestione italiano.
Hai il compito di mappare i conti del Piano dei Conti aziendale alle voci dello Schema di Riclassificazione del Conto Economico.

PIANO DEI CONTI:
{piano_str}

SCHEMA DI RICLASSIFICAZIONE:
{ricl_str}
{existing_str}

ISTRUZIONI:
1. Per ogni conto del piano dei conti, individua la voce di riclassifica più appropriata
2. Basa la mappatura sulla natura economica del conto (ricavi, costi del personale, ammortamenti, ecc.)
3. Se un conto non è pertinente al CE (es. conti patrimoniali), assegna null
4. Rispondi SOLO con un oggetto JSON valido, niente altro
5. Formato: {{"codice_conto": "codice_voce_ricl", ...}}
6. Se lo schema usa codici numerici, usa quelli; se usa descrizioni, usa le descrizioni esatte

RISPOSTA (solo JSON):"""

    try:
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()

        # Estrai JSON anche se c'è testo attorno
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
        return {}

    except json.JSONDecodeError as e:
        raise ValueError(f"Risposta AI non valida come JSON: {e}")
    except Exception as e:
        raise ValueError(f"Errore chiamata AI: {e}")


def ai_suggest_new_accounts(df_piano_new, df_ricl, existing_mapping: dict) -> dict:
    """
    Suggerisce la mappatura solo per i conti nuovi (non già mappati).
    """
    # Filtra solo conti non ancora mappati
    from services.data_utils import find_column
    col_cod = find_column(df_piano_new, ['Codice', 'codice', 'codice conto', 'Codice Conto', 'Conto', 'conto'])
    if not col_cod:
        return {}

    nuovi = df_piano_new[~df_piano_new[col_cod].astype(str).isin(existing_mapping.keys())]
    if nuovi.empty:
        return {}

    return ai_suggest_mapping(nuovi, df_ricl, existing_mapping)
