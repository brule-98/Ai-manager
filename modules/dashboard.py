import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from services.data_utils import get_cliente, save_cliente, fmt_eur, find_column
from services.riclassifica import (
    costruisci_ce_riclassificato, get_mesi_disponibili,
    calcola_incidenza, calcola_variazione_mensile
)


@st.cache_data(show_spinner=False)
def _cached_pivot(db_hash, piano_hash, mapping_hash, schema_hash, rettifiche_hash, sito):
    """Cache del pivot per evitare ricalcoli inutili."""
    return None  # Il caching reale richiede oggetti hashable; usato come flag


def render_dashboard():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        _empty_state(); return

    cliente = get_cliente()
    if not cliente:
        _empty_state(); return

    df_db    = cliente.get('df_db')
    df_piano = cliente.get('df_piano')
    df_ricl  = cliente.get('df_ricl')
    mapping  = cliente.get('mapping', {})
    schema_nome = cliente.get('schema_attivo', '')
    schema_config = cliente.get('schemi', {}).get(schema_nome, {})
    rettifiche = [r for r in cliente.get('rettifiche', []) if r.get('attiva', True)]
    sito = st.session_state.get('sito_attivo', 'Globale')

    if df_db is None or df_piano is None or df_ricl is None:
        st.info("👋 Carica i dati nel **Workspace** per visualizzare la dashboard.")
        _placeholder_kpi(); return

    if not mapping:
        st.warning("⚠️ Mappatura non configurata. Vai in **Workspace → Mappatura Conti**.")
        return

    # ── Costruisci CE ─────────────────────────────────────────────
    pivot, errore = costruisci_ce_riclassificato(
        df_db, df_piano, df_ricl, mapping, schema_config, rettifiche, sito
    )
    if errore:
        st.error(f"Errore CE: {errore}"); return

    # Mappa codice → descrizione umana
    label_map = _build_label_map(df_ricl, schema_config)
    mesi_disp = get_mesi_disponibili(pivot)

    # ── HEADER ────────────────────────────────────────────────────
    sito_label = f" — 🏭 {sito}" if sito != 'Globale' else ""
    schema_label = f" · Schema: **{schema_nome}**" if schema_nome else ""
    st.markdown(f"## 📊 Dashboard{sito_label}")
    if schema_label:
        st.markdown(f"<span style='font-size:0.8rem; color:#6B7280;'>{schema_label}</span>",
                    unsafe_allow_html=True)

    # ── FILTRI ────────────────────────────────────────────────────
    with st.container():
        st.markdown('<div class="card card-tight">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 3, 1])

        with c1:
            modalita = st.selectbox("Modalità:", [
                "Mensile", "Periodo personalizzato", "YTD", "Anno completo"
            ], key="d_mode")

        with c2:
            if not mesi_disp:
                mesi_filtro = []
            elif modalita == "Mensile":
                m = st.selectbox("Mese:", mesi_disp, index=len(mesi_disp) - 1, key="d_mese")
                mesi_filtro = [m]
            elif modalita == "Periodo personalizzato":
                sel = st.multiselect("Mesi:", mesi_disp, default=mesi_disp[-3:], key="d_multi")
                mesi_filtro = sel or mesi_disp
            elif modalita == "YTD":
                anni = sorted({m[:4] for m in mesi_disp}, reverse=True)
                a = st.selectbox("Anno:", anni, key="d_anno_ytd")
                mesi_filtro = [m for m in mesi_disp if m.startswith(a)]
            else:
                anni = sorted({m[:4] for m in mesi_disp}, reverse=True)
                a = st.selectbox("Anno:", anni, key="d_anno_full")
                mesi_filtro = [m for m in mesi_disp if m.startswith(a)]

        with c3:
            mostra_incidenza = st.checkbox("% su Ricavi", value=True, key="d_pct")

        st.markdown('</div>', unsafe_allow_html=True)

    cols_filtro = [c for c in mesi_filtro if c in pivot.columns]
    if not cols_filtro:
        st.warning("Nessun dato per il periodo selezionato."); return

    pivot_f = pivot[cols_filtro].copy()
    pivot_f['TOTALE PERIODO'] = pivot_f.sum(axis=1)

    # ── KPI CARDS ─────────────────────────────────────────────────
    _render_kpi_cards(pivot_f, pivot, mesi_filtro, mesi_disp)
    st.markdown("---")

    # ── TABS REPORT / GRAFICI ─────────────────────────────────────
    tab_rep, tab_graf, tab_var = st.tabs([
        "📋 Report CE", "📈 Trend & Analisi", "📉 Variazioni MoM"
    ])

    with tab_rep:
        _render_ce_table(pivot_f, schema_config, label_map, cols_filtro, mostra_incidenza, pivot)

    with tab_graf:
        _render_grafici(pivot, mesi_disp, label_map, schema_config)

    with tab_var:
        _render_variazioni(pivot, mesi_disp, label_map)


def _build_label_map(df_ricl, schema_config: dict) -> dict:
    """Costruisce mappa codice_voce → etichetta umana."""
    label_map = {}

    # Prima: override da schema_config
    if schema_config:
        for k, v in schema_config.items():
            if v.get('descrizione_override'):
                label_map[k] = v['descrizione_override']

    # Poi: da df_ricl
    if df_ricl is not None:
        col_cod  = find_column(df_ricl, ['Codice', 'codice', 'Voce', 'voce', 'ID'])
        col_desc = find_column(df_ricl, ['Descrizione', 'descrizione', 'voce', 'Voce', 'Nome'])
        if col_cod and col_desc:
            for _, row in df_ricl.iterrows():
                k = str(row[col_cod])
                if k not in label_map:
                    label_map[k] = str(row[col_desc])
    return label_map


def _render_kpi_cards(pivot_f, pivot_full, mesi_filtro, mesi_disp):
    kpi_keywords = [
        (['ricav', 'fattur', 'vendite', 'revenue'], "Ricavi Netti", "#1A3A7A"),
        (['ebitda', 'mol ', 'margine lordo'], "EBITDA / MOL", "#059669"),
        (['ebit', 'reddito op', 'risultato op'], "EBIT", "#7C3AED"),
        (['utile netto', 'risultato netto', 'reddito netto'], "Risultato Netto", "#DC2626"),
    ]

    cols = st.columns(4)
    for i, (keywords, label, color) in enumerate(kpi_keywords):
        voce = next((v for v in pivot_f.index
                     if any(k in v.lower() for k in keywords)), None)
        with cols[i]:
            if voce:
                val = pivot_f.loc[voce, 'TOTALE PERIODO']
                delta_html = _calc_delta_html(voce, val, pivot_full, mesi_filtro, mesi_disp)
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color:{color}">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value mono" style="color:{color}">{fmt_eur(val)}</div>
                    {delta_html}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="kpi-card" style="border-left-color:#E5E7EB; opacity:0.45">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value" style="color:#D1D5DB">— €</div>
                </div>
                """, unsafe_allow_html=True)


def _calc_delta_html(voce, val, pivot_full, mesi_filtro, mesi_disp) -> str:
    try:
        n = len(mesi_filtro)
        idx = mesi_disp.index(min(mesi_filtro))
        if idx >= n:
            mesi_prec = mesi_disp[idx - n: idx]
            cols_prec = [c for c in mesi_prec if c in pivot_full.columns]
            if cols_prec and voce in pivot_full.index:
                val_prec = pivot_full.loc[voce, cols_prec].sum()
                if val_prec != 0:
                    pct = (val - val_prec) / abs(val_prec) * 100
                    arrow = "▲" if pct >= 0 else "▼"
                    css   = "delta-up" if pct >= 0 else "delta-down"
                    return f'<div class="kpi-delta"><span class="{css}">{arrow} {abs(pct):.1f}% vs periodo prec.</span></div>'
    except Exception:
        pass
    return ""


def _render_ce_table(pivot_f, schema_config, label_map, cols_filtro, mostra_incidenza, pivot_full):
    st.markdown("#### Conto Economico Riclassificato")

    df_disp = pivot_f.copy()

    # Rinomina indice con label umane
    df_disp.index = [label_map.get(v, v) for v in df_disp.index]

    # Colonna Incidenza %
    if mostra_incidenza:
        inc = calcola_incidenza(pivot_full)
        if not inc.empty:
            inc.index = [label_map.get(v, v) for v in inc.index]
            df_disp['Inc. %'] = inc.reindex(df_disp.index)

    fmt_cols = [c for c in df_disp.columns if c not in ['Inc. %']]

    def fmt_eur_cell(v):
        try:
            fv = float(v)
            s = f"{abs(fv):,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            return f"({s} €)" if fv < 0 else f"{s} €"
        except Exception:
            return str(v)

    def fmt_pct_cell(v):
        try:
            return f"{float(v):.1f}%"
        except Exception:
            return "—"

    # Identifica righe subtotali per styling
    subtotal_rows = set()
    highlight_rows = set()
    if schema_config:
        for cod, cfg in schema_config.items():
            label = label_map.get(cod, cod)
            if cfg.get('subtotale'):
                subtotal_rows.add(label)
            if cfg.get('style_class') == 'highlight':
                highlight_rows.add(label)

    def row_style(row):
        label = row.name
        if label in subtotal_rows:
            return [
                'font-weight:700; background-color:#0F2044; color:white;'
            ] * len(row)
        if label in highlight_rows:
            return [
                'font-weight:600; background-color:#EEF4FF; color:#1A3A7A;'
            ] * len(row)
        return [''] * len(row)

    def cell_color(val):
        try:
            v = float(str(val).replace('(','').replace(')','').replace(' €','')
                     .replace('.','').replace(',','.'))
            if v < 0:
                return 'color: #B91C1C;'
            elif v > 0:
                return 'color: #065F46;'
        except Exception:
            pass
        return ''

    fmt_dict = {c: fmt_eur_cell for c in fmt_cols}
    if 'Inc. %' in df_disp.columns:
        fmt_dict['Inc. %'] = fmt_pct_cell

    styled = (
        df_disp.style
        .apply(row_style, axis=1)
        .applymap(cell_color, subset=fmt_cols)
        .format(fmt_dict)
        .set_table_styles([
            {'selector': 'thead th',
             'props': [('background-color', '#0F2044'), ('color', 'white'),
                       ('font-size', '0.73rem'), ('padding', '9px 14px'),
                       ('text-align', 'right'), ('white-space', 'nowrap')]},
            {'selector': 'th.row_heading',
             'props': [('text-align', 'left'), ('font-size', '0.82rem'),
                       ('padding', '8px 14px'), ('min-width', '180px')]},
            {'selector': 'td',
             'props': [('font-size', '0.82rem'), ('padding', '8px 14px'),
                       ('text-align', 'right'), ('font-family', "'JetBrains Mono', monospace")]},
        ])
    )

    st.dataframe(styled, use_container_width=True, height=480)

    csv = pivot_f.to_csv(decimal=',', sep=';').encode('utf-8-sig')
    st.download_button("⬇️ Esporta CSV", data=csv,
                       file_name=f"CE_{st.session_state.get('cliente_attivo','')}.csv",
                       mime="text/csv", key="dl_ce")


def _render_grafici(pivot, mesi_disp, label_map, schema_config):
    if not mesi_disp:
        st.info("Nessun dato temporale."); return

    voci = list(pivot.index)
    voci_labels = [label_map.get(v, v) for v in voci]
    voci_options = [f"{label_map.get(v, v)}" for v in voci]

    c1, c2 = st.columns([3, 1])
    with c1:
        sel_labels = st.multiselect(
            "Voci da analizzare:",
            voci_options,
            default=voci_options[:4] if len(voci_options) >= 4 else voci_options,
            key="g_voci"
        )
    with c2:
        tipo = st.radio("Tipo:", ["Barre", "Linee", "Stacked"], horizontal=False, key="g_tipo")

    if not sel_labels:
        st.info("Seleziona almeno una voce."); return

    # Ricava codici dai label
    label_to_cod = {label_map.get(v, v): v for v in voci}
    sel_codici = [label_to_cod.get(l, l) for l in sel_labels]

    cols_mesi = [c for c in mesi_disp if c in pivot.columns]
    df_plot = pivot.loc[sel_codici, cols_mesi].copy()
    df_plot.index = sel_labels
    df_melted = df_plot.T.reset_index().melt(id_vars='index', var_name='Voce', value_name='Importo')
    df_melted.columns = ['Mese', 'Voce', 'Importo']

    colors = ['#1A3A7A', '#059669', '#7C3AED', '#D97706', '#DC2626', '#0891B2', '#BE185D', '#065F46']

    fig_args = dict(
        data_frame=df_melted, x='Mese', y='Importo', color='Voce',
        color_discrete_sequence=colors,
        labels={'Importo': '€', 'Mese': 'Periodo'}
    )
    if tipo == "Barre":
        fig = px.bar(**fig_args, barmode='group')
    elif tipo == "Linee":
        fig = px.line(**fig_args, markers=True)
        fig.update_traces(line=dict(width=2.5))
    else:
        fig = px.bar(**fig_args, barmode='stack')

    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family='DM Sans', size=12),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis=dict(showgrid=False, tickangle=-30, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor='#F1F5F9', tickformat=',.0f'),
        height=400
    )
    fig.update_traces(hovertemplate='<b>%{x}</b><br>%{y:,.0f} €<extra>%{fullData.name}</extra>')
    st.plotly_chart(fig, use_container_width=True)

    # Waterfall
    st.markdown("---")
    st.markdown("#### Waterfall Mensile")
    voce_wf_label = st.selectbox("Seleziona voce:", voci_options, key="g_wf_voce")
    voce_wf_cod = label_to_cod.get(voce_wf_label, voce_wf_label)

    if voce_wf_cod in pivot.index:
        vals = pivot.loc[voce_wf_cod, cols_mesi].tolist()
        fig_wf = go.Figure(go.Waterfall(
            orientation='v', x=cols_mesi, y=vals,
            connector={'line': {'color': '#E5E7EB'}},
            increasing={'marker': {'color': '#059669'}},
            decreasing={'marker': {'color': '#DC2626'}},
            totals={'marker': {'color': '#1A3A7A'}},
            texttemplate='%{y:,.0f}',
            textposition='outside',
        ))
        fig_wf.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis=dict(showgrid=False, tickangle=-30),
            yaxis=dict(showgrid=True, gridcolor='#F1F5F9'),
            font=dict(family='DM Sans', size=12),
            height=320
        )
        st.plotly_chart(fig_wf, use_container_width=True)


def _render_variazioni(pivot, mesi_disp, label_map):
    st.markdown("#### Variazioni Mese su Mese (%)")

    df_var = calcola_variazione_mensile(pivot)
    if df_var is None:
        st.info("Servono almeno 2 mesi di dati per il calcolo delle variazioni.")
        return

    df_var.index = [label_map.get(v, v) for v in df_var.index]

    def color_pct(val):
        try:
            v = float(val)
            if v < -20: return 'background-color:#FEE2E2; color:#991B1B; font-weight:600;'
            if v < 0:   return 'background-color:#FEF3C7; color:#92400E;'
            if v > 20:  return 'background-color:#D1FAE5; color:#065F46; font-weight:600;'
            if v > 0:   return 'background-color:#ECFDF5; color:#059669;'
        except Exception:
            pass
        return ''

    def fmt_var(v):
        try:
            fv = float(v)
            s = f"{fv:+.1f}%"
            return s
        except Exception:
            return '—'

    styled = (
        df_var.style
        .applymap(color_pct)
        .format(fmt_var)
        .set_table_styles([
            {'selector': 'thead th',
             'props': [('background-color', '#0F2044'), ('color', 'white'),
                       ('font-size', '0.72rem'), ('padding', '8px 12px'), ('text-align', 'center')]},
            {'selector': 'td',
             'props': [('font-size', '0.82rem'), ('padding', '7px 12px'), ('text-align', 'center'),
                       ('font-family', "'JetBrains Mono', monospace")]},
            {'selector': 'th.row_heading',
             'props': [('text-align', 'left'), ('font-size', '0.8rem'), ('padding', '7px 14px')]},
        ])
    )
    st.dataframe(styled, use_container_width=True, height=420)


def _empty_state():
    st.markdown("## 📊 Dashboard")
    st.info("👋 Seleziona un cliente dalla sidebar e carica i dati nel Workspace.")


def _placeholder_kpi():
    cols = st.columns(4)
    for i, (label, color) in enumerate([
        ("Ricavi Netti", "#1A3A7A"), ("EBITDA", "#059669"),
        ("EBIT", "#7C3AED"), ("Risultato Netto", "#DC2626")
    ]):
        with cols[i]:
            st.markdown(f"""
            <div class="kpi-card" style="border-left-color:{color}; opacity:0.3">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">— €</div>
            </div>
            """, unsafe_allow_html=True)
