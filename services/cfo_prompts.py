"""
services/cfo_prompts.py — Prompt ufficiali per il CFO Agent.
Include istruzioni di sistema e costruttori di prompt per analisi finanziarie.
"""

CFO_SYSTEM_PROMPT = """
Sei un Senior CFO Virtuale esperto in PMI italiane, con competenze da McKinsey, BCG e certificazione CFA.
Il tuo obiettivo è analizzare i dati contabili forniti e fornire insight strategici di alto livello.

REGOLE DI ANALISI:
1. Usa un tono professionale, autorevole ma costruttivo.
2. Focalizzati su EBITDA, Flusso di Cassa e Margini.
3. Identifica anomalie (scostamenti > 10% o variazioni inattese).
4. Fornisci raccomandazioni pratiche (es. 'ridurre i costi d07' o 'monitorare b01').
5. Usa i codici di riclassifica (a01, b11, c01, etc.) per riferirti alle voci, spiegandone il significato.
6. Se i dati sono insufficienti, chiedi chiarimenti specifici.
"""

def build_monthly_analysis_prompt(periodo, dati_ce, kpi):
    return f"""
    Esegui un'analisi mensile approfondita per il periodo {periodo}.
    
    DATI CONTO ECONOMICO (Riclassificato):
    {dati_ce}
    
    KPI CALCOLATI:
    {kpi}
    
    Richiesta:
    - Commenta l'andamento del fatturato (a01) e dei margini.
    - Analizza l'incidenza del costo del venduto (b01-b05) e del personale (c01-c04).
    - Evidenzia eventuali criticita nella gestione PDV (d01-d10).
    - Proponi 3 azioni prioritarie per il prossimo mese.
    """

def build_weekly_flash_prompt(dati_recenti):
    return f"""
    Genera un report 'Flash' settimanale basato sugli ultimi movimenti:
    {dati_recenti}
    
    Fornisci un commento rapido (massimo 150 parole) sui trend più immediati.
    """

def build_budget_variance_prompt(scostamenti):
    return f"""
    Analizza gli scostamenti tra Budget ed Effettivo:
    {scostamenti}
    
    Spiega le cause probabili degli scostamenti negativi e suggerisci correttivi.
    """

# Aggiungi altre funzioni se richiamate in cfo_agent.py
def build_custom_query_prompt(query, contesto):
    return f"""
    L'utente ha chiesto: "{query}"
    
    Contesto finanziario attuale:
    {contesto}
    
    Rispondi in modo tecnico e preciso.
    """
