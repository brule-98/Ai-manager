"""
cfo_agent.py — SUPER AGENTE CFO AI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il CFO virtuale più avanzato per PMI italiane.
Powered by Claude Opus 4 | Framework McKinsey·BCG·HBS·CIMA·CFA

Features:
  ● KPI Dashboard automatica con visual analytics
  ● EBITDA Bridge interattivo (Plotly waterfall)
  ● DuPont Decomposition visual
  ● Chat streaming con contesto finanziario completo
  ● Generazione report: Mensile · Flash · Board · Budget Variance · Cash Flow
  ● Rilevamento anomalie statistiche (2σ) + AI deep analysis
  ● Market Intelligence con web search live
  ● Delivery email diretta al cliente
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import streamlit as st
import anthropic
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from services.data_utils import get_cliente, save_cliente, get_api_key, fmt_eur, fmt_pct, fmt_k
from services.riclassifica import (
    costruisci_ce_riclassificato, get_mesi_disponibili,
    calcola_kpi_finanziari, calcola_trend, calcola_statistiche_mensili
)
from services.report_generator import (
    format_ce_for_prompt, format_kpi_for_prompt,
    format_budget_variance_for_prompt, wrap_report
)
from services.cfo_prompts import (
    CFO_SYSTEM_PROMPT,
    build_monthly_analysis_prompt, build_weekly_flash_prompt,
    build_market_context_prompt, build_budget_variance_prompt,
    build_board_summary_prompt, build_anomaly_detection_prompt,
    build_cashflow_prompt, build_chat_context
)
from services.email_service import (
    send_report_email, build_email_body, validate_smtp_config, PROVIDER_PRESETS
)


# ─── PALETTE ─────────────────────────────────────────────────────────────────
C = {
    'gold':   '#C9A84C', 'gold_l': '#E8C96A',
    'navy':   '#0A1220', 'blue':   '#1E3A6E',
    'green':  '#10B981', 'red':    '#EF4444',
    'amber':  '#F59E0B', 'violet': '#8B5CF6',
    'text':   '#E2E8F0', 'muted':  '#64748B',
    'surf':   '#0F1923', 'surf2':  '#152030',
    'border': 'rgba(255,255,255,0.06)',
}

PLOTLY_THEME = dict(
    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Inter, -apple-system, sans-serif', color='#94A3B8', size=11),
    legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor='rgba(255,255,255,0.06)',
                orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
    margin=dict(l=0, r=0, t=40, b=0),
    hoverlabel=dict(bgcolor='#0F1923', bordercolor='#C9A84C', font_color='#E2E8F0'),
)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def render_cfo_agent():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        _page_no_cliente(); return

    cliente = get_cliente()
    if not cliente:
        _page_no_cliente(); return

    _inject_cfo_css()
    _header_cfo(ca)

    df_db    = cliente.get('df_db')
    df_piano = cliente.get('df_piano')
    df_ricl  = cliente.get('df_ricl')
    mapping  = cliente.get('mapping', {})

    if df_db is None or not mapping:
        _prereq_card(df_piano, df_db, df_ricl, mapping)
        return

    schema_att = cliente.get('schema_attivo', '')
    schema_cfg = cliente.get('schemi', {}).get(schema_att, {})
    rettifiche = cliente.get('rettifiche', [])
    budget     = cliente.get('budget', {})

    with st.spinner("⚙️ Elaborazione dati finanziari in corso…"):
        pivot, dettaglio, errore = costruisci_ce_riclassificato(
            df_db, df_piano, df_ricl, mapping, schema_cfg, rettifiche
        )

    if errore:
        st.error(f"❌ {errore}"); return

    mesi = get_mesi_disponibili(pivot)
    if not mesi:
        st.warning("⚠️ Nessun dato mensile trovato nel DB contabile."); return

    # ── AUTO KPI DASHBOARD ────────────────────────────────────────────────────
    _render_auto_kpi_dashboard(pivot, mesi, budget, ca)

    st.markdown("<hr style='border-color:rgba(201,168,76,0.12);margin:24px 0'>", unsafe_allow_html=True)

    # ── NAVIGATION TABS ───────────────────────────────────────────────────────
    tab_chat, tab_analytics, tab_report, tab_anomalie, tab_market, tab_email, tab_settings = st.tabs([
        "💬 Chat CFO",
        "📊 Visual Analytics",
        "📋 Genera Report",
        "🔍 Anomalie & Alert",
        "🌍 Market Intel",
        "📧 Email & Delivery",
        "⚙️ Settings",
    ])

    with tab_chat:
        _render_chat(ca, cliente, pivot, mesi, budget)

    with tab_analytics:
        _render_visual_analytics(pivot, mesi, budget)

    with tab_report:
        _render_report_gen(ca, cliente, pivot, mesi, budget)

    with tab_anomalie:
        _render_anomalie(ca, cliente, pivot, mesi, budget)

    with tab_market:
        _render_market_intel(ca, cliente, mesi)

    with tab_email:
        _render_email_tab(cliente, ca)

    with tab_settings:
        _render_settings(cliente, ca)


# ─────────────────────────────────────────────────────────────────────────────
# AUTO KPI DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def _render_auto_kpi_dashboard(pivot, mesi, budget, ca):
    """Dashboard KPI automatica visuale — si carica sempre all'apertura."""
    # Selettore periodo rapido
    c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
    with c1:
        mode = st.selectbox("Periodo:", ["Ultimo mese", "Ultimi 3 mesi", "Ultimi 6 mesi", "YTD", "Anno completo"],
                             key="kpi_dash_mode", label_visibility="collapsed")
    with c2:
        anni = sorted(set(m[:4] for m in mesi), reverse=True)
        if mode in ["YTD", "Anno completo"]:
            anno = st.selectbox("Anno:", anni, key="kpi_anno", label_visibility="collapsed")
        else:
            anno = anni[0] if anni else None
    with c3:
        anno_conf = st.selectbox("vs:", ["— nessun confronto —"] + anni, key="kpi_conf_anno", label_visibility="collapsed")
    with c4:
        show_budget_kpi = st.checkbox("Budget", value=bool(budget), key="kpi_show_bud")

    # Calcola mesi periodo
    if mode == "Ultimo mese":
        mesi_sel = [mesi[-1]]
    elif mode == "Ultimi 3 mesi":
        mesi_sel = mesi[-3:]
    elif mode == "Ultimi 6 mesi":
        mesi_sel = mesi[-6:]
    elif mode == "YTD":
        mesi_sel = [m for m in mesi if m.startswith(str(anno))]
    else:  # Anno completo
        mesi_sel = [m for m in mesi if m.startswith(str(anno))]

    cols_sel = [c for c in mesi_sel if c in pivot.columns]
    if not cols_sel:
        st.warning("Nessun dato per il periodo.")
        return

    kpi = calcola_kpi_finanziari(pivot, cols_sel)

    # Confronto
    kpi_conf = {}
    if anno_conf != "— nessun confronto —":
        mesi_num = {m[5:] for m in mesi_sel}
        cols_conf = [c for c in pivot.columns if c[:4] == anno_conf and c[5:] in mesi_num]
        if cols_conf:
            kpi_conf = calcola_kpi_finanziari(pivot, cols_conf)

    # Budget period
    bud_kpi = {}
    if show_budget_kpi and budget:
        for voce, vals in budget.items():
            bud_kpi[voce] = sum(vals.get(m, 0) for m in mesi_sel)

    # ── KPI CARDS ─────────────────────────────────────────────────────────────
    def kpi_card(label, value, unit, color, icon, conf_val=None, bud_val=None, benchmark=None):
        if value is None:
            return f"""<div class='cfo-kpi-card' style='border-top-color:{color}'>
                <div class='cfo-kpi-label'>{icon} {label}</div>
                <div class='cfo-kpi-value' style='color:{C["muted"]}'>—</div>
            </div>"""

        v_fmt = f"{value:.1f}{unit}" if unit == '%' else fmt_k(value) + " " + unit
        delta_html = ""
        if conf_val is not None and conf_val != 0:
            delta_pct = (value - conf_val) / abs(conf_val) * 100
            clr = C['green'] if delta_pct >= 0 else C['red']
            sym = "▲" if delta_pct >= 0 else "▼"
            delta_html = f"<div class='cfo-kpi-delta' style='color:{clr}'>{sym} {abs(delta_pct):.1f}% vs {anno_conf}</div>"
        bud_html = ""
        if bud_val and bud_val != 0 and unit != '%':
            scost = value - bud_val
            clr = C['green'] if scost >= 0 else C['red']
            sym = "+" if scost >= 0 else ""
            bud_html = f"<div class='cfo-kpi-bud' style='color:{clr}'>vs Budget: {sym}{fmt_k(scost)}€</div>"
        bench_html = f"<div class='cfo-kpi-bench'>Benchmark: {benchmark}</div>" if benchmark else ""

        return f"""<div class='cfo-kpi-card' style='border-top-color:{color}'>
            <div class='cfo-kpi-label'>{icon} {label}</div>
            <div class='cfo-kpi-value'>{v_fmt}</div>
            {delta_html}{bud_html}{bench_html}
        </div>"""

    kpi_defs = [
        ('Ricavi Netti',    kpi.get('ricavi'),        '€',  C['blue'],  '📈', kpi_conf.get('ricavi'),        None,                      None),
        ('EBITDA / MOL',   kpi.get('ebitda'),        '€',  C['green'], '💹', kpi_conf.get('ebitda'),        None,                      None),
        ('EBITDA Margin',  kpi.get('ebitda_margin'), '%',  '#3B82F6',  '📊', kpi_conf.get('ebitda_margin'),  None,                      '8-18% PMI'),
        ('Utile Netto',    kpi.get('utile_netto'),   '€',  C['gold'],  '🏆', kpi_conf.get('utile_netto'),   None,                      None),
        ('Net Margin',     kpi.get('net_margin'),    '%',  C['amber'], '📉', kpi_conf.get('net_margin'),    None,                      '3-8% PMI'),
        ('% Personale',    kpi.get('cost_labor_pct'),'%',  C['red'],   '👥', kpi_conf.get('cost_labor_pct'), None,                      '<35% target'),
    ]

    col_per_row = 3
    rows = [kpi_defs[i:i+col_per_row] for i in range(0, len(kpi_defs), col_per_row)]

    for row in rows:
        cards_html = "".join(kpi_card(*d) for d in row)
        st.markdown(f"<div class='cfo-kpi-row'>{cards_html}</div>", unsafe_allow_html=True)

    # ── MINI SPARK CHARTS ─────────────────────────────────────────────────────
    voci_spark = [v for v in [
        kpi.get('_voci', {}).get('ricavi'),
        kpi.get('_voci', {}).get('ebitda'),
        kpi.get('_voci', {}).get('utile_netto'),
    ] if v and v in pivot.index]

    if voci_spark and len(mesi) >= 3:
        all_mesi_plot = mesi[-min(12, len(mesi)):]
        fig = go.Figure()
        colors_spark = [C['blue'], C['green'], C['gold']]
        for i, voce in enumerate(voci_spark[:3]):
            vals = [float(pivot.loc[voce, m]) if m in pivot.columns else 0 for m in all_mesi_plot]
            fig.add_trace(go.Scatter(
                x=all_mesi_plot, y=vals, name=str(voce)[:25],
                mode='lines', line=dict(color=colors_spark[i], width=2),
                fill='tozeroy',
                fillcolor=f"rgba({','.join(str(int(colors_spark[i].lstrip('#')[j:j+2], 16)) for j in (0,2,4))}, 0.06)",
                hovertemplate=f'<b>{str(voce)[:25]}</b><br>%{{x}}: %{{y:,.0f}} €<extra></extra>'
            ))

        fig.update_layout(
            **PLOTLY_THEME, height=200,
            xaxis=dict(showgrid=False, tickfont=dict(size=10), color='#475569',
                       tickangle=-30, title=''),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.04)',
                       tickformat=',.0f', ticksuffix='€', tickfont=dict(size=10), color='#475569'),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — CHAT CFO
