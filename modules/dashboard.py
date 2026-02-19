"""
dashboard.py — Dashboard CE riclassificato premium.
Design: clean corporate con Plotly dark theme.
BUG FIX: KeyError su melt risolto con costruzione esplicita df_melted.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from services.data_utils import get_cliente, save_cliente, fmt_eur, fmt_pct
from services.riclassifica import costruisci_ce_riclassificato, get_mesi_disponibili, calcola_kpi_finanziari

PALETTE = ['#1A3A7A','#10B981','#C9A84C','#EF4444','#8B5CF6','#F59E0B','#06B6D4','#EC4899','#14B8A6','#6366F1']

PLOTLY_BASE = dict(
    plot_bgcolor='white', paper_bgcolor='white',
    font=dict(family='DM Sans, Inter, -apple-system, sans-serif', color='#374151', size=11),
    legend=dict(bgcolor='rgba(255,255,255,0)', bordercolor='#E2E8F0',
                orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0,
                font=dict(size=10)),
    margin=dict(l=0, r=0, t=50, b=0),
    hoverlabel=dict(bgcolor='white', bordercolor='#1A3A7A', font_color='#1A3A7A',
                    font_family='DM Sans, sans-serif'),
)


def render_dashboard():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        _empty_state(); return

    cliente = get_cliente()
    if not cliente:
        _empty_state(); return

    df_db      = cliente.get('df_db')
    df_piano   = cliente.get('df_piano')
    df_ricl    = cliente.get('df_ricl')
    mapping    = cliente.get('mapping', {})
    rettifiche = cliente.get('rettifiche', [])
    budget     = cliente.get('budget', {})
    schema_att = cliente.get('schema_attivo', '')
    schema_cfg = cliente.get('schemi', {}).get(schema_att, {})

    if df_db is None or df_piano is None or df_ricl is None:
        st.markdown(f"""
        <div style='background:#EEF2FF;border-left:4px solid #1A3A7A;padding:16px 20px;
                    border-radius:0 10px 10px 0;margin:16px 0;font-size:0.9rem'>
            <b>👋 Inizia dal Workspace</b> — Carica i tre file (Piano Conti, DB Contabile, Schema Riclassifica)
            e configura la mappatura per vedere la Dashboard.
        </div>""", unsafe_allow_html=True)
        return

    if not mapping:
        st.warning("⚠️ Nessuna mappatura configurata. Vai in **Workspace → Mappatura Conti**.")
        return

    with st.spinner("⚙️ Elaborazione dati…"):
        pivot, dettaglio, errore = costruisci_ce_riclassificato(
            df_db, df_piano, df_ricl, mapping, schema_cfg, rettifiche
        )

    if errore:
        st.error(f"❌ {errore}"); return

    mesi = get_mesi_disponibili(pivot)
    if not mesi:
        st.warning("⚠️ Nessun dato mensile disponibile."); return

    # ── HEADER ────────────────────────────────────────────────────────────────
    col_h, col_s = st.columns([5, 2])
    with col_h:
        st.markdown(f"## 📊 Dashboard Controllo di Gestione")
        st.markdown(f"<div style='color:#6B7280;font-size:0.82rem;margin-top:-10px'>{ca} &nbsp;·&nbsp; {len(mesi)} mesi di dati &nbsp;·&nbsp; Aggiornato ora</div>", unsafe_allow_html=True)
    with col_s:
        if schema_att:
            st.markdown(f"<div style='text-align:right;padding-top:20px;font-size:0.78rem;color:#9CA3AF'>Schema: <b style='color:#374151'>{schema_att}</b></div>", unsafe_allow_html=True)

    # ── FILTRI ────────────────────────────────────────────────────────────────
    with st.expander("🔍 Filtri & Confronto", expanded=True):
        c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
        with c1:
            modalita = st.selectbox("Periodo:", ["Mese singolo","Range mesi","YTD","Anno completo"], key="d_mod")
        with c2:
            anni = sorted(set(m[:4] for m in mesi), reverse=True)
            if modalita == "Mese singolo":
                mese_s = st.selectbox("Mese:", mesi, index=len(mesi)-1, key="d_mese")
                mesi_filtro = [mese_s]
            elif modalita == "Range mesi":
                sel = st.multiselect("Mesi:", mesi, default=mesi[-3:], key="d_range")
                mesi_filtro = sel or mesi[-3:]
            elif modalita == "YTD":
                anno_y = st.selectbox("Anno:", anni, key="d_ytd")
                mesi_filtro = [m for m in mesi if m.startswith(str(anno_y))]
            else:
                anno_y = st.selectbox("Anno:", anni, key="d_ay")
                mesi_filtro = [m for m in mesi if m.startswith(str(anno_y))]
        with c3:
            anno_conf = st.selectbox("Confronta vs:", ['— nessuno —'] + anni, key="d_conf")
        with c4:
            mostra_bud = st.checkbox("Budget", value=bool(budget), key="d_bud")

    cols_filtro = [c for c in mesi_filtro if c in pivot.columns]
    if not cols_filtro:
        st.warning("Nessun dato per il periodo."); return

    # Dati confronto
    pf      = pivot[cols_filtro].copy()
    pf['_PERIODO'] = pf.sum(axis=1)

    pf_conf = None
    if anno_conf != '— nessuno —':
        mesi_num = {m[5:] for m in cols_filtro}
        cols_conf_raw = [c for c in pivot.columns if c[:4] == anno_conf and c[5:] in mesi_num]
        if cols_conf_raw:
            pf_conf = pivot[cols_conf_raw].copy()
            pf_conf['_PERIODO'] = pf_conf.sum(axis=1)

    kpi = calcola_kpi_finanziari(pivot, cols_filtro)
    kpi_conf = calcola_kpi_finanziari(pivot, [c for c in pivot.columns if c[:4] == anno_conf and c[5:] in {m[5:] for m in cols_filtro}]) if anno_conf != '— nessuno —' else {}

    # ── ALERT BUDGET ──────────────────────────────────────────────────────────
    if mostra_bud and budget:
        _render_budget_alerts(pf, budget, cols_filtro)

    # ── KPI CARDS ─────────────────────────────────────────────────────────────
    _render_kpi_cards(kpi, kpi_conf, anno_conf)

    st.markdown("<hr style='border-color:#F1F5F9;margin:20px 0'>", unsafe_allow_html=True)

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab_ce, tab_grafici, tab_budget = st.tabs(["📋 Conto Economico", "📈 Grafici & Analisi", "🎯 Budget"])

    with tab_ce:
        _render_tabella_ce(ca, pf, dettaglio, cols_filtro, pf_conf, anno_conf, mostra_bud, budget, mesi_filtro)

    with tab_grafici:
        _render_grafici(pivot, mesi, kpi)

    with tab_budget:
        from modules.budget import render_budget_inline
        render_budget_inline(cliente, pivot, mesi, ca)


# ─────────────────────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────────────────────

def _render_kpi_cards(kpi, kpi_conf, anno_conf):
    def card(label, val, unit, color, conf_val):
        if val is None:
            return f"""<div class='dash-kpi-card' style='border-left-color:#CBD5E1;opacity:.5'>
                <div class='dkc-label'>{label}</div>
                <div class='dkc-value' style='color:#CBD5E1'>—</div>
            </div>"""
        v_fmt = f"{val:.1f}{unit}" if unit == '%' else fmt_eur(val)
        delta_html = ""
        if conf_val is not None and conf_val != 0:
            delta_pct = (val - conf_val) / abs(conf_val) * 100
            clr = '#059669' if delta_pct >= 0 else '#DC2626'
            sym = '▲' if delta_pct >= 0 else '▼'
            delta_html = f"<div class='dkc-delta' style='color:{clr}'>{sym} {abs(delta_pct):.1f}% vs {anno_conf}</div>"
        return f"""<div class='dash-kpi-card' style='border-left-color:{color}'>
            <div class='dkc-label'>{label}</div>
            <div class='dkc-value' style='color:{color}'>{v_fmt}</div>
            {delta_html}
        </div>"""

    kpi_defs = [
        ('Ricavi Netti',   kpi.get('ricavi'),        '€',  '#1A3A7A', kpi_conf.get('ricavi')),
        ('EBITDA / MOL',  kpi.get('ebitda'),        '€',  '#059669', kpi_conf.get('ebitda')),
        ('EBITDA Margin', kpi.get('ebitda_margin'), '%', '#7C3AED',  kpi_conf.get('ebitda_margin')),
        ('Risultato Netto',kpi.get('utile_netto'),  '€',  '#DC2626', kpi_conf.get('utile_netto')),
    ]

    cards_html = "".join(card(*d) for d in kpi_defs)
    st.markdown(f"""
    <style>
    .dash-kpi-row {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:20px; }}
    .dash-kpi-card {{ background:white; border-radius:12px; padding:16px 18px;
                      box-shadow:0 1px 8px rgba(0,0,0,.07); border-left:4px solid #1A3A7A;
                      transition:transform .15s, box-shadow .15s; }}
    .dash-kpi-card:hover {{ transform:translateY(-2px); box-shadow:0 4px 16px rgba(0,0,0,.1); }}
    .dkc-label {{ font-size:0.7rem; text-transform:uppercase; letter-spacing:1px; color:#8896AB; font-weight:700; margin-bottom:6px; }}
    .dkc-value {{ font-size:1.45rem; font-weight:700; color:#0F2044; letter-spacing:-0.5px; margin-bottom:4px; }}
    .dkc-delta {{ font-size:0.78rem; font-weight:600; }}
    </style>
    <div class='dash-kpi-row'>{cards_html}</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TABELLA CE — 2 livelli con drill-down
# ─────────────────────────────────────────────────────────────────────────────

def _render_tabella_ce(ca, pf, dettaglio, cols_filtro, pf_conf, anno_conf, mostra_bud, budget, mesi_filtro):
    st.markdown("### 📋 Conto Economico Riclassificato")
    st.markdown("""
    <div style='font-size:0.79rem;color:#6B7280;margin-bottom:16px;padding:10px 14px;
                background:#F8FAFC;border-radius:6px;border-left:3px solid #CBD5E8'>
    💡 Clicca su <b>▶ una voce</b> per espandere il dettaglio dei singoli conti contabili.
    I valori mensili sono visibili nella riga di riepilogo.
    </div>""", unsafe_allow_html=True)

    def fmt(v, zero_dash=True):
        try:
            fv = float(v)
            if zero_dash and fv == 0:
                return "—"
            s = f"{abs(fv):>12,.0f}".replace(',','X').replace('.',',').replace('X','.')
            return f"({s} €)" if fv < 0 else f"{s} €"
        except Exception:
            return str(v)

    for voce in pf.index:
        val_tot = float(pf.loc[voce, '_PERIODO']) if '_PERIODO' in pf.columns else 0
        val_fmt = fmt(val_tot)

        # Colore basato su segno
        color_val = '#059669' if val_tot > 0 else ('#DC2626' if val_tot < 0 else '#6B7280')

        with st.expander(f"**{voce}**  —  {val_fmt}", expanded=False):
            # Riga riepilogo mensile
            row_data = {}
            for c in cols_filtro:
                if c in pf.columns:
                    row_data[c.replace('-','\u2011')] = fmt(pf.loc[voce, c])
            row_data['▶ TOTALE PERIODO'] = val_fmt

            if pf_conf is not None and voce in pf_conf.index:
                val_c = float(pf_conf.loc[voce, '_PERIODO']) if '_PERIODO' in pf_conf.columns else 0
                delta_a = val_tot - val_c
                delta_p = (delta_a / abs(val_c) * 100) if val_c != 0 else 0
                row_data[f'Conf. {anno_conf}'] = fmt(val_c)
                row_data['Δ Assoluto'] = fmt(delta_a)
                row_data['Δ %'] = f"{delta_p:+.1f}%"

            if mostra_bud and budget and voce in budget:
                bud_tot = sum(budget[voce].get(m, 0) for m in cols_filtro)
                row_data['Budget'] = fmt(bud_tot)
                row_data['Scostamento'] = fmt(val_tot - bud_tot)

            df_row = pd.DataFrame([row_data])
            st.dataframe(df_row, use_container_width=True, hide_index=True)

            # Dettaglio conti
            if voce in dettaglio and not dettaglio[voce].empty:
                st.markdown("**Dettaglio per conto:**")
                det = dettaglio[voce]
                cols_det = [c for c in cols_filtro if c in det.columns] + ['TOTALE']
                det_show = det[[c for c in cols_det if c in det.columns]].copy()
                det_show_fmt = det_show.applymap(lambda x: fmt(x) if isinstance(x, (int, float)) else str(x))
                st.dataframe(
                    det_show_fmt,
                    use_container_width=True,
                    height=min(38*len(det_show)+40, 320)
                )

    # Export
    st.markdown("---")
    export_df = pf[[c for c in cols_filtro if c in pf.columns] + ['_PERIODO']].copy()
    export_df = export_df.rename(columns={'_PERIODO': 'TOTALE PERIODO'})
    csv = export_df.to_csv(decimal=',', sep=';').encode('utf-8-sig')
    st.download_button("⬇️ Esporta CE (CSV)", data=csv,
                       file_name=f"CE_{ca}_{'-'.join(mesi_filtro[:2])}.csv", mime="text/csv")


# ─────────────────────────────────────────────────────────────────────────────
# GRAFICI — BUG FIXED + ENHANCED
# ─────────────────────────────────────────────────────────────────────────────

def _render_grafici(pivot, mesi, kpi):
    st.markdown("### 📈 Analisi Grafici & Trend")

    voci = list(pivot.index)
    cols_mesi = [c for c in mesi if c in pivot.columns]
    if not cols_mesi:
        st.info("Nessun dato temporale."); return

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        voci_sel = st.multiselect("Voci da visualizzare:", voci,
            default=voci[:min(4, len(voci))], key="g_voci")
    with c2:
        tipo = st.radio("Tipo:", ["Linee", "Barre", "Stacked", "Area"], horizontal=True, key="g_tipo")
    with c3:
        n_m = st.slider("Mesi:", 3, len(cols_mesi), min(12, len(cols_mesi)), key="g_nm")

    mesi_plot = cols_mesi[-n_m:]

    if not voci_sel:
        st.info("Seleziona almeno una voce."); return

    # ── BUG FIX: costruzione df_melted row-by-row, NO transpose+melt ─────────
    rows = []
    for voce in voci_sel:
        if voce not in pivot.index:
            continue
        for m in mesi_plot:
            if m in pivot.columns:
                rows.append({
                    'Mese':    m,
                    'Voce':    str(voce)[:30],
                    'Importo': float(pivot.loc[voce, m]),
                })
    if not rows:
        st.info("Nessun dato per le voci e il periodo selezionati."); return

    df_m = pd.DataFrame(rows)
    color_map = {str(v)[:30]: PALETTE[i % len(PALETTE)] for i, v in enumerate(voci_sel)}

    if tipo == "Linee":
        fig = px.line(df_m, x='Mese', y='Importo', color='Voce',
                      markers=True, color_discrete_map=color_map)
        fig.update_traces(line=dict(width=2.5), marker=dict(size=7, line=dict(width=2, color='white')))
    elif tipo == "Barre":
        fig = px.bar(df_m, x='Mese', y='Importo', color='Voce',
                     barmode='group', color_discrete_map=color_map)
    elif tipo == "Stacked":
        fig = px.bar(df_m, x='Mese', y='Importo', color='Voce',
                     barmode='stack', color_discrete_map=color_map)
    else:  # Area
        fig = px.area(df_m, x='Mese', y='Importo', color='Voce',
                      color_discrete_map=color_map)

    fig.update_layout(
        **PLOTLY_BASE, height=380,
        xaxis=dict(showgrid=False, tickangle=-30, title='', color='#6B7280',
                   tickfont=dict(size=10), linecolor='#E2E8F0'),
        yaxis=dict(showgrid=True, gridcolor='#F8FAFC', tickformat=',.0f', ticksuffix=' €',
                   color='#6B7280', tickfont=dict(size=10), title=''),
        bargap=0.2,
    )
    fig.update_traces(hovertemplate='<b>%{x}</b><br>%{y:,.0f} €<extra>%{fullData.name}</extra>')
    st.plotly_chart(fig, use_container_width=True)

    # ── 2 colonne: Waterfall + Trend ultimi 3m ────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 🌊 Waterfall Mensile")
        voce_wf = st.selectbox("Voce:", voci, key="wf_voce_sel")
        if voce_wf in pivot.index:
            vals_wf = [float(pivot.loc[voce_wf, m]) for m in mesi_plot]
            fig_wf = go.Figure(go.Waterfall(
                orientation='v', x=mesi_plot, y=vals_wf,
                connector=dict(line=dict(color='#E2E8F0', width=1)),
                increasing=dict(marker=dict(color='#059669', line=dict(width=0))),
                decreasing=dict(marker=dict(color='#DC2626', line=dict(width=0))),
                totals=dict(marker=dict(color='#1A3A7A', line=dict(width=0))),
            ))
            fig_wf.update_layout(
                **PLOTLY_BASE, height=310,
                xaxis=dict(showgrid=False, tickangle=-30, color='#6B7280', tickfont=dict(size=9)),
                yaxis=dict(showgrid=True, gridcolor='#F8FAFC', tickformat=',.0f', ticksuffix=' €',
                           color='#6B7280', tickfont=dict(size=9)),
                margin=dict(l=0, r=0, t=20, b=0),
            )
            st.plotly_chart(fig_wf, use_container_width=True)

    with col_b:
        st.markdown("#### 📊 Composizione Periodo")
        mese_pie = st.selectbox("Mese:", mesi_plot, index=len(mesi_plot)-1, key="pie_mese")
        if mese_pie in pivot.columns:
            vals_pie = {str(v)[:25]: float(pivot.loc[v, mese_pie]) for v in voci_sel if v in pivot.index}
            pos_pie = {k: v for k, v in vals_pie.items() if v > 0}
            if pos_pie:
                fig_pie = go.Figure(go.Pie(
                    labels=list(pos_pie.keys()),
                    values=list(pos_pie.values()),
                    marker=dict(colors=PALETTE[:len(pos_pie)], line=dict(color='white', width=2)),
                    textposition='inside', textinfo='percent+label',
                    insidetextfont=dict(size=10),
                    hovertemplate='<b>%{label}</b><br>%{value:,.0f} €<br>%{percent}<extra></extra>',
                    hole=0.35,
                ))
                fig_pie.update_layout(
                    **PLOTLY_BASE, height=310,
                    showlegend=False,
                    margin=dict(l=0, r=0, t=20, b=0),
                )
                st.plotly_chart(fig_pie, use_container_width=True)

    # ── Heatmap ──────────────────────────────────────────────────────────────
    if len(voci_sel) > 2:
        st.markdown("#### 🗺️ Heatmap — Intensità Voci × Mesi")
        hm = pivot.loc[voci_sel, [m for m in mesi_plot if m in pivot.columns]]
        hm_norm = hm.div(hm.abs().max(axis=1).replace(0, 1), axis=0)
        fig_hm = px.imshow(
            hm_norm.values,
            labels=dict(x="Mese", y="Voce", color="Intensità normalizzata"),
            x=list(hm_norm.columns),
            y=[str(v)[:30] for v in hm_norm.index],
            color_continuous_scale=[[0,'#FECACA'],[0.5,'#EEF2FF'],[1,'#1A3A7A']],
            aspect='auto',
            text_auto=False,
        )
        fig_hm.update_traces(
            text=[[f"{v:,.0f}€" for v in row] for row in hm.values],
            texttemplate="%{text}",
            textfont=dict(size=9, color='#374151'),
        )
        fig_hm.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            margin=dict(l=0, r=0, t=20, b=10),
            xaxis=dict(tickangle=-30, tickfont=dict(size=9), color='#6B7280'),
            yaxis=dict(tickfont=dict(size=9), color='#6B7280'),
            height=max(220, 45*len(voci_sel)+60),
            font=dict(family='DM Sans, sans-serif', size=10),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_hm, use_container_width=True)

    # ── Margini mensili ──────────────────────────────────────────────────────
    st.markdown("#### 📉 Evoluzione Margini Mensili")
    margin_rows = []
    for m in mesi_plot:
        kpi_m = calcola_kpi_finanziari(pivot, [m])
        for k, label, color in [
            ('ebitda_margin', 'EBITDA Margin', '#059669'),
            ('net_margin',    'Net Margin',    '#1A3A7A'),
            ('cost_labor_pct','% Personale/Ricavi', '#DC2626'),
        ]:
            v = kpi_m.get(k)
            if v is not None:
                margin_rows.append({'Mese': m, 'KPI': label, 'Valore': v})

    if margin_rows:
        df_marg = pd.DataFrame(margin_rows)
        color_disc = {'EBITDA Margin': '#059669', 'Net Margin': '#1A3A7A', '% Personale/Ricavi': '#DC2626'}
        fig_marg = px.line(df_marg, x='Mese', y='Valore', color='KPI',
                           markers=True, color_discrete_map=color_disc)
        fig_marg.add_hline(y=0, line_dash='dot', line_color='#CBD5E1')
        fig_marg.update_traces(line=dict(width=2.5), marker=dict(size=7, line=dict(width=2, color='white')))
        fig_marg.update_layout(
            **PLOTLY_BASE, height=280,
            yaxis=dict(ticksuffix='%', showgrid=True, gridcolor='#F8FAFC', color='#6B7280',
                       title='', tickfont=dict(size=10), zerolinecolor='#CBD5E1'),
            xaxis=dict(showgrid=False, tickangle=-30, color='#6B7280', title='', tickfont=dict(size=10)),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        fig_marg.update_traces(hovertemplate='<b>%{x}</b><br>%{y:.1f}%<extra>%{fullData.name}</extra>')
        st.plotly_chart(fig_marg, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# ALERT BUDGET
# ─────────────────────────────────────────────────────────────────────────────

def _render_budget_alerts(pf, budget, cols_filtro):
    alert_list = []
    for voce in pf.index:
        if voce not in budget:
            continue
        val_eff = float(pf.loc[voce, '_PERIODO']) if '_PERIODO' in pf.columns else sum(float(pf.loc[voce, c]) for c in cols_filtro if c in pf.columns)
        val_bud = sum(budget[voce].get(m, 0) for m in cols_filtro)
        if val_bud == 0:
            continue
        scost_pct = (val_eff - val_bud) / abs(val_bud) * 100
        if abs(scost_pct) >= 15:
            alert_list.append((voce, val_eff, val_bud, scost_pct))

    if not alert_list:
        return

    st.markdown("#### ⚠️ Alert Scostamenti Budget")
    n_cols = min(len(alert_list), 3)
    cols = st.columns(n_cols)
    for i, (voce, eff, bud, pct) in enumerate(alert_list[:6]):
        with cols[i % n_cols]:
            color = '#DC2626' if pct < 0 else '#D97706'
            bg    = '#FEF2F2' if pct < 0 else '#FFFBEB'
            sym   = '▼' if pct < 0 else '▲'
            st.markdown(f"""
            <div style='background:{bg};border-left:4px solid {color};border-radius:8px;
                        padding:12px 14px;margin-bottom:10px'>
                <div style='font-size:0.7rem;font-weight:700;color:{color};text-transform:uppercase;
                            letter-spacing:.7px'>{sym} Alert Budget</div>
                <div style='font-weight:600;font-size:0.86rem;margin:4px 0;color:#1F2937'>{voce[:30]}</div>
                <div style='font-size:0.8rem;color:#374151'>
                    Effettivo: <b>{fmt_eur(eff)}</b><br>
                    Budget: {fmt_eur(bud)}<br>
                    <span style='color:{color};font-weight:700'>{pct:+.1f}%</span>
                </div>
            </div>""", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#F1F5F9;margin:16px 0'>", unsafe_allow_html=True)


def _empty_state():
    st.markdown("## 📊 Dashboard")
    st.info("👋 Seleziona un cliente dalla sidebar e carica i dati nel Workspace per visualizzare la Dashboard.")
