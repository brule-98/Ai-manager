import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from services.data_utils import get_cliente, fmt_eur
from services.riclassifica import costruisci_ce_riclassificato, get_mesi_disponibili


def render_dashboard():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        _render_empty()
        return

    cliente = get_cliente()
    if cliente is None:
        _render_empty()
        return

    df_db = cliente.get('df_db')
    df_piano = cliente.get('df_piano')
    df_ricl = cliente.get('df_ricl')
    mapping = cliente.get('mapping', {})
    schema_config = cliente.get('schemi', {}).get(cliente.get('schema_attivo', ''), {})
    rettifiche = cliente.get('rettifiche', [])

    if df_db is None or df_piano is None or df_ricl is None:
        st.info("👋 Carica i dati nel **Workspace Dati** per visualizzare la dashboard.")
        _render_placeholder()
        return

    if not mapping:
        st.warning("⚠️ Nessuna mappatura configurata. Vai nel **Workspace → Mappatura Conti**.")
        return

    # Costruisci CE
    pivot, errore = costruisci_ce_riclassificato(
        df_db, df_piano, df_ricl, mapping, schema_config, rettifiche
    )

    if errore:
        st.error(f"Errore nella costruzione del CE: {errore}")
        return

    mesi_disponibili = get_mesi_disponibili(pivot)

    # ── HEADER DASHBOARD ─────────────────────────────────────────────────────
    st.markdown(f"## 📊 Dashboard — {ca}")

    # ── FILTRI ───────────────────────────────────────────────────────────────
    with st.container():
        st.markdown("""
        <div style='background:white; border-radius:12px; padding:1rem 1.5rem; box-shadow:0 1px 4px rgba(0,0,0,0.07); margin-bottom:1.2rem;'>
        <div class='section-title'>🔍 Filtri di Visualizzazione</div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns([2, 2, 1])

        with c1:
            modalita = st.selectbox(
                "Modalità:",
                ["Mensile (singolo mese)", "Periodo (range mesi)", "YTD (anno progressivo)", "Anno completo"],
                key="dash_modalita"
            )

        with c2:
            if mesi_disponibili:
                if modalita == "Mensile (singolo mese)":
                    mese_sel = st.selectbox("Mese:", mesi_disponibili, index=len(mesi_disponibili) - 1,
                                             key="dash_mese_singolo")
                    mesi_filtro = [mese_sel]
                elif modalita == "Periodo (range mesi)":
                    sel = st.multiselect("Mesi:", mesi_disponibili, default=mesi_disponibili[-3:],
                                          key="dash_mesi_multi")
                    mesi_filtro = sel if sel else mesi_disponibili
                elif modalita == "YTD (anno progressivo)":
                    anni_disp = sorted(list(set(m[:4] for m in mesi_disponibili)), reverse=True)
                    anno_ytd = st.selectbox("Anno:", anni_disp, key="dash_anno_ytd")
                    mesi_filtro = [m for m in mesi_disponibili if m.startswith(str(anno_ytd))]
                else:  # Anno completo
                    anni_disp = sorted(list(set(m[:4] for m in mesi_disponibili)), reverse=True)
                    anno_sel = st.selectbox("Anno:", anni_disp, key="dash_anno_comp")
                    mesi_filtro = [m for m in mesi_disponibili if m.startswith(str(anno_sel))]
            else:
                mesi_filtro = []

        with c3:
            confronto = st.checkbox("Confronto periodo precedente", value=False, key="dash_confronto")

        st.markdown("</div>", unsafe_allow_html=True)

    # ── CALCOLO DATI FILTRATI ────────────────────────────────────────────────
    cols_filtro = [c for c in mesi_filtro if c in pivot.columns]
    if not cols_filtro:
        st.warning("Nessun dato per il periodo selezionato.")
        return

    pivot_filtrato = pivot[cols_filtro].copy()
    pivot_filtrato['TOTALE PERIODO'] = pivot_filtrato.sum(axis=1)

    # KPI sommari (prime voci chiave)
    _render_kpi(pivot_filtrato, pivot, mesi_filtro, mesi_disponibili)

    st.markdown("---")

    # ── TABELLA CE ────────────────────────────────────────────────────────────
    tab_report, tab_grafici = st.tabs(["📋 Report Tabellare", "📈 Analisi Grafici"])

    with tab_report:
        _render_tabella_ce(pivot_filtrato, schema_config, cols_filtro)

    with tab_grafici:
        _render_grafici(pivot, mesi_disponibili, schema_config)


def _render_kpi(pivot_filtrato, pivot_full, mesi_filtro, mesi_disponibili):
    """Mostra i KPI principali in metric cards."""
    # Cerca voci significative (ricavi, margine, ebitda, utile)
    voci = list(pivot_filtrato.index)

    def cerca_voce(keywords):
        for k in keywords:
            for v in voci:
                if k.lower() in v.lower():
                    return v
        return None

    ricavi_v = cerca_voce(['ricav', 'fattur', 'vendite', 'revenue'])
    ebitda_v = cerca_voce(['ebitda', 'mol', 'margine operativo lordo'])
    ebit_v = cerca_voce(['ebit', 'reddito operativo', 'risultato operativo'])
    utile_v = cerca_voce(['utile', 'perdita', 'risultato netto', 'reddito netto'])

    cols = st.columns(4)
    kpi_data = [
        (ricavi_v, "Ricavi Netti", "#1A3A7A"),
        (ebitda_v, "EBITDA / MOL", "#059669"),
        (ebit_v, "EBIT", "#7C3AED"),
        (utile_v, "Risultato Netto", "#DC2626"),
    ]

    for i, (voce, label, color) in enumerate(kpi_data):
        with cols[i]:
            if voce and voce in pivot_filtrato.index:
                val = pivot_filtrato.loc[voce, 'TOTALE PERIODO']
                # Calcola confronto (stesso numero di mesi, periodo precedente)
                delta_str = ""
                try:
                    n_mesi = len(mesi_filtro)
                    idx_primo = mesi_disponibili.index(min(mesi_filtro))
                    if idx_primo >= n_mesi:
                        mesi_prec = mesi_disponibili[idx_primo - n_mesi: idx_primo]
                        cols_prec = [c for c in mesi_prec if c in pivot_full.columns]
                        if cols_prec and voce in pivot_full.index:
                            val_prec = pivot_full.loc[voce, cols_prec].sum()
                            if val_prec != 0:
                                delta_pct = (val - val_prec) / abs(val_prec) * 100
                                delta_str = f"<span class='{'delta-pos' if delta_pct >= 0 else 'delta-neg'}'>{'▲' if delta_pct >= 0 else '▼'} {abs(delta_pct):.1f}% vs periodo prec.</span>"
                except Exception:
                    pass

                st.markdown(f"""
                <div class='metric-card' style='border-left-color:{color}'>
                    <div class='label'>{label}</div>
                    <div class='value' style='color:{color}'>{fmt_eur(val)}</div>
                    {delta_str}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='metric-card' style='border-left-color:#CBD5E8; opacity:0.5'>
                    <div class='label'>{label}</div>
                    <div class='value' style='color:#CBD5E8'>—</div>
                </div>
                """, unsafe_allow_html=True)


def _render_tabella_ce(pivot_filtrato, schema_config, cols_filtro):
    """Render tabella CE riclassificato con formattazione."""
    st.markdown("#### Conto Economico Riclassificato")

    # Prepara dataframe per display
    df_display = pivot_filtrato.copy()

    # Formatta colonne numeriche
    fmt_cols = list(cols_filtro) + ['TOTALE PERIODO']
    fmt_cols = [c for c in fmt_cols if c in df_display.columns]

    # Applica grassetto alle voci totale/subtotale basato su config
    def style_row(row):
        voce = row.name
        is_subtotal = False
        if schema_config and voce in schema_config:
            is_subtotal = schema_config[voce].get('subtotale', False)
        if is_subtotal:
            return ['font-weight: bold; background-color: #EEF2FF; color: #0F2044'] * len(row)
        return [''] * len(row)

    # Format euro
    def fmt_cell(v):
        try:
            fv = float(v)
            s = f"{fv:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            if fv < 0:
                return f"({s.replace('-', '')} €)"
            return f"{s} €"
        except Exception:
            return str(v)

    styled = (
        df_display.style
        .apply(style_row, axis=1)
        .format(fmt_cell, subset=fmt_cols)
        .set_table_styles([
            {'selector': 'thead th', 'props': [
                ('background-color', '#0F2044'), ('color', 'white'),
                ('font-size', '0.75rem'), ('padding', '8px 12px'), ('text-align', 'right')
            ]},
            {'selector': 'td', 'props': [
                ('font-size', '0.82rem'), ('padding', '7px 12px'), ('text-align', 'right')
            ]},
            {'selector': 'th.row_heading', 'props': [
                ('font-size', '0.82rem'), ('text-align', 'left'), ('padding', '7px 12px'),
                ('min-width', '200px')
            ]},
        ])
    )

    st.dataframe(styled, use_container_width=True, height=500)

    # Export CSV
    csv = pivot_filtrato.to_csv(decimal=',', sep=';').encode('utf-8-sig')
    st.download_button(
        "⬇️ Esporta CSV",
        data=csv,
        file_name=f"CE_{st.session_state.get('cliente_attivo', 'cliente')}.csv",
        mime="text/csv"
    )


def _render_grafici(pivot, mesi_disponibili, schema_config):
    """Grafici di analisi trend."""
    st.markdown("#### Analisi Trend nel Tempo")

    if not mesi_disponibili:
        st.info("Nessun dato temporale disponibile.")
        return

    voci = list(pivot.index)

    c1, c2 = st.columns([2, 1])
    with c1:
        voci_sel = st.multiselect(
            "Voci da confrontare:",
            voci,
            default=voci[:3] if len(voci) >= 3 else voci,
            key="grafici_voci_sel"
        )
    with c2:
        tipo_grafico = st.radio("Tipo:", ["Barre", "Linee", "Barre Stacked"], horizontal=True, key="tipo_grafico")

    if not voci_sel:
        st.info("Seleziona almeno una voce.")
        return

    # Prepara dati per grafico
    cols_mesi = [c for c in mesi_disponibili if c in pivot.columns]
    df_plot = pivot.loc[voci_sel, cols_mesi].T.reset_index()
    df_plot.columns = ['Mese'] + voci_sel
    df_melted = df_plot.melt(id_vars='Mese', var_name='Voce', value_name='Importo')

    colors = ['#1A3A7A', '#059669', '#7C3AED', '#D97706', '#DC2626', '#0891B2', '#BE185D']

    if tipo_grafico == "Barre":
        fig = px.bar(
            df_melted, x='Mese', y='Importo', color='Voce',
            barmode='group',
            color_discrete_sequence=colors,
            labels={'Importo': 'Importo (€)', 'Mese': 'Periodo'}
        )
    elif tipo_grafico == "Linee":
        fig = px.line(
            df_melted, x='Mese', y='Importo', color='Voce',
            markers=True,
            color_discrete_sequence=colors,
            labels={'Importo': 'Importo (€)', 'Mese': 'Periodo'}
        )
        fig.update_traces(line=dict(width=2.5))
    else:  # Stacked
        fig = px.bar(
            df_melted, x='Mese', y='Importo', color='Voce',
            barmode='stack',
            color_discrete_sequence=colors,
            labels={'Importo': 'Importo (€)', 'Mese': 'Periodo'}
        )

    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(showgrid=False, tickangle=-30),
        yaxis=dict(showgrid=True, gridcolor='#F1F5F9',
                   tickformat=',.0f',
                   tickprefix='€ '),
        font=dict(family='DM Sans', size=12, color='#374151'),
        height=420
    )
    fig.update_traces(
        hovertemplate='<b>%{x}</b><br>%{y:,.0f} €<extra>%{fullData.name}</extra>'
    )

    st.plotly_chart(fig, use_container_width=True)

    # Grafico waterfall per singola voce
    st.markdown("---")
    st.markdown("#### Waterfall Mensile")
    voce_wf = st.selectbox("Seleziona voce:", voci, key="waterfall_voce")
    if voce_wf and voce_wf in pivot.index:
        dati_wf = pivot.loc[voce_wf, cols_mesi]
        fig_wf = go.Figure(go.Waterfall(
            name=voce_wf,
            orientation='v',
            x=cols_mesi,
            y=dati_wf.tolist(),
            connector={'line': {'color': '#CBD5E8'}},
            increasing={'marker': {'color': '#059669'}},
            decreasing={'marker': {'color': '#DC2626'}},
            totals={'marker': {'color': '#1A3A7A'}},
        ))
        fig_wf.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(showgrid=False, tickangle=-30),
            yaxis=dict(showgrid=True, gridcolor='#F1F5F9'),
            font=dict(family='DM Sans', size=12),
            height=350
        )
        st.plotly_chart(fig_wf, use_container_width=True)


def _render_empty():
    st.markdown("## 📊 Dashboard")
    st.info("👋 Seleziona un cliente dalla sidebar e carica i dati nel Workspace per visualizzare la dashboard.")


def _render_placeholder():
    """Placeholder grafico quando i dati non sono ancora caricati."""
    col1, col2, col3 = st.columns(3)
    for col, label, color in [
        (col1, "Ricavi Netti", "#1A3A7A"),
        (col2, "EBITDA", "#059669"),
        (col3, "Risultato Netto", "#7C3AED")
    ]:
        with col:
            st.markdown(f"""
            <div class='metric-card' style='border-left-color:{color}; opacity:0.4'>
                <div class='label'>{label}</div>
                <div class='value'>— €</div>
            </div>
            """, unsafe_allow_html=True)