# ─────────────────────────────────────────────────────────────────────────────

def _render_chat(ca, cliente, pivot, mesi, budget):
    if 'cfo_chat_history' not in st.session_state:
        st.session_state['cfo_chat_history'] = []

    cfo_cfg = cliente.get('cfo_settings', {})
    settore = cfo_cfg.get('settore', '')
    note_az = cfo_cfg.get('note_azienda', '')

    # ── Prompt rapidi ────────────────────────────────────────────────────────
    st.markdown(f"<div style='font-size:0.72rem;text-transform:uppercase;letter-spacing:2px;color:{C['gold']};font-weight:700;margin-bottom:12px'>⚡ ANALISI RAPIDA</div>", unsafe_allow_html=True)

    quick_prompts = [
        ("📊 EBITDA Bridge",    "Costruisci l'EBITDA Bridge completo per il periodo più recente: decomponi la variazione in Volume, Prezzo/Mix, Efficienza costi, One-off. Quantifica ogni componente in € e %. Identifica il driver principale."),
        ("⚠️ Top 3 Rischi",    "Analizza i 3 rischi finanziari più critici emergenti dai dati. Per ognuno: probabilità (Alta/Media/Bassa), impatto stimato in €, segnali premonitori nei numeri, azione di mitigazione concreta."),
        ("💡 Leve Redditività", "Identifica le top 3 leve per migliorare l'EBITDA margin. Per ognuna: impatto € stimato, fattibilità, tempo di realizzazione, rischi. Usa la struttura: Leva → Driver → Azione → Impatto → Timeline."),
        ("🎯 Outlook Q+1",      "Proiezione per il prossimo trimestre nei 3 scenari (Bear 25%, Base 50%, Bull 25%). Per ogni scenario: assunzione chiave, EBITDA stimato, Revenue, Net Margin. Cosa devo monitorare ogni settimana?"),
        ("💰 Cash Flow",       "Analisi della generazione di cassa partendo dall'EBITDA. Stima FCF = EBITDA − Capex stimato ± ΔWorking Capital. Dove si congela o si libera cassa? CCC stimato e ottimizzazione possibile."),
        ("🏦 DuPont Analysis", "Esegui la decomposizione DuPont completa: ROE = Net Margin × Asset Turnover × Leverage. Dove si crea valore? Confronto vs benchmark settore. ROIC vs costo stimato del capitale (WACC ~9%)."),
        ("📈 Crescita ricavi", "Analizza il trend ricavi: Volume vs Prezzo vs Mix. Stagionalità, concentrazione clienti, qualità e ricorrenza. Proietti i ricavi nei prossimi 3 mesi. Quale leva di crescita è più praticabile?"),
        ("🔬 Altman Z-Score",  "Stima il rischio default con Altman Z'-Score per PMI (Z' = 0.717×X1 + 0.847×X2 + 3.107×X3 + 0.420×X4 + 0.998×X5). Interpreta i dati CE disponibili per stimare X1-X5. Zona: sicura/grigia/distress?"),
    ]

    rows = [quick_prompts[i:i+4] for i in range(0, len(quick_prompts), 4)]
    for row in rows:
        cols = st.columns(4)
        for i, (label, prompt) in enumerate(row):
            with cols[i]:
                if st.button(label, key=f"qp_{label}", use_container_width=True):
                    st.session_state['cfo_pending_prompt'] = prompt

    # ── Chat history ─────────────────────────────────────────────────────────
    st.markdown("<hr style='border-color:rgba(255,255,255,0.06);margin:16px 0'>", unsafe_allow_html=True)

    for msg in st.session_state['cfo_chat_history']:
        if msg['role'] == 'user':
            st.markdown(f"""
            <div class='chat-user'>
                <div class='chat-label-user'>👤 TU</div>
                <div class='chat-text'>{msg["content"]}</div>
            </div>""", unsafe_allow_html=True)
        else:
            content = msg["content"]
            # Render HTML se il contenuto inizia con tag HTML
            if content.strip().startswith('<div') or content.strip().startswith('<p'):
                st.markdown(f"""
                <div class='chat-ai'>
                    <div class='chat-label-ai'>🤖 CFO AI — ANALISI</div>
                    <div class='chat-text'>{content}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='chat-ai'>
                    <div class='chat-label-ai'>🤖 CFO AI — ANALISI</div>
                    <div class='chat-text'>{content}</div>
                </div>""", unsafe_allow_html=True)

    # ── Input ────────────────────────────────────────────────────────────────
    default_val = st.session_state.pop('cfo_pending_prompt', '')
    domanda = st.text_area(
        "Scrivi la tua domanda:",
        value=default_val,
        height=80,
        placeholder="Es: Come spiego la variazione EBITDA al CDA? Dove posso tagliare costi? Outlier insolito su costi logistici...",
        key="cfo_chat_input_main",
        label_visibility="collapsed"
    )

    c1, c2, c3, c4, c5 = st.columns([4, 1, 1, 1, 1])
    with c1:
        send = st.button("📨 Analizza con CFO AI", type="primary", use_container_width=True)
    with c2:
        n_mesi_ctx = st.selectbox("Contesto:", [3, 6, 12], index=1, key="ctx_m",
                                   format_func=lambda x: f"↩ {x}m")
    with c3:
        inc_data = st.checkbox("CE", value=True, key="chat_ce")
    with c4:
        inc_bud = st.checkbox("Budget", value=bool(budget), key="chat_bud")
    with c5:
        if st.button("🗑️", use_container_width=True, help="Reset chat"):
            st.session_state['cfo_chat_history'] = []
            st.rerun()

    if send and domanda.strip():
        api_key = get_api_key()
        if not api_key:
            st.error("⚠️ API Key non configurata. Vai in ⚙️ Settings."); return

        mesi_ctx = mesi[-n_mesi_ctx:]
        ce_text  = format_ce_for_prompt(pivot, mesi_ctx) if inc_data else ""
        kpi_data = calcola_kpi_finanziari(pivot, mesi_ctx) if inc_data else {}
        kpi_text = format_kpi_for_prompt(kpi_data)
        bud_text = format_budget_variance_for_prompt(pivot, budget, mesi_ctx) if (inc_bud and budget) else ""

        context = build_chat_context(
            ca, ce_text, kpi_text,
            f"{mesi_ctx[0]} → {mesi_ctx[-1]}",
            bud_text, settore, note_az
        ) if inc_data else ""

        history = [
            {"role": h['role'], "content": h['content']}
            for h in st.session_state['cfo_chat_history'][-8:]
        ]
        user_content = f"{context}\n\nDomanda: {domanda.strip()}" if context else domanda.strip()
        history.append({"role": "user", "content": user_content})

        risposta = ""
        placeholder = st.empty()
        try:
            client = anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=3000,
                system=CFO_SYSTEM_PROMPT,
                messages=history
            ) as stream:
                for text in stream.text_stream:
                    risposta += text
                    placeholder.markdown(
                        f"<div class='chat-ai streaming'>"
                        f"<div class='chat-label-ai'>🤖 CFO AI — IN ANALISI…</div>"
                        f"<div class='chat-text'>{risposta}▌</div></div>",
                        unsafe_allow_html=True
                    )

            placeholder.empty()
            st.session_state['cfo_chat_history'].append({'role': 'user', 'content': domanda.strip()})
            st.session_state['cfo_chat_history'].append({'role': 'assistant', 'content': risposta})
            st.rerun()

        except Exception as e:
            err = str(e)
            if '401' in err or 'authentication' in err.lower():
                st.error("🔑 API Key non valida. Verifica in ⚙️ Settings → API Key.")
            else:
                st.error(f"Errore: {err}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — VISUAL ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

def _render_visual_analytics(pivot, mesi, budget):
    st.markdown(f"<div class='section-header'>📊 Visual Analytics — Analisi Avanzata</div>", unsafe_allow_html=True)

    voci = list(pivot.index)
    mesi_plot = mesi[-min(18, len(mesi)):]

    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "📈 Trend & Grafici", "🌉 EBITDA Bridge", "🧮 Decomposizione KPI", "📊 Composizione CE"
    ])

    # ── SUB TAB 1: Trend ──────────────────────────────────────────────────────
    with sub_tab1:
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            voci_sel = st.multiselect("Voci CE:", voci,
                default=voci[:min(3, len(voci))], key="va_voci")
        with c2:
            tipo = st.radio("Tipo:", ["Linee", "Barre", "Area", "Stacked", "Waterfall mensile"],
                            horizontal=True, key="va_tipo")
        with c3:
            n_mesi_plot = st.slider("Mesi:", 3, len(mesi), min(12, len(mesi)), key="va_n")

        mesi_p = mesi[-n_mesi_plot:]

        if voci_sel:
            rows_data = []
            for voce in voci_sel:
                for m in mesi_p:
                    if m in pivot.columns:
                        rows_data.append({'Mese': m, 'Voce': str(voce)[:30], 'Importo': float(pivot.loc[voce, m])})
            df_m = pd.DataFrame(rows_data)

            PALETTE = ['#3B82F6', '#10B981', '#C9A84C', '#EF4444', '#8B5CF6', '#F59E0B', '#06B6D4', '#EC4899']
            color_map = {str(v)[:30]: PALETTE[i % len(PALETTE)] for i, v in enumerate(voci_sel)}

            if tipo == "Linee":
                fig = px.line(df_m, x='Mese', y='Importo', color='Voce',
                              markers=True, color_discrete_map=color_map)
                fig.update_traces(line=dict(width=2.5), marker=dict(size=7))
            elif tipo == "Barre":
                fig = px.bar(df_m, x='Mese', y='Importo', color='Voce',
                             barmode='group', color_discrete_map=color_map)
            elif tipo == "Area":
                fig = px.area(df_m, x='Mese', y='Importo', color='Voce',
                              color_discrete_map=color_map)
            elif tipo == "Stacked":
                fig = px.bar(df_m, x='Mese', y='Importo', color='Voce',
                             barmode='stack', color_discrete_map=color_map)
            else:  # Waterfall mensile
                voce_wf = voci_sel[0]
                vals_wf = [float(pivot.loc[voce_wf, m]) if m in pivot.columns else 0 for m in mesi_p]
                fig = go.Figure(go.Waterfall(
                    orientation='v', x=mesi_p, y=vals_wf,
                    connector=dict(line=dict(color='rgba(255,255,255,0.1)', width=1)),
                    increasing=dict(marker=dict(color=C['green'], line=dict(width=0))),
                    decreasing=dict(marker=dict(color=C['red'], line=dict(width=0))),
                    totals=dict(marker=dict(color=C['gold'], line=dict(width=0))),
                ))

            fig.update_layout(
                **PLOTLY_THEME, height=380,
                xaxis=dict(showgrid=False, tickangle=-35, color='#475569',
                           tickfont=dict(size=10), title=''),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)',
                           tickformat=',.0f', ticksuffix=' €', color='#475569',
                           tickfont=dict(size=10)),
                bargap=0.25,
            )
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>%{y:,.0f} €<extra>%{fullData.name}</extra>'
            )
            st.plotly_chart(fig, use_container_width=True)

            # ── Heatmap ────────────────────────────────────────────────────────────
            if len(voci_sel) > 1:
                st.markdown("##### 🗺️ Heatmap Intensità")
                hm = pivot.loc[voci_sel, [m for m in mesi_p if m in pivot.columns]]
                # Normalizza per riga
                hm_norm = hm.div(hm.abs().max(axis=1).replace(0, 1), axis=0)
                fig_hm = go.Figure(go.Heatmap(
                    z=hm_norm.values,
                    x=list(hm_norm.columns),
                    y=[str(v)[:30] for v in hm_norm.index],
                    colorscale=[[0,'#EF4444'],[0.5,'#1E3A6E'],[1,'#10B981']],
                    text=[[f"{v:,.0f}€" for v in row] for row in hm.values],
                    texttemplate="%{text}",
                    textfont=dict(size=9),
                    hoverongaps=False,
                ))
                fig_hm.update_layout(
                    **PLOTLY_THEME, height=max(200, 50*len(voci_sel)+60),
                    xaxis=dict(tickangle=-35, tickfont=dict(size=10), color='#475569'),
                    yaxis=dict(tickfont=dict(size=10), color='#475569'),
                    margin=dict(l=120, r=0, t=20, b=40),
                )
                st.plotly_chart(fig_hm, use_container_width=True)

    # ── SUB TAB 2: EBITDA Bridge ───────────────────────────────────────────────
    with sub_tab2:
        st.markdown("""
        <div class='info-callout'>
        🌉 <b>EBITDA Bridge McKinsey</b> — Decompone la variazione EBITDA tra due periodi nelle sue componenti.
        Seleziona il periodo di riferimento (attuale) e quello di confronto (precedente).
        </div>""", unsafe_allow_html=True)

        anni = sorted(set(m[:4] for m in mesi), reverse=True)
        c1, c2 = st.columns(2)
        with c1:
            anno_att = st.selectbox("Periodo attuale (anno):", anni, key="bridge_att")
            mesi_att = [m for m in mesi if m.startswith(str(anno_att))]
        with c2:
            altri_anni = [a for a in anni if a != anno_att]
            if altri_anni:
                anno_prec = st.selectbox("Periodo confronto (anno):", altri_anni, key="bridge_prec")
                mesi_prec = [m for m in mesi if m.startswith(str(anno_prec))]
            else:
                # Splitta l'anno in S1 e S2
                mid = len(mesi_att)//2
                mesi_prec = mesi_att[:mid]
                mesi_att  = mesi_att[mid:]
                anno_prec = f"H1 {anno_att}"
                st.info("Un solo anno disponibile: confronto H1 vs H2.")

        cols_att  = [c for c in mesi_att  if c in pivot.columns]
        cols_prec = [c for c in mesi_prec if c in pivot.columns]

        if cols_att and cols_prec:
            # Calcola valori per periodo
            def period_sum(cols, voce):
                if voce not in pivot.index:
                    return 0.0
                return float(sum(pivot.loc[voce, c] for c in cols if c in pivot.columns))

            from services.riclassifica import _find_voce_pivot
            v_ricavi = _find_voce_pivot(pivot, ['ricav','fattur','vendite'])
            v_ebitda = _find_voce_pivot(pivot, ['ebitda','mol'])
            v_personale = _find_voce_pivot(pivot, ['personale','lavoro','stipendi'])
            v_acquisti = _find_voce_pivot(pivot, ['acquisti','materie','merci','costi diretti'])
            v_altri = _find_voce_pivot(pivot, ['altri costi','spese generali','overh'])

            ric_att  = period_sum(cols_att, v_ricavi)
            ric_prec = period_sum(cols_prec, v_ricavi)
            eb_att   = period_sum(cols_att, v_ebitda)
            eb_prec  = period_sum(cols_prec, v_ebitda)
            per_att  = period_sum(cols_att, v_personale)
            per_prec = period_sum(cols_prec, v_personale)
            acq_att  = period_sum(cols_att, v_acquisti)
            acq_prec = period_sum(cols_prec, v_acquisti)

            # Bridge components
            delta_ricavi   = ric_att - ric_prec
            delta_per      = -(per_att - per_prec)  # riduzione costi = positivo
            delta_acq      = -(acq_att - acq_prec)
            delta_altri    = eb_att - eb_prec - delta_ricavi - delta_per - delta_acq

            bridge_x = [
                f"EBITDA {anno_prec}", "Δ Ricavi", "Δ Costi\nPersonale",
                "Δ Acquisti\nMaterie", "Δ Altri Costi\n& One-off", f"EBITDA {anno_att}"
            ]
            bridge_y = [eb_prec, delta_ricavi, delta_per, delta_acq, delta_altri, eb_att]
            bridge_type = ["absolute", "relative", "relative", "relative", "relative", "absolute"]
            bridge_color = [
                C['blue'],
                C['green'] if delta_ricavi >= 0 else C['red'],
                C['green'] if delta_per >= 0 else C['red'],
                C['green'] if delta_acq >= 0 else C['red'],
                C['green'] if delta_altri >= 0 else C['red'],
                C['gold'],
            ]

            fig_bridge = go.Figure(go.Waterfall(
                orientation='v',
                measure=bridge_type,
                x=bridge_x,
                y=[v/1000 for v in bridge_y],
                connector=dict(line=dict(color='rgba(255,255,255,0.1)', width=1, dash='dot')),
                increasing=dict(marker=dict(color=C['green'], line=dict(width=0))),
                decreasing=dict(marker=dict(color=C['red'],   line=dict(width=0))),
                totals=dict(marker=dict(color=C['gold'],      line=dict(width=0))),
                text=[f"{v/1000:+,.0f}K€" if bridge_type[i]=='relative' else f"{v/1000:,.0f}K€"
                      for i, v in enumerate(bridge_y)],
                textposition="outside",
                textfont=dict(size=11, color='#E2E8F0'),
            ))
            fig_bridge.update_layout(
                **PLOTLY_THEME, height=380,
                title=dict(text=f"EBITDA Bridge: {anno_prec} → {anno_att}", x=0,
                           font=dict(size=13, color='#C9A84C')),
                xaxis=dict(showgrid=False, tickfont=dict(size=11), color='#64748B'),
                yaxis=dict(title='EBITDA (K€)', showgrid=True, gridcolor='rgba(255,255,255,0.05)',
                           ticksuffix='K', color='#64748B'),
                margin=dict(l=0, r=0, t=60, b=20),
            )
            st.plotly_chart(fig_bridge, use_container_width=True)

            # Riepilogo testuale
            total_delta = eb_att - eb_prec
            pct_delta = total_delta/abs(eb_prec)*100 if eb_prec != 0 else 0
            col_a, col_b, col_c = st.columns(3)
            col_a.metric(f"EBITDA {anno_prec}", fmt_eur(eb_prec))
            col_b.metric(f"EBITDA {anno_att}", fmt_eur(eb_att), f"{pct_delta:+.1f}%")
            col_c.metric("Δ Assoluto", fmt_eur(total_delta))

    # ── SUB TAB 3: Decomposizione KPI ─────────────────────────────────────────
    with sub_tab3:
        n_m = st.slider("Mesi di analisi:", 3, len(mesi), min(6, len(mesi)), key="kd_n")
        mesi_kd = mesi[-n_m:]
        cols_kd = [c for c in mesi_kd if c in pivot.columns]
        kpi = calcola_kpi_finanziari(pivot, cols_kd)

        if kpi:
            st.markdown("##### 📐 Margini — Evoluzione mensile")
            margin_data = []
            for m in mesi_kd:
                if m not in pivot.columns:
                    continue
                kpi_m = calcola_kpi_finanziari(pivot, [m])
                for k, label, color in [
                    ('ebitda_margin', 'EBITDA Margin', C['green']),
                    ('net_margin',    'Net Margin',    C['gold']),
                    ('cost_labor_pct','% Personale',   C['red']),
                ]:
                    v = kpi_m.get(k)
                    if v is not None:
                        margin_data.append({'Mese': m, 'KPI': label, 'Valore': v})

            if margin_data:
                df_marg = pd.DataFrame(margin_data)
                color_disc = {'EBITDA Margin': C['green'], 'Net Margin': C['gold'], '% Personale': C['red']}
                fig_m = px.line(df_marg, x='Mese', y='Valore', color='KPI',
                                markers=True, color_discrete_map=color_disc)
                fig_m.add_hline(y=0, line_dash='dash', line_color='rgba(255,255,255,0.2)')
                fig_m.update_traces(line=dict(width=2.5), marker=dict(size=7))
                fig_m.update_layout(
                    **PLOTLY_THEME, height=300,
                    yaxis=dict(ticksuffix='%', showgrid=True, gridcolor='rgba(255,255,255,0.05)',
                               color='#475569', tickfont=dict(size=10)),
                    xaxis=dict(showgrid=False, tickangle=-30, color='#475569', tickfont=dict(size=10)),
                    margin=dict(l=0, r=0, t=10, b=0),
                )
                st.plotly_chart(fig_m, use_container_width=True)

            # DuPont (semplificato da CE)
            st.markdown("##### 🔬 DuPont — Decomposizione della Redditività")
            ricavi = kpi.get('ricavi', 0)
            ebitda = kpi.get('ebitda', 0)
            utile  = kpi.get('utile_netto', 0)
            em     = kpi.get('ebitda_margin', 0) or 0
            nm     = kpi.get('net_margin', 0) or 0

            st.markdown(f"""
            <div class='dupont-box'>
                <div class='dp-col'>
                    <div class='dp-label'>NET MARGIN</div>
                    <div class='dp-val' style='color:{C["gold"]}'>{nm:.1f}%</div>
                    <div class='dp-sub'>Utile / Ricavi</div>
                </div>
                <div class='dp-op'>×</div>
                <div class='dp-col'>
                    <div class='dp-label'>ASSET TURNOVER</div>
                    <div class='dp-val' style='color:{C["blue"]}'>—</div>
                    <div class='dp-sub'>Ricavi / Attivo<br>(dato non disponibile da CE)</div>
                </div>
                <div class='dp-op'>×</div>
                <div class='dp-col'>
                    <div class='dp-label'>LEVERAGE</div>
                    <div class='dp-val' style='color:{C["violet"]}'>—</div>
                    <div class='dp-sub'>Attivo / Patrimonio<br>(dato non disponibile da CE)</div>
                </div>
                <div class='dp-op'>=</div>
                <div class='dp-col' style='background:rgba(201,168,76,0.08);border:1px solid rgba(201,168,76,0.2)'>
                    <div class='dp-label'>ROE STIMATO</div>
                    <div class='dp-val' style='color:{C["green"]}'>—</div>
                    <div class='dp-sub'>Basato solo su CE<br>carica SP per ROE completo</div>
                </div>
            </div>
            <div class='info-callout' style='margin-top:12px;font-size:0.78rem'>
            💡 Per l'analisi DuPont completa (ROE, ROIC, Asset Turnover, Leverage) carica 
            anche lo Stato Patrimoniale nel Workspace. Con solo il CE posso calcolare 
            Net Margin e EBITDA Margin.
            </div>""", unsafe_allow_html=True)

    # ── SUB TAB 4: Composizione CE ─────────────────────────────────────────────
    with sub_tab4:
        st.markdown("##### 🥧 Composizione CE — Struttura dei Costi e Ricavi")
        c1, c2 = st.columns(2)
        with c1:
            mese_comp = st.selectbox("Mese di riferimento:", mesi, index=len(mesi)-1, key="comp_mese")
        with c2:
            soglia_pct = st.slider("Soglia minima (%):", 0.5, 10.0, 2.0, 0.5, key="comp_soglia")

        if mese_comp in pivot.columns:
            vals_comp = {v: float(pivot.loc[v, mese_comp]) for v in pivot.index}
            pos = {k: v for k, v in vals_comp.items() if v > 0}
            neg = {k: abs(v) for k, v in vals_comp.items() if v < 0}

            tot_pos = sum(pos.values())
            tot_neg = sum(neg.values())

            def make_pie(d, total, title, colors_palette):
                if not d or total == 0:
                    return None
                thresh = total * soglia_pct / 100
                big = {k: v for k, v in d.items() if v >= thresh}
                altri = sum(v for k, v in d.items() if v < thresh)
                if altri > 0:
                    big['Altri (<{:.0f}%)'.format(soglia_pct)] = altri
                labels = [str(k)[:25] for k in big.keys()]
                values = list(big.values())
                colors = [colors_palette[i % len(colors_palette)] for i in range(len(labels))]
                fig = go.Figure(go.Pie(
                    labels=labels, values=values,
                    marker=dict(colors=colors, line=dict(color='#0F1923', width=2)),
                    textposition='inside', textinfo='percent',
                    insidetextfont=dict(size=11, color='white'),
                    hovertemplate='<b>%{label}</b><br>%{value:,.0f} €<br>%{percent}<extra></extra>',
                ))
                fig.update_layout(
                    **PLOTLY_THEME, height=300,
                    title=dict(text=title, x=0.5, font=dict(size=12, color='#C9A84C')),
                    margin=dict(l=0, r=0, t=40, b=0),
                    showlegend=True,
                    legend=dict(font=dict(size=9), orientation='v', x=1, y=0.5),
                )
                return fig

            BLUES  = ['#1E3A6E','#2563EB','#3B82F6','#60A5FA','#93C5FD','#BFDBFE']
            REDS   = ['#7F1D1D','#DC2626','#EF4444','#F87171','#FCA5A5','#FECACA']

            fig_pos = make_pie(pos, tot_pos, f"Voci Positive — {mese_comp}", BLUES)
            fig_neg = make_pie(neg, tot_neg, f"Voci Negative — {mese_comp}", REDS)

            p1, p2 = st.columns(2)
            if fig_pos:
                with p1:
                    st.plotly_chart(fig_pos, use_container_width=True)
                    st.metric("Totale positivi", fmt_eur(tot_pos))
            if fig_neg:
                with p2:
                    st.plotly_chart(fig_neg, use_container_width=True)
                    st.metric("Totale negativi", fmt_eur(-tot_neg))


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — GENERA REPORT
# ─────────────────────────────────────────────────────────────────────────────

