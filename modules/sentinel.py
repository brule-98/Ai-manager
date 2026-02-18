import streamlit as st
import pandas as pd
from services.data_utils import get_cliente, fmt_eur, find_column
from services.riclassifica import costruisci_ce_riclassificato, get_mesi_disponibili


def _compute_alerts(cliente: dict) -> list:
    """
    Calcola gli alert di anomalia per un cliente.
    Returns lista di dict con: tipo, voce, mese, valore, valore_prec, variazione_pct, severita, spiegazione
    """
    df_db    = cliente.get('df_db')
    df_piano = cliente.get('df_piano')
    df_ricl  = cliente.get('df_ricl')
    mapping  = cliente.get('mapping', {})
    schema_config = cliente.get('schemi', {}).get(cliente.get('schema_attivo', ''), {})
    rettifiche = [r for r in cliente.get('rettifiche', []) if r.get('attiva', True)]
    sito = st.session_state.get('sito_attivo', 'Globale')

    profile = st.session_state.get('company_profile', {})
    soglia_warn = profile.get('soglia_warn', 15)
    soglia_crit = profile.get('soglia_crit', 30)

    if not all([df_db is not None, df_piano is not None, df_ricl is not None, mapping]):
        return []

    pivot, errore = costruisci_ce_riclassificato(
        df_db, df_piano, df_ricl, mapping, schema_config, rettifiche, sito
    )
    if errore or pivot is None:
        return []

    mesi = get_mesi_disponibili(pivot)
    if len(mesi) < 2:
        return []

    alerts = []
    for voce in pivot.index:
        for i in range(1, len(mesi)):
            m_prec = mesi[i - 1]
            m_curr = mesi[i]
            v_prec = float(pivot.loc[voce, m_prec])
            v_curr = float(pivot.loc[voce, m_curr])

            if v_prec == 0:
                continue

            var_pct = (v_curr - v_prec) / abs(v_prec) * 100
            abs_var = abs(var_pct)

            if abs_var < soglia_warn:
                continue

            # Determina severità e tipo
            if abs_var >= soglia_crit:
                severita = 'critical'
            else:
                severita = 'warning'

            # Determina se è positivo o negativo (dipende dalla natura della voce)
            is_ricavo = any(k in voce.lower() for k in ['ricav', 'fattur', 'vendite', 'revenue', 'margine'])
            is_costo  = any(k in voce.lower() for k in ['costo', 'spese', 'oneri', 'perdite'])

            se_positivo = (var_pct > 0 and is_ricavo) or (var_pct < 0 and is_costo)
            if se_positivo:
                severita = 'positive'

            spiegazione = _genera_spiegazione(voce, m_prec, m_curr, v_prec, v_curr, var_pct)

            alerts.append({
                'voce': voce,
                'mese_prec': m_prec,
                'mese_curr': m_curr,
                'valore_prec': v_prec,
                'valore_curr': v_curr,
                'variazione_pct': round(var_pct, 1),
                'variazione_abs': v_curr - v_prec,
                'severita': severita,
                'spiegazione': spiegazione,
            })

    # Ordina: critical prima, poi warning, poi positive
    ordine = {'critical': 0, 'warning': 1, 'positive': 2}
    alerts.sort(key=lambda a: (ordine.get(a['severita'], 3), -abs(a['variazione_pct'])))
    return alerts


def _genera_spiegazione(voce, m_prec, m_curr, v_prec, v_curr, var_pct) -> str:
    """Genera una spiegazione testuale dell'anomalia."""
    direzione = "aumentato" if var_pct > 0 else "diminuito"
    entita = "significativamente" if abs(var_pct) > 30 else "in modo rilevante"

    tpl = (
        f"La voce **{voce}** è {direzione} {entita} da {fmt_eur(v_prec)} ({m_prec}) "
        f"a {fmt_eur(v_curr)} ({m_curr}), con una variazione del **{var_pct:+.1f}%** "
        f"(delta: {fmt_eur(v_curr - v_prec, show_sign=True)})."
    )

    # Suggerimento contestuale
    if abs(var_pct) > 50:
        tpl += " ⚠️ Variazione molto alta: verifica se si tratta di dati corretti o di una rettifica necessaria."
    elif 'costo' in voce.lower() and var_pct > 20:
        tpl += " 💡 Analizza se l'incremento dei costi è strutturale o una tantum."
    elif 'ricav' in voce.lower() and var_pct < -15:
        tpl += " 💡 Calo dei ricavi: valuta cause commerciali o stagionalità."

    return tpl


