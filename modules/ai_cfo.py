import streamlit as st
import json
import anthropic
from services.data_utils import get_cliente, fmt_eur, find_column
from services.riclassifica import costruisci_ce_riclassificato, get_mesi_disponibili


def render_ai_cfo():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("⚠️ Seleziona un cliente dalla sidebar.")
        return

    cliente = get_cliente()
    profile = st.session_state.get('company_profile', {})

    st.markdown(f"## 🤖 AI CFO — Assistente Strategico · {ca}")
    st.markdown("""
    <div class="info-box info-box-blue">
    🧠 Il <b>CFO Digitale</b> combina i tuoi dati contabili con il contesto aziendale per produrre
    analisi strategiche, identificare il breakeven, commentare la marginalità e fornire
    intelligence di mercato sui tuoi competitor.
    </div>
    """, unsafe_allow_html=True)

    api_key = st.session_state.get('anthropic_api_key', '')
    if not api_key:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass

    if not api_key:
        st.warning("⚠️ Configura la API Key Anthropic nel Workspace → API Key.")
        return

    tab1, tab2, tab3 = st.tabs([
        "📊 Analisi CE & Breakeven", "🏆 Market Intelligence", "💬 Chat CFO"
    ])

    with tab1:
        _render_analisi_interna(ca, cliente, profile, api_key)

    with tab2:
        _render_market_intelligence(profile, api_key)

    with tab3:
        _render_chat_cfo(ca, cliente, profile, api_key)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: ANALISI INTERNA
# ══════════════════════════════════════════════════════════════════════════════
def _render_analisi_interna(ca, cliente, profile, api_key):
    st.markdown("### Analisi CE, Breakeven e Marginalità")

    df_db    = cliente.get('df_db')
    df_piano = cliente.get('df_piano')
    df_ricl  = cliente.get('df_ricl')
    mapping  = cliente.get('mapping', {})
    schema_config = cliente.get('schemi', {}).get(cliente.get('schema_attivo', ''), {})
    rettifiche = [r for r in cliente.get('rettifiche', []) if r.get('attiva', True)]

    if not all([df_db is not None, df_piano is not None, df_ricl is not None, mapping]):
        st.warning("Completa il caricamento dati e la mappatura nel Workspace.")
        return

    pivot, errore = costruisci_ce_riclassificato(
        df_db, df_piano, df_ricl, mapping, schema_config, rettifiche
    )
    if errore or pivot is None:
        st.error(f"Impossibile costruire il CE: {errore}")
        return

    mesi = get_mesi_disponibili(pivot)

    # Selezione periodo
    c1, c2 = st.columns(2)
    with c1:
        if mesi:
            mesi_sel = st.multiselect("Periodo di analisi:", mesi, default=mesi[-6:], key="cfo_mesi")
        else:
            mesi_sel = []
    with c2:
        tipo_analisi = st.multiselect("Tipo di analisi:", [
            "Commento CE e trend",
            "Calcolo Breakeven Point",
            "Analisi marginalità",
            "Struttura costi fissi/variabili",
            "Indicatori di allerta precoce",
        ], default=["Commento CE e trend", "Calcolo Breakeven Point"], key="cfo_tipo")

    if not mesi_sel:
        st.info("Seleziona almeno un mese.")
        return

    cols_sel = [c for c in mesi_sel if c in pivot.columns]
    if not cols_sel:
        return

    pivot_period = pivot[cols_sel].copy()
    pivot_period['TOTALE'] = pivot_period.sum(axis=1)

    # Preview dati
    with st.expander("📋 Dati CE inviati all'AI"):
        st.dataframe(pivot_period.style.format("{:,.0f} €"), use_container_width=True)

    if st.button("🤖 Genera Analisi CFO", type="primary", key="btn_cfo_analisi"):
        _esegui_analisi_ce(pivot_period, profile, ca, tipo_analisi, api_key)