def _render_report_gen(ca, cliente, pivot, mesi, budget):
    st.markdown(f"<div class='section-header'>📋 Genera Report Automatici con AI</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='info-callout'>
    Il CFO AI usa <b>Claude Opus 4</b> con framework McKinsey·BCG·HBS·CIMA per produrre
    report professionali di altissimo livello. Il processo richiede 30–90 secondi.
    I report vengono salvati in HTML scaricabile e pronto per l'invio email.
    </div>""", unsafe_allow_html=True)

    cfo_cfg   = cliente.get('cfo_settings', {})
    settore   = cfo_cfg.get('settore', '')
    note_az   = cfo_cfg.get('note_azienda', '')
    targets   = cfo_cfg.get('kpi_targets', {})
    anni_disp = sorted(set(m[:4] for m in mesi), reverse=True)

    # ── Config ────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    with c1:
        tipo_report = st.selectbox("Tipo report:", [
            "📊 Analisi Mensile Completa",
            "⚡ Flash Report Settimanale",
            "🎯 Analisi Scostamenti Budget",
            "🏛️ Board Summary Annuale",
            "💰 Cash Flow Analysis",
        ], key="rpt_tipo")
    with c2:
        if "Annuale" in tipo_report or "Board" in tipo_report:
            anno = st.selectbox("Anno:", anni_disp, key="rpt_anno")
            mesi_sel = [m for m in mesi if m.startswith(str(anno))]
        else:
            mese_sel = st.selectbox("Mese:", mesi, index=len(mesi)-1, key="rpt_mese")
            mesi_sel = [mese_sel]
    with c3:
        settore_ov = st.text_input("Settore:", value=settore, placeholder="es. Manifattura", key="rpt_sett")
    with c4:
        st.markdown("<br>", unsafe_allow_html=True)
        genera = st.button("🚀 Genera", type="primary", use_container_width=True)

    periodo_label = mesi_sel[0] if len(mesi_sel) == 1 else f"{mesi_sel[0]}→{mesi_sel[-1]}"

    if genera:
        api_key = get_api_key()
        if not api_key:
            st.error("⚠️ API Key non configurata. Vai in ⚙️ Settings."); return

        cols_sel = [c for c in mesi_sel if c in pivot.columns]
        if not cols_sel:
            st.error("Nessun dato per il periodo selezionato."); return

        ce_text    = format_ce_for_prompt(pivot, cols_sel)
        kpi_data   = calcola_kpi_finanziari(pivot, cols_sel)
        kpi_text   = format_kpi_for_prompt(kpi_data)
        bud_text   = format_budget_variance_for_prompt(pivot, budget, cols_sel) if budget else ""

        # Anno precedente
        anno_num  = int(mesi_sel[0][:4])
        mesi_prec = [m.replace(str(anno_num), str(anno_num-1)) for m in mesi_sel]
        cols_prec = [c for c in mesi_prec if c in pivot.columns]
        ap_text   = format_ce_for_prompt(pivot, cols_prec) if cols_prec else ""

        # Prompt selector
        if "Mensile" in tipo_report:
            prompt  = build_monthly_analysis_prompt(ca, periodo_label, ce_text, kpi_text, bud_text, "", settore_ov or settore, ap_text, note_az, targets)
            titolo  = f"Analisi Mensile — {periodo_label}"
        elif "Flash" in tipo_report:
            prompt  = build_weekly_flash_prompt(ca, periodo_label, ce_text, kpi_text, "", settore_ov or settore)
            titolo  = f"Flash Report — {periodo_label}"
        elif "Budget" in tipo_report:
            if not budget:
                st.warning("⚠️ Configura prima un Budget nella sezione Budget."); return
            prompt  = build_budget_variance_prompt(ca, periodo_label, bud_text, kpi_text, note_az)
            titolo  = f"Analisi Budget — {periodo_label}"
        elif "Board" in tipo_report:
            prompt  = build_board_summary_prompt(ca, str(anno_num), ce_text, kpi_text, "", settore_ov or settore)
            titolo  = f"Board Summary — FY {anno_num}"
        else:  # Cash Flow
            prompt  = build_cashflow_prompt(ca, periodo_label, ce_text, kpi_text)
            titolo  = f"Cash Flow Analysis — {periodo_label}"

        # ── Streaming generation ──────────────────────────────────────────────
        content_ai  = ""
        placeholder = st.empty()

        with placeholder.container():
            prog_bar = st.progress(0)
            status   = st.empty()
            live_box = st.empty()

        try:
            client = anthropic.Anthropic(api_key=api_key)
            token_count = 0

            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=5000,
                system=CFO_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    content_ai  += text
                    token_count += len(text.split())
                    prog = min(0.98, token_count / 800)
                    prog_bar.progress(prog)
                    status.markdown(f"<div style='color:{C['gold']};font-size:0.8rem'>✍️ Il CFO sta scrivendo… ({len(content_ai)} caratteri)</div>", unsafe_allow_html=True)
                    live_box.markdown(
                        f"<div class='live-report-box'>{content_ai[-2000:]}▌</div>",
                        unsafe_allow_html=True
                    )

            placeholder.empty()

            # Wrap in template HTML premium
            tipo_label = tipo_report.split(" ", 1)[1] if " " in tipo_report else tipo_report
            report_html = wrap_report(content_ai, titolo, ca, tipo_label, periodo_label)

            st.session_state['last_report_html']    = report_html
            st.session_state['last_report_title']   = titolo
            st.session_state['last_report_content'] = content_ai
            st.session_state['last_report_period']  = periodo_label

            hist = cliente.get('report_history', [])
            hist.append({'titolo': titolo, 'tipo': tipo_report, 'periodo': periodo_label,
                          'data': datetime.now().strftime('%d/%m/%Y %H:%M')})
            save_cliente({'report_history': hist[-30:]})
            st.success(f"✅ Report generato: **{titolo}**")

        except Exception as e:
            placeholder.empty()
            err = str(e)
            if '401' in err:
                st.error("🔑 API Key non valida.")
            else:
                st.error(f"Errore generazione: {err}")
            return

    # ── Visualizza ultimo report ────────────────────────────────────────────
    if 'last_report_html' in st.session_state:
        st.markdown("---")
        titolo_show = st.session_state.get('last_report_title', 'Report')
        content     = st.session_state.get('last_report_content', '')

        st.markdown(f"### 📄 {titolo_show}")
        st.markdown(f"<div class='report-preview'>{content}</div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button("⬇️ Download HTML", data=st.session_state['last_report_html'].encode('utf-8'),
                                file_name=f"report_{ca}_{datetime.now().strftime('%Y%m%d')}.html",
                                mime="text/html", use_container_width=True)
        with c2:
            st.download_button("⬇️ Download TXT", data=content.encode('utf-8'),
                                file_name=f"report_{ca}_{datetime.now().strftime('%Y%m%d')}.txt",
                                mime="text/plain", use_container_width=True)
        with c3:
            if st.button("📧 → Email", use_container_width=True):
                st.info("Vai al tab 📧 Email & Delivery per inviare questo report.")

        # Storico
        hist = cliente.get('report_history', [])
        if len(hist) > 1:
            with st.expander(f"📚 Storico report ({len(hist)})"):
                for r in reversed(hist[-15:]):
                    st.markdown(
                        f"<div style='padding:7px 0;border-bottom:1px solid {C['border']};font-size:0.8rem;color:{C['muted']}'>"
                        f"<b style='color:{C['text']}'>{r['titolo']}</b> · {r['data']}</div>",
                        unsafe_allow_html=True
                    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — ANOMALIE & ALERT
# ─────────────────────────────────────────────────────────────────────────────

def _render_anomalie(ca, cliente, pivot, mesi, budget):
    st.markdown(f"<div class='section-header'>🔍 Anomalie & Alert Intelligenti</div>", unsafe_allow_html=True)

    # Statistica automatica
    st.markdown("#### 📊 Early Warning System — Analisi Statistica Automatica")
    n_finestra = st.slider("Finestra storica (mesi):", 3, min(24, len(mesi)), min(12, len(mesi)), key="anom_win")
    anomalie = _calcola_anomalie_avanzate(pivot, budget, mesi, n_finestra)

    n_rossi  = sum(1 for a in anomalie if a['semaforo'] == '🔴')
    n_gialli = sum(1 for a in anomalie if a['semaforo'] == '🟡')
    n_verdi  = sum(1 for a in anomalie if a['semaforo'] == '🟢')

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Anomalie Critiche",  n_rossi)
    c2.metric("Da Monitorare",      n_gialli)
    c3.metric("Positive",           n_verdi)
    c4.metric("Totale Segnali",     len(anomalie))

    if anomalie:
        for a in anomalie:
            color = {
                '🔴': C['red'], '🟡': C['amber'], '🟢': C['green']
            }.get(a['semaforo'], C['muted'])
            bg = {
                '🔴': 'rgba(239,68,68,0.06)', '🟡': 'rgba(245,158,11,0.06)',
                '🟢': 'rgba(16,185,129,0.06)'
            }.get(a['semaforo'], 'rgba(255,255,255,0.02)')

            st.markdown(f"""
            <div style='background:{bg};border:1px solid {color}22;border-left:3px solid {color};
                        border-radius:10px;padding:14px 18px;margin:8px 0;display:flex;gap:16px'>
                <div style='font-size:1.4rem;min-width:30px'>{a["semaforo"]}</div>
                <div style='flex:1'>
                    <div style='font-weight:700;color:{C["text"]};font-size:0.88rem;margin-bottom:3px'>{a["voce"]}</div>
                    <div style='color:{C["muted"]};font-size:0.8rem'>{a["descrizione"]}</div>
                    <div style='color:{color};font-size:0.78rem;margin-top:5px;font-weight:600'>
                        ↳ {a["azione"]}
                    </div>
                </div>
                <div style='text-align:right;min-width:90px;flex-shrink:0'>
                    <div style='font-size:1.05rem;font-weight:700;color:{color}'>{a["valore"]}</div>
                    <div style='font-size:0.7rem;color:{C["muted"]};margin-top:2px'>{a["tipo"]}</div>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.2);
                    border-radius:10px;padding:16px 20px;text-align:center;color:{C["green"]}'>
            ✅ Nessuna anomalia statistica significativa nel periodo analizzato.
        </div>""", unsafe_allow_html=True)

    # ── Visualizzazione trend con confidence band ──────────────────────────────
    if anomalie:
        st.markdown("---")
        st.markdown("#### 📈 Visualizzazione Trend con Banda di Confidenza")
        voce_viz = st.selectbox("Voce da analizzare:",
                                 [a['voce'] for a in anomalie if a['voce'] in pivot.index],
                                 key="anom_voce")
        if voce_viz and voce_viz in pivot.index:
            _render_trend_chart_with_bands(pivot, voce_viz, mesi[-n_finestra:])

    # ── AI Deep Analysis ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🤖 Deep Analysis — Intelligenza Artificiale")
    st.markdown(f"""
    <div class='info-callout'>
    L'AI analizza pattern sequenziali, outlier multivariati e correlazioni tra voci
    che la statistica semplice non coglie. Include early warning a 60-90 giorni.
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([4, 1])
    with c1:
        n_mesi_ai = st.slider("Finestra AI:", 3, min(24, len(mesi)), min(9, len(mesi)), key="anom_ai_n")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        lancia_ai = st.button("🔍 Analisi AI", type="primary", use_container_width=True)

    if lancia_ai:
        api_key = get_api_key()
        if not api_key:
            st.error("⚠️ API Key non configurata."); return

        mesi_an = mesi[-n_mesi_ai:]
        ce_text = format_ce_for_prompt(pivot, mesi_an)

        trend_lines = []
        for voce in list(pivot.index):
            t = calcola_trend(pivot, voce, n_mesi_ai)
            if t:
                yoy_s = f" | yoy={t['yoy']:+.1f}%" if t.get('yoy') is not None else ""
                trend_lines.append(
                    f"{str(voce)[:40]}: media={t['media']:,.0f}€ | cv={t['cv']:.1f}% | "
                    f"mom={t['mom']:+.1f}% | dir={t['direction']}{yoy_s}"
                )

        prompt = build_anomaly_detection_prompt(ce_text, "\n".join(trend_lines), ca)
        result = ""
        placeholder = st.empty()
        try:
            client = anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model="claude-opus-4-6", max_tokens=3500,
                system=CFO_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    result += text
                    placeholder.markdown(f"<div class='report-preview'>{result}▌</div>",
                                         unsafe_allow_html=True)

            st.session_state['anomalie_ai_result'] = result
        except Exception as e:
            st.error(f"Errore: {e}")

    if 'anomalie_ai_result' in st.session_state:
        st.markdown(f"<div class='report-preview'>{st.session_state['anomalie_ai_result']}</div>",
                     unsafe_allow_html=True)


