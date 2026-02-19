"""
ai_mapper.py — Mappatura automatica dei conti contabili con Claude AI.
Usa claude-opus-4-6 per analisi semantica del piano dei conti.
"""
import json
import anthropic
from services.data_utils import find_column, get_api_key


def ai_suggest_mapping(df_piano, df_ricl, existing_mapping: dict = None) -> dict:
    """
    Mappa TUTTI i conti del piano dei conti alle voci dello schema di riclassifica.
    Usa Claude claude-opus-4-6 con prompt specializzato per contabilità italiana.

    Returns: {codice_conto: codice_voce_ricl}
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("API Key Anthropic non configurata. Vai in Workspace → API Key.")

    client = anthropic.Anthropic(api_key=api_key)

    col_cod_piano  = find_column(df_piano, ['Codice','codice','CodConto','Conto','conto','ID'])
    col_desc_piano = find_column(df_piano, ['Descrizione','descrizione','Nome','nome','Conto','conto'])
    col_cod_ricl   = find_column(df_ricl,  ['Codice','codice','ID','id','Voce','voce'])
    col_desc_ricl  = find_column(df_ricl,  ['Descrizione','descrizione','Nome','nome','Voce','voce'])

    if not col_cod_piano or not col_cod_ricl:
        raise ValueError("Colonne chiave non trovate nei file caricati.")

    # Prepara piano dei conti (max 300 conti)
    piano_list = []
    for _, row in df_piano.head(300).iterrows():
        entry = {'codice': str(row[col_cod_piano]).strip()}
        if col_desc_piano and col_desc_piano != col_cod_piano:
            entry['descrizione'] = str(row[col_desc_piano]).strip()
        piano_list.append(entry)

    # Prepara schema riclassifica
    ricl_list = []
    for _, row in df_ricl.iterrows():
        entry = {'codice': str(row[col_cod_ricl]).strip()}
        if col_desc_ricl and col_desc_ricl != col_cod_ricl:
            entry['descrizione'] = str(row[col_desc_ricl]).strip()
        ricl_list.append(entry)

    existing_str = ""
    if existing_mapping:
        n = len(existing_mapping)
        existing_str = f"\n\nMappatura già esistente ({n} conti): " + json.dumps(
            dict(list(existing_mapping.items())[:30]), ensure_ascii=False
        ) + ("..." if n > 30 else "")

    prompt = f"""Sei un esperto dottore commercialista italiano con 20 anni di esperienza in controllo di gestione.

Il tuo compito è mappare ogni conto del Piano dei Conti alla voce più appropriata dello Schema di Riclassificazione CE.

PIANO DEI CONTI DA MAPPARE:
{json.dumps(piano_list, ensure_ascii=False, indent=2)}

SCHEMA DI RICLASSIFICAZIONE DISPONIBILE:
{json.dumps(ricl_list, ensure_ascii=False, indent=2)}
{existing_str}

REGOLE DI MAPPATURA:
1. Associa ogni conto CE (ricavi, costi, proventi/oneri finanziari) alla voce più specifica disponibile
2. I conti PATRIMONIALI (cassa, banche, crediti, debiti, immobilizzazioni, patrimonio netto) → null (non appartengono al CE)
3. Usa il CODICE del conto riclassificato (prima colonna dello schema), NON la descrizione
4. Se non trovi una voce adatta → null
5. Considera la struttura tipica italiana: Conti 3/4/5/6/7/8/9 = CE; Conti 1/2 = Patrimoniale
6. Analizza sia il codice che la descrizione per capire la natura del conto

RISPOSTA: JSON puro, niente testo aggiuntivo, niente markdown:
{{"codice_conto_1": "codice_voce_ricl_o_null", "codice_conto_2": "codice_voce_ricl_o_null", ...}}"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # Estrai JSON
    start = raw.find('{')
    end   = raw.rfind('}') + 1
    if start < 0 or end <= start:
        raise ValueError(f"Risposta AI non valida: {raw[:200]}")

    result = json.loads(raw[start:end])
    # Filtra i null
    return {k: v for k, v in result.items() if v and str(v).lower() not in ('null','none','')}


def ai_suggest_new_accounts(df_piano, df_ricl, existing_mapping: dict) -> dict:
    """Suggerisce mappatura solo per i conti nuovi non ancora mappati."""
    col_cod = find_column(df_piano, ['Codice','codice','CodConto','Conto','conto','ID'])
    if not col_cod:
        return {}
    nuovi = df_piano[~df_piano[col_cod].astype(str).str.strip().isin(existing_mapping.keys())]
    if nuovi.empty:
        return {}
    return ai_suggest_mapping(nuovi, df_ricl, existing_mapping)