def _esegui_analisi_ce(pivot, profile, ca, tipo_analisi, api_key):
    """Chiama Claude per analisi CE."""
    # Prepara dati CE come testo strutturato
    ce_rows = []
    for voce in pivot.index:
        ce_rows.append({
            'voce': voce,
            'totale_periodo': round(float(pivot.loc[voce, 'TOTALE']), 0),
        })

    prompt = f"""Sei un CFO esperto e ingegnere gestionale italiano di alto livello.

PROFILO AZIENDALE:
- Azienda: {profile.get('nome_azienda', ca)}
- Settore: {profile.get('settore', 'N/D')}
- Fascia fatturato: {profile.get('fascia_fatturato', 'N/D')}
- Dipendenti: {profile.get('dipendenti', 'N/D')}
- Descrizione: {profile.get('descrizione', 'N/D')}
- Anni di attività: {profile.get('anni_attivita', 'N/D')}

CONTO ECONOMICO RICLASSIFICATO (periodo analizzato):
{json.dumps(ce_rows, ensure_ascii=False, indent=2)}

ANALISI RICHIESTE: {', '.join(tipo_analisi)}

Per ogni analisi richiesta, produci:
{"- **Commento CE**: Analisi narrativa del CE, trend principali, performance per area" if "Commento CE e trend" in tipo_analisi else ""}
{"- **Breakeven Point**: Calcola o stima il BEP identificando costi fissi, variabili e margine contribuzione" if "Calcolo Breakeven Point" in tipo_analisi else ""}
{"- **Marginalità**: Analisi del margine lordo, EBITDA margin, EBIT margin con benchmark settoriale" if "Analisi marginalità" in tipo_analisi else ""}
{"- **Struttura costi**: Identifica i principali centri di costo e la loro incidenza" if "Struttura costi fissi/variabili" in tipo_analisi else ""}
{"- **Early Warning**: Segnala fino a 5 indicatori che richiedono attenzione immediata" if "Indicatori di allerta precoce" in tipo_analisi else ""}

Usa un tono professionale da CFO senior. Sii quantitativo dove possibile.
Fornisci benchmark di settore realistici per il settore indicato.
Concludi sempre con 3 raccomandazioni strategiche concrete e azionabili.
"""

    client = anthropic.Anthropic(api_key=api_key)
    with st.spinner("🤖 CFO Digitale in elaborazione... 20-40 secondi"):
        try:
            msg = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            risposta = msg.content[0].text

            st.markdown("---")
            st.markdown(f"""
            <div class="card">
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:1rem;">
                    <div class="chat-avatar chat-avatar-ai">🤖</div>
                    <div>
                        <div style="font-weight:600; color:#0F2044;">CFO Digitale AI-Manager</div>
                        <div style="font-size:0.72rem; color:#6B7280;">Analisi basata su dati reali</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown(risposta)
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Errore: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: MARKET INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════
def _render_market_intelligence(profile, api_key):
    st.markdown("### Market Intelligence & Benchmark Competitor")
    st.markdown("""
    <div class="info-box info-box-amber">
    🌐 Il CFO Digitale utilizza il profilo aziendale per generare una simulazione di analisi
    di mercato e benchmark competitivo basato su dati di settore e tendenze aggiornate.
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        focus_market = st.multiselect("Focus dell'analisi:", [
            "Trend di settore e crescita mercato",
            "Benchmark KPI finanziari di settore",
            "Analisi competitor principali",
            "Opportunità e minacce (SWOT)",
            "Scenari macroeconomici rilevanti",
        ], default=["Benchmark KPI finanziari di settore", "Trend di settore e crescita mercato"],
        key="mi_focus")
    with c2:
        sito_web = st.text_input("Sito web aziendale (opzionale):",
                                  value=profile.get('sito_web', ''),
                                  placeholder="https://www.azienda.it",
                                  key="mi_sito")
        info_extra = st.text_area("Info aggiuntive per l'AI:", height=60,
                                   placeholder="Es: vendiamo principalmente in nord Italia, target PMI...",
                                   key="mi_extra")

    if st.button("🌐 Genera Market Intelligence", type="primary", key="btn_mi"):
        if not profile.get('settore'):
            st.warning("Completa il profilo aziendale (Settore ATECO) per un'analisi più accurata.")

        _esegui_market_intelligence(profile, sito_web, info_extra, focus_market, api_key)


def _esegui_market_intelligence(profile, sito_web, info_extra, focus, api_key):
    prompt = f"""Sei un analista di mercato e strategist aziendale italiano di alto livello.
Hai accesso a dati di mercato aggiornati e conosci in profondità il tessuto imprenditoriale italiano.

PROFILO AZIENDA:
- Nome: {profile.get('nome_azienda', 'N/D')}
- Settore: {profile.get('settore', 'N/D')}
- Fatturato: {profile.get('fascia_fatturato', 'N/D')}
- Dipendenti: {profile.get('dipendenti', 'N/D')}
- Descrizione: {profile.get('descrizione', 'N/D')}
- Sito web: {sito_web or 'N/D'}
- Note aggiuntive: {info_extra or 'N/D'}

ANALISI RICHIESTE: {', '.join(focus)}

Produci un report di Market Intelligence professionale che includa:

{"**📈 TREND DI SETTORE**: Analisi delle principali tendenze del mercato di riferimento negli ultimi 12-24 mesi e prospettive 2025-2026" if "Trend di settore e crescita mercato" in focus else ""}

{"**📊 BENCHMARK KPI**: Valori tipici di mercato per EBITDA margin, EBIT margin, ROE, leverage per aziende simili nel settore indicato. Fornisci range realistici per PMI italiane" if "Benchmark KPI finanziari di settore" in focus else ""}

{"**🏆 COMPETITOR LANDSCAPE**: Identifica le categorie di competitor principali (non nomi specifici se non certi), i loro punti di forza e strategie comuni nel settore" if "Analisi competitor principali" in focus else ""}

{"**⚡ SWOT DI SETTORE**: Opportunità e minacce tipiche per le aziende di questo settore/dimensione oggi" if "Opportunità e minacce (SWOT)" in focus else ""}

{"**🌍 MACRO SCENARI**: Fattori macroeconomici rilevanti (tassi, inflazione, normative) che impattano questo settore" if "Scenari macroeconomici rilevanti" in focus else ""}

Concludi con **3 raccomandazioni strategiche** specifiche per un'azienda con questo profilo.

Sii concreto e basato su dinamiche reali del mercato italiano/europeo.
Cita trend realistici con dati indicativi (% crescita, range di margini, ecc.).
"""

    client = anthropic.Anthropic(api_key=api_key)
    with st.spinner("🌐 Analisi di mercato in corso..."):
        try:
            msg = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=3500,
                messages=[{"role": "user", "content": prompt}]
            )
            risposta = msg.content[0].text

            st.markdown("---")
            st.markdown(f"""
            <div class="card">
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:1rem;">
                    <div class="chat-avatar chat-avatar-ai">🌐</div>
                    <div>
                        <div style="font-weight:600; color:#0F2044;">Market Intelligence — CFO Digitale</div>
                        <div style="font-size:0.72rem; color:#6B7280;">
                            Analisi settoriale: {profile.get('settore', 'N/D')}
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown(risposta)
            st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Errore: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: CHAT CFO
# ══════════════════════════════════════════════════════════════════════════════
def _render_chat_cfo(ca, cliente, profile, api_key):
    st.markdown("### 💬 Chat con il CFO Digitale")
    st.markdown("""
    <div class="info-box info-box-blue">
    Fai domande libere al tuo CFO Digitale. Conosce i tuoi dati contabili e il tuo profilo aziendale.
    </div>
    """, unsafe_allow_html=True)

    # Inizializza chat history
    if 'cfo_chat_history' not in st.session_state:
        st.session_state['cfo_chat_history'] = []

    # Mostra storico chat
    for msg in st.session_state['cfo_chat_history']:
        is_user = msg['role'] == 'user'
        avatar_css = "chat-avatar-user" if is_user else "chat-avatar-ai"
        bubble_css = "chat-bubble chat-bubble-user" if is_user else "chat-bubble"
        avatar_icon = "👤" if is_user else "🤖"

        st.markdown(f"""
        <div class="chat-message" style="{'flex-direction:row-reverse;' if is_user else ''}">
            <div class="chat-avatar {avatar_css}">{avatar_icon}</div>
            <div>
                <div class="{bubble_css}">{msg['content']}</div>
                <div class="chat-time" style="{'text-align:right;' if is_user else ''}">{msg.get('time', '')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Input
    st.markdown("---")
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        domanda = st.text_input(
            "Domanda al CFO:",
            placeholder="Es: Qual è il breakeven? Perché i costi sono aumentati? Come mi confronto con il settore?",
            key="cfo_chat_input",
            label_visibility="collapsed"
        )
    with col_btn:
        invia = st.button("Invia →", key="btn_chat_invia", use_container_width=True)

    # Domande suggerite
    suggerimenti = [
        "Qual è il mio breakeven point attuale?",
        "Come migliorare il margine EBITDA?",
        "Quali sono i principali rischi finanziari?",
        "Come ottimizzare la struttura dei costi?",
    ]
    st.markdown("**Domande rapide:**")
    cols_s = st.columns(4)
    for i, sug in enumerate(suggerimenti):
        with cols_s[i]:
            if st.button(sug[:30] + "...", key=f"sug_{i}", use_container_width=True):
                domanda = sug
                invia = True

    if invia and domanda.strip():
        _invia_chat_cfo(domanda.strip(), ca, cliente, profile, api_key)

    if st.session_state['cfo_chat_history']:
        if st.button("🗑️ Cancella conversazione", key="btn_clear_chat"):
            st.session_state['cfo_chat_history'] = []
            st.rerun()


def _invia_chat_cfo(domanda, ca, cliente, profile, api_key):
    """Invia una domanda al CFO con contesto completo."""
    from datetime import datetime

    # Costruisci contesto CE sintetico
    ce_context = ""
    df_db    = cliente.get('df_db')
    df_piano = cliente.get('df_piano')
    df_ricl  = cliente.get('df_ricl')
    mapping  = cliente.get('mapping', {})
    schema_config = cliente.get('schemi', {}).get(cliente.get('schema_attivo', ''), {})
    rettifiche = [r for r in cliente.get('rettifiche', []) if r.get('attiva', True)]

    if all([df_db is not None, df_piano is not None, df_ricl is not None, mapping]):
        pivot, _ = costruisci_ce_riclassificato(
            df_db, df_piano, df_ricl, mapping, schema_config, rettifiche
        )
        if pivot is not None:
            totali = {voce: round(float(pivot.loc[voce, 'TOTALE']), 0)
                      for voce in pivot.index}
            ce_context = f"\nCE RICLASSIFICATO (TOTALI):\n{json.dumps(totali, ensure_ascii=False)}\n"

    # Sistema prompt
    system_prompt = f"""Sei il CFO Digitale di AI-Manager, un esperto controller di gestione e CFO italiano.

PROFILO CLIENTE:
- Azienda: {profile.get('nome_azienda', ca)}
- Settore: {profile.get('settore', 'N/D')}  
- Fatturato: {profile.get('fascia_fatturato', 'N/D')}
- Dipendenti: {profile.get('dipendenti', 'N/D')}
{ce_context}

STORICO CONVERSAZIONE (per contesto):
{_format_history(st.session_state.get('cfo_chat_history', [])[-6:])}

Rispondi come un CFO senior: preciso, quantitativo, diretto.
Usa markdown per strutturare le risposte. Sii conciso ma completo.
Quando non hai dati certi, indica le assunzioni che stai facendo.
"""

    messages = [{"role": "user", "content": domanda}]

    timestamp = datetime.now().strftime("%H:%M")
    st.session_state['cfo_chat_history'].append({
        'role': 'user', 'content': domanda, 'time': timestamp
    })

    client = anthropic.Anthropic(api_key=api_key)
    with st.spinner("🤖 CFO in risposta..."):
        try:
            msg = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1500,
                system=system_prompt,
                messages=messages
            )
            risposta = msg.content[0].text
            st.session_state['cfo_chat_history'].append({
                'role': 'assistant', 'content': risposta, 'time': timestamp
            })
            st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")


def _format_history(history: list) -> str:
    if not history:
        return "Nessuna conversazione precedente."
    lines = []
    for m in history:
        role = "Utente" if m['role'] == 'user' else "CFO"
        lines.append(f"{role}: {m['content'][:200]}")
    return "\n".join(lines)