def _calcola_anomalie_avanzate(pivot, budget, mesi, n_finestra) -> list:
    """Rilevamento anomalie statistico avanzato: 2σ, trend consecutivi, budget alert."""
    anomalie = []
    mesi_an = mesi[-n_finestra:]

    stat = calcola_statistiche_mensili(pivot)

    for voce in pivot.index:
        if voce not in stat:
            continue
        s  = stat[voce]
        if s['media'] == 0:
            continue
        vals_an = [float(pivot.loc[voce, m]) for m in mesi_an if m in pivot.columns]
        if not vals_an:
            continue
        ultimo = vals_an[-1]

        # ─ Anomalia statistica >2σ ─────────────────────────────────────────
        if s['std'] > 0 and abs(ultimo - s['media']) > 2 * s['std']:
            pct = (ultimo - s['media']) / abs(s['media']) * 100
            anomalie.append({
                'voce': voce,
                'semaforo': '🔴' if abs(pct) > 35 else '🟡',
                'tipo': 'Outlier >2σ',
                'descrizione': f"Valore ({fmt_eur(ultimo)}) dista {abs(ultimo-s['media'])/s['std']:.1f}σ dalla media storica ({fmt_eur(s['media'])}). CV={s['cv']:.1f}%",
                'azione': "Verifica: dato errato, operazione straordinaria o cambio strutturale del business?",
                'valore': f"{pct:+.1f}%",
            })

        # ─ Trend consecutivo ≥3 mesi ─────────────────────────────────────
        if len(vals_an) >= 3:
            last3 = vals_an[-3:]
            if all(last3[i] < last3[i-1] for i in range(1,3)):
                pct = (last3[-1]-last3[0])/abs(last3[0])*100 if last3[0]!=0 else 0
                if abs(pct) > 8:
                    anomalie.append({
                        'voce': voce,
                        'semaforo': '🔴' if pct < -20 else '🟡',
                        'tipo': 'Trend discendente',
                        'descrizione': f"3 mesi consecutivi in calo: da {fmt_eur(last3[0])} a {fmt_eur(last3[-1])} ({pct:.1f}%)",
                        'azione': "Causa radice: Volume in erosione? Perdita clienti? Calo prezzi? Richiede azione immediata.",
                        'valore': f"{pct:+.1f}%",
                    })
            elif all(last3[i] > last3[i-1] for i in range(1,3)):
                pct = (last3[-1]-last3[0])/abs(last3[0])*100 if last3[0]!=0 else 0
                if pct > 20:
                    anomalie.append({
                        'voce': voce,
                        'semaforo': '🟢',
                        'tipo': 'Trend crescita',
                        'descrizione': f"3 mesi consecutivi in crescita: +{pct:.1f}% ({fmt_eur(last3[0])} → {fmt_eur(last3[-1])})",
                        'azione': "Capitalizza: è scalabile? Sostenibile? Identifica il driver e amplificalo.",
                        'valore': f"+{pct:.1f}%",
                    })

        # ─ Volatilità anomala (CV >50%) ────────────────────────────────────
        cv_an = np.std(vals_an) / abs(np.mean(vals_an)) * 100 if np.mean(vals_an) != 0 else 0
        if cv_an > 50 and len(vals_an) >= 4:
            anomalie.append({
                'voce': voce,
                'semaforo': '🟡',
                'tipo': 'Alta volatilità',
                'descrizione': f"CV={cv_an:.0f}% — valore molto volatile. Range: {fmt_eur(min(vals_an))} ÷ {fmt_eur(max(vals_an))}",
                'azione': "Verifica stagionalità vs irregolarità. Budget e forecast potrebbero essere inaffidabili.",
                'valore': f"CV {cv_an:.0f}%",
            })

        # ─ Budget alert intelligente ────────────────────────────────────────
        if budget and voce in budget:
            bud_ult = budget[voce].get(mesi_an[-1] if mesi_an else '', 0)
            if bud_ult != 0:
                scost = (ultimo - bud_ult) / abs(bud_ult) * 100
                # Soglia dinamica basata su CV storico
                soglia_min = 15.0
                soglia = max(soglia_min, s['cv'] * 0.8)
                if abs(scost) >= soglia:
                    anomalie.append({
                        'voce': voce,
                        'semaforo': '🔴' if abs(scost) > 30 else '🟡',
                        'tipo': 'Scostamento budget',
                        'descrizione': f"Effettivo {fmt_eur(ultimo)} vs Budget {fmt_eur(bud_ult)} | Soglia adattiva: {soglia:.0f}%",
                        'azione': "Aggiorna forecast, informa il management, prepara recovery plan con impatto €.",
                        'valore': f"{scost:+.1f}%",
                    })

    return sorted(anomalie, key=lambda x: {'🔴': 0, '🟡': 1, '🟢': 2}.get(x['semaforo'], 3))