def render_sentinel():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("⚠️ Seleziona un cliente dalla sidebar.")
        return

    cliente = get_cliente()

    st.markdown(f"## 🔔 Sentinel — Anomaly Detection · {ca}")
    st.markdown("""
    <div class="info-box info-box-blue">
    🛡️ Sentinel monitora il tuo CE e segnala automaticamente scostamenti anomali mese su mese.
    Le soglie di attenzione sono configurabili nel tuo <b>Profilo Aziendale</b>.
    </div>
    """, unsafe_allow_html=True)

    if cliente.get('df_db') is None:
        st.info("👋 Carica i dati nel Workspace per attivare Sentinel.")
        return

    if not cliente.get('mapping'):
        st.warning("⚠️ Configura la mappatura nel Workspace per abilitare Sentinel.")
        return

    # Soglie
    profile = st.session_state.get('company_profile', {})
    soglia_warn = profile.get('soglia_warn', 15)
    soglia_crit = profile.get('soglia_crit', 30)

    st.markdown(f"""
    <div style="display:flex; gap:12px; margin-bottom:1rem;">
        <span class="sentinel-badge badge-warn">⚡ Warning > {soglia_warn}%</span>
        <span class="sentinel-badge badge-crit">🚨 Critical > {soglia_crit}%</span>
        <span class="sentinel-badge badge-ok">✅ Positivo</span>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("📡 Sentinel in analisi..."):
        alerts = _compute_alerts(cliente)

    if not alerts:
        st.markdown("""
        <div class="info-box info-box-green">
        ✅ <b>Nessuna anomalia rilevata.</b> Tutti gli indicatori rientrano nelle soglie configurate.
        </div>
        """, unsafe_allow_html=True)
        return

    # Stats
    n_crit = sum(1 for a in alerts if a['severita'] == 'critical')
    n_warn = sum(1 for a in alerts if a['severita'] == 'warning')
    n_pos  = sum(1 for a in alerts if a['severita'] == 'positive')

    cols = st.columns(4)
    cols[0].metric("Alert Totali", len(alerts))
    cols[1].metric("🚨 Critical", n_crit, delta=None)
    cols[2].metric("⚡ Warning", n_warn)
    cols[3].metric("✅ Positivi", n_pos)

    st.markdown("---")

    # Filtro
    filtro_sev = st.multiselect(
        "Filtra per severità:",
        ["critical", "warning", "positive"],
        default=["critical", "warning"],
        format_func=lambda x: {"critical":"🚨 Critical","warning":"⚡ Warning","positive":"✅ Positivo"}.get(x, x),
        key="sent_filtro"
    )

    alerts_filt = [a for a in alerts if a['severita'] in filtro_sev] if filtro_sev else alerts

    # AI Enhancement
    tab_cards, tab_ai = st.tabs(["📋 Alert Cards", "🤖 Analisi AI Approfondita"])

    with tab_cards:
        for a in alerts_filt:
            _render_alert_card(a)

    with tab_ai:
        _render_ai_sentinel(alerts, cliente)


def _render_alert_card(a: dict):
    sev = a['severita']
    badge_css = {'critical': 'badge-crit', 'warning': 'badge-warn', 'positive': 'badge-ok'}.get(sev, 'badge-info')
    badge_label = {'critical': '🚨 CRITICAL', 'warning': '⚡ WARNING', 'positive': '✅ POSITIVO'}.get(sev, '')
    card_css = {'critical': 'sentinel-card critical', 'warning': 'sentinel-card', 'positive': 'sentinel-card positive'}.get(sev, 'sentinel-card')

    arrow = "▲" if a['variazione_pct'] > 0 else "▼"
    color_var = "#059669" if a['variazione_pct'] > 0 else "#DC2626"

    st.markdown(f"""
    <div class="{card_css}">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <div class="sentinel-title">{a['voce']}</div>
                <div class="sentinel-body" style="margin-top:6px;">{a['spiegazione']}</div>
            </div>
            <div style="text-align:right; flex-shrink:0; margin-left:16px;">
                <span class="sentinel-badge {badge_css}">{badge_label}</span>
                <div style="font-family:'JetBrains Mono',monospace; font-size:1.1rem; font-weight:700;
                            color:{color_var}; margin-top:6px;">
                    {arrow} {abs(a['variazione_pct']):.1f}%
                </div>
                <div style="font-size:0.72rem; color:#6B7280;">{a['mese_prec']} → {a['mese_curr']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Bottone link a rettifiche
    if st.button(f"✏️ Aggiungi rettifica per: {a['voce'][:40]}",
                  key=f"sent_rtt_{a['voce']}_{a['mese_curr']}"):
        st.session_state['page'] = 'Rettifiche'
        st.session_state['rettifica_precomp'] = {
            'conto': '', 'descrizione': f"Rettifica anomalia: {a['voce']} ({a['mese_curr']})"
        }
        st.rerun()


def _render_ai_sentinel(alerts: list, cliente: dict):
    """Analisi AI approfondita degli alert."""
    st.markdown("#### 🤖 Analisi Approfondita del CFO Digitale")
    st.markdown("""
    <div class="info-box info-box-blue">
    L'AI analizzerà tutti gli alert rilevati e produrrà un commento gestionale strutturato
    con cause probabili, impatti sul business e azioni raccomandate.
    </div>
    """, unsafe_allow_html=True)

    api_key = st.session_state.get('anthropic_api_key', '')
    if not api_key:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass

    if not api_key:
        st.warning("⚠️ Configura la API Key nel Workspace → API Key per abilitare l'analisi AI.")
        return

    if st.button("🤖 Genera Analisi AI degli Alert", type="primary", key="btn_ai_sentinel"):
        _esegui_analisi_ai_sentinel(alerts, cliente, api_key)


def _esegui_analisi_ai_sentinel(alerts, cliente, api_key):
    import anthropic, json

    profile = st.session_state.get('company_profile', {})
    ca = st.session_state.get('cliente_attivo', '')

    alert_summary = []
    for a in alerts[:10]:  # Max 10 alert
        alert_summary.append({
            'voce': a['voce'],
            'variazione_pct': a['variazione_pct'],
            'valore_prec': round(a['valore_prec'], 0),
            'valore_curr': round(a['valore_curr'], 0),
            'mese_prec': a['mese_prec'],
            'mese_curr': a['mese_curr'],
            'severita': a['severita']
        })

    prompt = f"""Sei un CFO esperto e controller di gestione italiano con 20 anni di esperienza.

CONTESTO AZIENDALE:
- Azienda: {profile.get('nome_azienda', ca)}
- Settore: {profile.get('settore', 'N/D')}
- Fatturato stimato: {profile.get('fascia_fatturato', 'N/D')}
- Dipendenti: {profile.get('dipendenti', 'N/D')}

ANOMALIE RILEVATE DAL SISTEMA SENTINEL:
{json.dumps(alert_summary, ensure_ascii=False, indent=2)}

COMPITO:
Analizza queste anomalie come farebbe un CFO esperto e produci:
1. **Sintesi Esecutiva** (2-3 righe): cosa sta succedendo nel complesso
2. **Analisi per ogni alert** (max 3 righe ciascuno): causa più probabile + impatto
3. **Top 3 Azioni Raccomandate**: cosa fare SUBITO
4. **Red Flag**: se c'è qualcosa che segnala un problema strutturale

Usa un tono professionale ma diretto. Sii specifico, non generico.
"""

    client = anthropic.Anthropic(api_key=api_key)

    with st.spinner("🤖 CFO Digitale in analisi..."):
        try:
            msg = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            risposta = msg.content[0].text

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(risposta)
            st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Errore analisi AI: {e}")