def _render_trend_chart_with_bands(pivot, voce, mesi):
    """Visualizza trend con banda di confidenza ±2σ."""
    vals  = [float(pivot.loc[voce, m]) for m in mesi if m in pivot.columns]
    mesi_v = [m for m in mesi if m in pivot.columns]
    if not vals:
        return

    media = np.mean(vals)
    std   = np.std(vals)

    fig = go.Figure()
    # Banda confidenza ±2σ
    fig.add_trace(go.Scatter(
        x=mesi_v + list(reversed(mesi_v)),
        y=[media+2*std]*len(mesi_v) + [media-2*std]*len(mesi_v),
        fill='toself', fillcolor='rgba(59,130,246,0.08)',
        line=dict(color='rgba(0,0,0,0)'),
        name='Banda ±2σ', showlegend=True,
        hoverinfo='skip'
    ))
    # Media
    fig.add_trace(go.Scatter(
        x=mesi_v, y=[media]*len(mesi_v),
        mode='lines', line=dict(color=C['muted'], width=1, dash='dot'),
        name=f'Media ({fmt_k(media)}€)', showlegend=True
    ))
    # Valori
    colors_pts = [C['red'] if abs(v-media) > 2*std else (C['amber'] if abs(v-media) > std else C['green'])
                  for v in vals]
    fig.add_trace(go.Scatter(
        x=mesi_v, y=vals,
        mode='lines+markers',
        line=dict(color=C['blue'], width=2.5),
        marker=dict(size=8, color=colors_pts, line=dict(color='white', width=1.5)),
        name=str(voce)[:30],
        hovertemplate='<b>%{x}</b><br>%{y:,.0f} €<extra></extra>'
    ))

    fig.update_layout(
        **PLOTLY_THEME, height=300,
        title=dict(text=f"Trend + Confidence Band — {str(voce)[:40]}", x=0,
                   font=dict(size=12, color='#C9A84C')),
        xaxis=dict(showgrid=False, tickangle=-30, color='#475569', tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)',
                   tickformat=',.0f', ticksuffix='€', color='#475569', tickfont=dict(size=10)),
        margin=dict(l=0, r=0, t=50, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — MARKET INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────

def _render_market_intel(ca, cliente, mesi):
    st.markdown(f"<div class='section-header'>🌍 Market Intelligence — Contesto di Mercato</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='info-callout'>
    Il CFO AI analizza il contesto macroeconomico e settoriale italiano con fonti aggiornate
    (ISTAT, Banca d'Italia, BCE, Mediobanca R&S, Cerved, Il Sole 24 Ore, Confindustria).
    </div>""", unsafe_allow_html=True)

    cfo_cfg = cliente.get('cfo_settings', {})
    settore_def = cfo_cfg.get('settore', '')

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        settore_mi = st.text_input("Settore:", value=settore_def,
                                    placeholder="es. manifattura meccanica, retail alimentare, SaaS B2B...",
                                    key="mi_settore")
    with c2:
        tipo_mi = st.selectbox("Tipo analisi:", [
            "📊 Market Overview Completo",
            "⚡ Flash Macro Italia (30gg)",
            "📈 Benchmark Settoriale",
            "⚖️ Alert Normativo & Fiscale",
            "🏦 Credito & Costo Capitale",
        ], key="mi_tipo")
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        genera_mi = st.button("🌍 Genera", type="primary", use_container_width=True)

    periodo_mi = datetime.now().strftime('%B %Y')

    if genera_mi:
        if not settore_mi.strip():
            st.warning("Inserisci il settore."); return
        api_key = get_api_key()
        if not api_key:
            st.error("⚠️ API Key non configurata."); return

        result = ""
        placeholder = st.empty()

        try:
            client = anthropic.Anthropic(api_key=api_key)

            # Prova web search
            web_content = ""
            try:
                ws_prompt = f"Trova informazioni aggiornate (ultimi 60 giorni) su: economia italiana e settore {settore_mi}. Include dati macroeconomici, normativa fiscale recente, trend settoriale."
                ws_resp = client.messages.create(
                    model="claude-opus-4-6", max_tokens=2000,
                    messages=[{"role": "user", "content": ws_prompt}],
                    tools=[{"type": "web_search_20250305", "name": "web_search"}]
                )
                for block in ws_resp.content:
                    if hasattr(block, 'text'):
                        web_content += block.text
            except Exception:
                pass  # Fallback senza web search

            prompt = build_market_context_prompt(settore_mi, periodo_mi, web_content)

            with client.messages.stream(
                model="claude-opus-4-6", max_tokens=3500,
                system=CFO_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    result += text
                    placeholder.markdown(f"<div class='report-preview'>{result}▌</div>",
                                         unsafe_allow_html=True)

            st.session_state['market_intel_result']  = result
            st.session_state['market_intel_settore'] = settore_mi

        except Exception as e:
            err = str(e)
            if '401' in err:
                st.error("🔑 API Key non valida.")
            else:
                st.error(f"Errore: {err}")

    if 'market_intel_result' in st.session_state:
        st.markdown(f"<div class='report-preview'>{st.session_state['market_intel_result']}</div>",
                     unsafe_allow_html=True)
        mi_html = wrap_report(
            st.session_state['market_intel_result'],
            f"Market Intelligence — {st.session_state.get('market_intel_settore','')}",
            ca, "Market Intelligence", periodo_mi
        )
        st.download_button("⬇️ Download Report HTML", data=mi_html.encode('utf-8'),
                            file_name=f"market_intel_{datetime.now().strftime('%Y%m%d')}.html",
                            mime="text/html")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — EMAIL & DELIVERY
# ─────────────────────────────────────────────────────────────────────────────

def _render_email_tab(cliente, ca):
    st.markdown(f"<div class='section-header'>📧 Email & Delivery Automatica</div>", unsafe_allow_html=True)

    email_cfg = cliente.get('email_config', {})
    cfo_cfg   = cliente.get('cfo_settings', {})

    sub1, sub2, sub3 = st.tabs(["⚙️ Configura SMTP", "📤 Invia Report", "🔌 Test"])

    with sub1:
        st.markdown(f"""
        <div style='background:rgba(245,158,11,0.07);border-left:3px solid {C["amber"]};
                    border-radius:0 8px 8px 0;padding:12px 16px;font-size:0.83rem;
                    color:{C["muted"]};margin-bottom:16px'>
        Per <b style='color:{C["text"]}'>Gmail</b>: usa una App Password (non la password normale).<br>
        Account Google → Sicurezza → Verifica in 2 passaggi → Password per le app
        </div>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            provider = st.selectbox("Provider:", list(PROVIDER_PRESETS.keys()), key="smtp_prov")
            preset   = PROVIDER_PRESETS[provider]
            smtp_user = st.text_input("Email mittente:", value=email_cfg.get('user',''), key="smtp_user")
            smtp_host = st.text_input("Host SMTP:", value=email_cfg.get('host', preset['host']), key="smtp_host")
        with c2:
            smtp_pass = st.text_input("Password / App Password:", type="password", value=email_cfg.get('password',''), key="smtp_pass")
            smtp_port = st.number_input("Porta:", value=int(email_cfg.get('port', preset['port'])), min_value=1, max_value=65535, key="smtp_port")
            smtp_tls  = st.checkbox("TLS (STARTTLS)", value=email_cfg.get('tls', True), key="smtp_tls")

        if st.button("💾 Salva SMTP", type="primary"):
            save_cliente({'email_config': {'host': smtp_host, 'port': smtp_port,
                                           'user': smtp_user, 'password': smtp_pass, 'tls': smtp_tls}})
            st.success("✅ Configurazione SMTP salvata!")

        st.markdown("---")
        dest_str = st.text_area("Destinatari predefiniti (uno per riga):",
                                 value='\n'.join(cfo_cfg.get('destinatari',[])),
                                 height=90, placeholder="ceo@azienda.it\ncfo@azienda.it", key="dest_cfg")
        if st.button("💾 Salva Destinatari"):
            dest_list = [e.strip() for e in dest_str.split('\n') if e.strip() and '@' in e]
            cfo_cfg['destinatari'] = dest_list
            save_cliente({'cfo_settings': cfo_cfg})
            st.success(f"✅ {len(dest_list)} destinatari salvati")

    with sub2:
        if not email_cfg.get('user'):
            st.warning("⚠️ Configura prima il server SMTP.")
        elif 'last_report_html' not in st.session_state:
            st.info("💡 Genera prima un report nel tab 📋 Genera Report.")
        else:
            titolo_r = st.session_state.get('last_report_title', 'Report')
            c1, c2 = st.columns(2)
            with c1:
                oggetto  = st.text_input("Oggetto:", value=f"AI-Manager | {titolo_r} — {ca}", key="email_obj")
            with c2:
                dest_inp = st.text_area("Destinatari:", height=80,
                                         value='\n'.join(cfo_cfg.get('destinatari',[])), key="email_dest")
            cc_inp = st.text_input("CC:", placeholder="cc@example.com", key="email_cc")

            preview = st.session_state.get('last_report_content','')[:1500]
            st.markdown(f"<div style='background:{C['surf']};border:1px solid {C['border']};border-radius:8px;padding:14px;max-height:200px;overflow-y:auto;font-size:0.78rem;color:{C['muted']}'>{preview}…</div>", unsafe_allow_html=True)

            if st.button("📤 Invia Email Ora", type="primary"):
                dest_list = [e.strip() for e in dest_inp.split('\n') if e.strip() and '@' in e]
                cc_list   = [e.strip() for e in cc_inp.split(',') if e.strip() and '@' in e]
                if not dest_list:
                    st.error("Nessun destinatario valido.")
                else:
                    body = build_email_body(ca, titolo_r,
                                             st.session_state.get('last_report_period',''),
                                             f"<p>{preview[:600]}…</p>")
                    with st.spinner("📤 Invio in corso…"):
                        ok, msg = send_report_email(
                            smtp_config=email_cfg, destinatari=dest_list,
                            oggetto=oggetto, body_html=body,
                            allegato_html=st.session_state['last_report_html'],
                            allegato_nome=f"report_{ca}_{datetime.now().strftime('%Y%m%d')}.html",
                            cc=cc_list or None
                        )
                    st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}")

    with sub3:
        if not email_cfg.get('user'):
            st.info("Configura prima le credenziali SMTP.")
        else:
            st.json({k: '•'*8 if k == 'password' else v for k, v in email_cfg.items()})
            if st.button("🔌 Testa Connessione"):
                with st.spinner("Test…"):
                    ok, msg = validate_smtp_config(email_cfg)
                st.success(msg) if ok else st.error(msg)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

def _render_settings(cliente, ca):
    st.markdown(f"<div class='section-header'>⚙️ Configurazione Agente CFO</div>", unsafe_allow_html=True)

    cfo_cfg = cliente.get('cfo_settings', {})

    # API Key
    st.markdown("#### 🔑 API Key Anthropic")
    current_key = get_api_key()
    if current_key:
        masked = current_key[:12] + '•'*20 + current_key[-4:]
        st.success(f"✅ API Key attiva: `{masked}`")
    else:
        st.error("❌ Nessuna API Key — il CFO Agent non funzionerà.")
    new_key = st.text_input("Inserisci / aggiorna API Key:", type="password",
                             placeholder="sk-ant-api03-...", key="cfg_new_key")
    if st.button("💾 Salva API Key") and new_key.strip():
        st.session_state['anthropic_api_key'] = new_key.strip()
        st.success("✅ API Key salvata per questa sessione")
        st.rerun()

    st.markdown("---")

    # Contesto aziendale
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🏭 Profilo Aziendale")
        settore  = st.text_input("Settore / Industry:", value=cfo_cfg.get('settore',''),
                                  placeholder="es. Manifattura metalmeccanica, Retail, SaaS B2B…", key="cfg_sett")
        lingua   = st.selectbox("Lingua report:", ["Italiano","Inglese","Bilingue IT/EN"],
                                  index=0 if cfo_cfg.get('lingua','Italiano')=='Italiano' else 1, key="cfg_ling")
        stile    = st.selectbox("Stile:", ["Executive (CDA/Investitori)","Operativo (Management)","Tecnico (CFO/Controller)"], key="cfg_stile")

    with c2:
        st.markdown("#### 📝 Contesto per AI")
        note_az  = st.text_area("Contesto aziendale per il CFO AI:", value=cfo_cfg.get('note_azienda',''),
                                 height=140,
                                 placeholder="Es: PMI manifatturiera, 50 dipendenti, B2B export 60% Europa,\n"
                                             "stagionalità forte Q3, EBITDA target 15%, debito bancario basso,\n"
                                             "acquisizione pianificata nel 2025...", key="cfg_note")

    st.markdown("---")
    st.markdown("#### 🎯 KPI Target Aziendali")
    targets = cfo_cfg.get('kpi_targets', {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        t_ebitda = st.number_input("EBITDA margin (%):", value=float(targets.get('ebitda_margin', 12.0)),
                                    step=0.5, format="%.1f", key="t_eb")
    with c2:
        t_net    = st.number_input("Net margin (%):", value=float(targets.get('net_margin', 5.0)),
                                    step=0.5, format="%.1f", key="t_net")
    with c3:
        t_growth = st.number_input("Revenue growth (%):", value=float(targets.get('revenue_growth', 10.0)),
                                    step=1.0, format="%.1f", key="t_gr")
    with c4:
        t_alert  = st.slider("Soglia alert (%):", 5, 30, int(cfo_cfg.get('soglia_alert', 15)), 5, key="t_alert")

    st.markdown("---")
    if st.button("💾 Salva Configurazione CFO", type="primary"):
        cfo_cfg.update({
            'settore': settore, 'lingua': lingua, 'stile': stile,
            'note_azienda': note_az, 'soglia_alert': t_alert,
            'kpi_targets': {'ebitda_margin': t_ebitda, 'net_margin': t_net, 'revenue_growth': t_growth}
        })
        save_cliente({'cfo_settings': cfo_cfg})
        st.success("✅ Configurazione CFO salvata!")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# CSS & HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _inject_cfo_css():
    st.markdown(f"""
    <style>
    /* ─ KPI Cards ─ */
    .cfo-kpi-row {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 14px;
        margin-bottom: 14px;
    }}
    .cfo-kpi-card {{
        background: #0F1923;
        border: 1px solid rgba(255,255,255,0.06);
        border-top: 3px solid {C["blue"]};
        border-radius: 12px;
        padding: 16px 18px;
        position: relative;
        overflow: hidden;
    }}
    .cfo-kpi-card::after {{
        content: '';
        position: absolute;
        top: 0; right: 0;
        width: 60px; height: 60px;
        background: radial-gradient(circle at top right, rgba(255,255,255,0.03), transparent);
    }}
    .cfo-kpi-label {{
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #475569;
        font-weight: 700;
        margin-bottom: 8px;
    }}
    .cfo-kpi-value {{
        font-size: 1.5rem;
        font-weight: 700;
        color: #F1F5F9;
        letter-spacing: -0.5px;
        line-height: 1;
        margin-bottom: 6px;
    }}
    .cfo-kpi-delta {{
        font-size: 11.5px;
        font-weight: 600;
    }}
    .cfo-kpi-bud {{
        font-size: 11px;
        font-weight: 500;
        margin-top: 3px;
    }}
    .cfo-kpi-bench {{
        font-size: 10px;
        color: #475569;
        margin-top: 4px;
    }}

    /* ─ Chat ─ */
    .chat-user {{
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 14px 18px;
        margin: 10px 0;
    }}
    .chat-ai {{
        background: rgba(30,58,110,0.2);
        border: 1px solid rgba(201,168,76,0.15);
        border-radius: 10px;
        padding: 16px 20px;
        margin: 10px 0;
    }}
    .chat-ai.streaming {{
        border-color: rgba(201,168,76,0.3);
    }}
    .chat-label-user {{
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #475569;
        font-weight: 700;
        margin-bottom: 8px;
    }}
    .chat-label-ai {{
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: {C["gold"]};
        font-weight: 700;
        margin-bottom: 8px;
    }}
    .chat-text {{
        color: #CBD5E8;
        font-size: 0.88rem;
        line-height: 1.75;
    }}

    /* ─ Report preview ─ */
    .report-preview {{
        background: #0F1923;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 24px 28px;
        max-height: 700px;
        overflow-y: auto;
        font-size: 0.86rem;
        line-height: 1.75;
        color: #94A3B8;
        margin: 12px 0;
    }}
    .report-preview .section {{ background: #152030; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 16px 20px; margin: 12px 0; }}
    .report-preview .section-title {{ font-size: 9px; text-transform: uppercase; letter-spacing: 2px; color: {C["gold"]}; font-weight: 700; margin-bottom: 10px; }}
    .report-preview .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px,1fr)); gap: 10px; margin: 12px 0; }}
    .report-preview .kpi-card {{ background: #1A2744; border-radius: 8px; padding: 12px; border-top: 2px solid {C["gold"]}; }}
    .report-preview strong {{ color: #E2E8F0; }}
    .report-preview h2, .report-preview h3 {{ color: #E2E8F0; }}
    .report-preview .alert.red {{ background: rgba(239,68,68,0.08); border-left: 3px solid #EF4444; padding: 10px 14px; border-radius: 6px; color: #FCA5A5; }}
    .report-preview .alert.yellow {{ background: rgba(245,158,11,0.08); border-left: 3px solid #F59E0B; padding: 10px 14px; border-radius: 6px; color: #FCD34D; }}
    .report-preview .action-item {{ display: flex; gap: 12px; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }}
    .report-preview .badge-urgent {{ background: rgba(239,68,68,0.15); color: #EF4444; padding: 3px 8px; border-radius: 4px; font-size: 9px; }}
    .report-preview .badge-short {{ background: rgba(245,158,11,0.15); color: #F59E0B; padding: 3px 8px; border-radius: 4px; font-size: 9px; }}
    .report-preview .scenario-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin: 12px 0; }}
    .report-preview .scenario-card {{ background: #1A2744; border-radius: 8px; padding: 12px; text-align: center; }}
    .report-preview .scenario-base {{ border-top: 2px solid #3B82F6; }}
    .report-preview .scenario-opt {{ border-top: 2px solid #10B981; }}
    .report-preview .scenario-pess {{ border-top: 2px solid #EF4444; }}

    /* ─ Live report box ─ */
    .live-report-box {{
        background: #0F1923;
        border: 1px solid rgba(201,168,76,0.2);
        border-radius: 10px;
        padding: 16px 20px;
        max-height: 300px;
        overflow-y: auto;
        font-size: 0.8rem;
        line-height: 1.6;
        color: #64748B;
    }}

    /* ─ DuPont ─ */
    .dupont-box {{
        display: flex;
        align-items: center;
        gap: 8px;
        background: #0F1923;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 20px;
        margin: 12px 0;
    }}
    .dp-col {{
        flex: 1;
        background: #152030;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }}
    .dp-label {{ font-size: 9px; text-transform: uppercase; letter-spacing: 1.5px; color: #475569; font-weight: 700; margin-bottom: 6px; }}
    .dp-val   {{ font-size: 1.5rem; font-weight: 700; letter-spacing: -0.5px; }}
    .dp-sub   {{ font-size: 9.5px; color: #475569; margin-top: 4px; line-height: 1.4; }}
    .dp-op    {{ font-size: 1.2rem; font-weight: 700; color: #475569; flex-shrink: 0; }}

    /* ─ Info callout ─ */
    .info-callout {{
        background: rgba(30,58,110,0.15);
        border-left: 3px solid rgba(59,130,246,0.4);
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        font-size: 0.82rem;
        color: #64748B;
        margin-bottom: 16px;
        line-height: 1.6;
    }}
    .info-callout b {{ color: #E2E8F0; }}

    /* ─ Section header ─ */
    .section-header {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 2.5px;
        color: {C["gold"]};
        font-weight: 700;
        margin-bottom: 20px;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(201,168,76,0.12);
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    /* ─ Quick buttons ─ */
    [data-testid="stSidebar"] ~ div .stButton > button:not([kind="primary"]) {{
        font-size: 0.78rem !important;
        padding: 6px 10px !important;
    }}
    </style>
    """, unsafe_allow_html=True)


def _header_cfo(ca):
    api_ok = bool(get_api_key())
    badge_api = (
        f"<span style='background:rgba(16,185,129,0.15);color:{C['green']};padding:3px 10px;"
        f"border-radius:4px;font-size:0.7rem;font-weight:700'>● CLAUDE OPUS 4 ATTIVO</span>"
        if api_ok else
        f"<span style='background:rgba(239,68,68,0.15);color:{C['red']};padding:3px 10px;"
        f"border-radius:4px;font-size:0.7rem;font-weight:700'>● API KEY MANCANTE</span>"
    )
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#04080F 0%,#0A1628 45%,#1A3A6E 80%,#0A1628 100%);
                border-radius:16px;padding:28px 36px;margin-bottom:24px;
                border:1px solid rgba(201,168,76,0.18);
                box-shadow:0 8px 32px rgba(0,0,0,0.5),0 0 0 1px rgba(201,168,76,0.05) inset'>
        <div style='display:flex;justify-content:space-between;align-items:flex-start'>
            <div>
                <div style='font-size:9px;text-transform:uppercase;letter-spacing:4px;
                            color:{C["gold"]};font-weight:700;margin-bottom:10px;
                            display:flex;align-items:center;gap:10px'>
                    <div style='width:20px;height:1px;background:{C["gold"]}'></div>
                    SUPER AGENTE CFO AI · AI-MANAGER PLATFORM
                    <div style='width:20px;height:1px;background:{C["gold"]}'></div>
                </div>
                <h2 style='color:#F8FAFC;margin:0;font-size:1.6rem;font-weight:700;
                           letter-spacing:-0.5px;line-height:1.2'>
                    🏦 Virtual CFO — {ca}
                </h2>
                <p style='color:{C["muted"]};margin:10px 0 0;font-size:0.8rem;line-height:1.6;
                          max-width:600px'>
                    EBITDA Bridge · DuPont Decomposition · McKinsey/BCG/HBS/CIMA Framework<br>
                    Analisi Anomalie Statistiche · Report AI · Market Intelligence · Email Delivery
                </p>
            </div>
            <div style='text-align:right;flex-shrink:0'>
                {badge_api}
                <div style='font-size:0.7rem;color:{C["muted"]};margin-top:8px'>
                    {datetime.now().strftime('%d %B %Y')}
                </div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)


def _prereq_card(df_piano, df_db, df_ricl, mapping):
    stati = [
        ("Piano dei Conti caricato",  df_piano is not None),
        ("DB Contabile caricato",     df_db is not None),
        ("Schema Riclassifica caricato", df_ricl is not None),
        ("Mappatura conti configurata",  bool(mapping)),
    ]
    muted = C['muted']
    def _prereq_row(label, ok):
        sym = '✅' if ok else '❌'
        return (f"<div style='padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.04);"
                f"font-size:0.84rem;color:{muted}'>"
                f"{sym} {label}</div>")
    righe = "".join(_prereq_row(l, o) for l, o in stati)
    st.markdown(f"""
    <div style='background:rgba(201,168,76,0.04);border:1px solid rgba(201,168,76,0.2);
                border-radius:14px;padding:24px 28px;margin:16px 0'>
        <div style='color:{C["gold"]};font-weight:700;font-size:0.95rem;margin-bottom:16px'>
            ⚠️ Prerequisiti mancanti per il CFO Agent
        </div>
        {righe}
        <div style='margin-top:16px;font-size:0.82rem;color:{C["muted"]}'>
            Vai nel menu → <b style='color:{C["text"]}'>🗂️ Workspace Dati</b> per completare la configurazione.
        </div>
    </div>""", unsafe_allow_html=True)


def _page_no_cliente():
    st.markdown("## 🏦 CFO Agent")
    st.info("👋 Seleziona un cliente dalla sidebar per attivare il CFO Agent.")
