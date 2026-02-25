"""
dashboard.py — CE Matrix con drill-down, dark theme, DM Sans.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from services.data_utils import get_cliente, fmt_eur, fmt_pct
from services.riclassifica import (
    costruisci_ce_riclassificato, get_mesi_disponibili,
    calcola_kpi_finanziari, _safe_scalar, _safe_str,
)

PALETTE = ['#1A3A7A','#10B981','#C9A84C','#EF4444','#8B5CF6',
           '#F59E0B','#06B6D4','#EC4899','#14B8A6','#6366F1']

PLOTLY_BASE = dict(
    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
    font=dict(family='DM Sans, -apple-system, sans-serif', color='#64748B', size=11),
    legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor='rgba(255,255,255,0.06)',
                orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0,
                font=dict(size=10, color='#94A3B8')),
    hoverlabel=dict(bgcolor='#0D1625', bordercolor='#C9A84C', font_color='#F1F5F9'),
)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

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

    from services.riclassifica import get_label_map
    label_map = get_label_map(df_ricl) if df_ricl is not None else {}

    if df_db is None or df_piano is None or df_ricl is None:
        st.markdown("""
<div style='background:rgba(37,99,235,0.08);border-left:4px solid #2563EB;
            padding:16px 20px;border-radius:0 10px 10px 0;margin:16px 0'>
  <div style='font-size:0.95rem;font-weight:700;color:#F1F5F9;margin-bottom:4px'>👋 Inizia dal Workspace</div>
  <div style='font-size:0.84rem;color:#94A3B8'>
    Carica i tre file (Piano Conti, DB Contabile, Schema Riclassifica) e configura la mappatura.
  </div>
</div>""", unsafe_allow_html=True)
        return

    if not mapping:
        st.warning("⚠️ Nessuna mappatura. Vai in **Workspace → Mappatura Conti**.")
        return

    with st.spinner("⚙️ Elaborazione dati…"):
        pivot, dettaglio, errore = costruisci_ce_riclassificato(
            df_db, df_piano, df_ricl, mapping, schema_cfg, rettifiche
        )

    if errore:
        st.error("❌ " + errore); return
    if pivot is None or pivot.empty:
        st.warning("⚠️ Nessun dato. Verifica mappatura e dati caricati."); return

    mesi = get_mesi_disponibili(pivot)
    if not mesi:
        st.warning("⚠️ Nessun dato mensile."); return

    # ── HEADER ──────────────────────────────────────────────────────────────
    h1, h2 = st.columns([5, 2])
    with h1:
        st.markdown(f"## 📊 Dashboard — {ca}")
        st.markdown(f"<p style='color:#475569;font-size:0.82rem;margin-top:-8px'>"
                    f"{len(mesi)} mesi &nbsp;·&nbsp; Schema: <b style='color:#94A3B8'>{schema_att or '—'}</b></p>",
                    unsafe_allow_html=True)

    # ── FILTRI ──────────────────────────────────────────────────────────────
    with st.expander("🔍 Periodo & Confronto", expanded=True):
        c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
        with c1:
            modalita = st.selectbox("Periodo", ["Mese singolo","Range mesi","YTD","Anno completo"], key="d_mod")
        with c2:
            anni = sorted(set(m[:4] for m in mesi), reverse=True)
            if modalita == "Mese singolo":
                mese_s = st.selectbox("Mese", mesi, index=len(mesi)-1, key="d_mese")
                mesi_filtro = [mese_s]
            elif modalita == "Range mesi":
                sel = st.multiselect("Mesi", mesi, default=mesi[-3:], key="d_range")
                mesi_filtro = sel or mesi[-3:]
            elif modalita == "YTD":
                anno_y = st.selectbox("Anno", anni, key="d_ytd")
                mesi_filtro = [m for m in mesi if m.startswith(str(anno_y))]
            else:
                anno_y = st.selectbox("Anno", anni, key="d_ay")
                mesi_filtro = [m for m in mesi if m.startswith(str(anno_y))]
        with c3:
            from datetime import datetime as _dt
            _anno_max = max(int(a) for a in anni) if anni else _dt.now().year
            _anni_ext = [str(a) for a in range(max(_anno_max, _dt.now().year)+2, min(int(a) for a in anni)-1 if anni else _dt.now().year-4, -1)]
            _anni_opt_labels = [a if a in anni else a+" ↩" for a in _anni_ext]
            _conf_raw = st.selectbox("Confronta vs", ['— nessuno —'] + _anni_opt_labels, key="d_conf")
            anno_conf = _conf_raw.rstrip(" ↩") if _conf_raw != '— nessuno —' else '— nessuno —' 
        with c4:
            mostra_bud = st.checkbox("Budget", value=bool(budget), key="d_bud")

    cols_filtro = [c for c in mesi_filtro if c in pivot.columns]
    if not cols_filtro:
        st.warning("Nessun dato per il periodo."); return

    # Build pf conservando _tipo
    pf_cols  = [c for c in cols_filtro if c in pivot.columns]
    meta_cols = [c for c in ('_tipo', '_cod') if c in pivot.columns]
    pf        = pivot[pf_cols + meta_cols].copy()
    pf['_PERIODO'] = pf[pf_cols].sum(axis=1)

    pf_conf = None
    if anno_conf != '— nessuno —':
        mesi_num      = {m[5:] for m in cols_filtro}
        cols_conf_raw = [c for c in pivot.columns if c[:4] == anno_conf and c[5:] in mesi_num and c not in ('_tipo','_cod')]
        if cols_conf_raw:
            pf_conf = pivot[cols_conf_raw + meta_cols].copy()
            pf_conf['_PERIODO'] = pf_conf[cols_conf_raw].sum(axis=1)

    kpi = calcola_kpi_finanziari(pivot, cols_filtro, schema_cfg)
    kpi_conf = calcola_kpi_finanziari(pivot,
        [c for c in pivot.columns if c[:4] == anno_conf and c[5:] in {m[5:] for m in cols_filtro} and c not in ('_tipo','_cod')],
        schema_cfg
    ) if anno_conf != '— nessuno —' else {}

    # ── ALERT BUDGET ────────────────────────────────────────────────────────
    if mostra_bud and budget:
        _render_budget_alerts(pf, budget, pf_cols)

    # ── KPI CARDS ──────────────────────────────────────────────────────────
    _render_kpi_cards(kpi, kpi_conf, anno_conf)

    st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.06);margin:20px 0'>",
                unsafe_allow_html=True)

    # ── TABS ────────────────────────────────────────────────────────────────
    tab_ce, tab_grafici, tab_budget = st.tabs(["📋 Conto Economico", "📈 Grafici", "🎯 Budget"])

    with tab_ce:
        _render_tabella_ce(ca, pf, dettaglio, pf_cols, pf_conf,
                           anno_conf, mostra_bud, budget, mesi_filtro, schema_cfg)
    with tab_grafici:
        _render_grafici(pivot, mesi, kpi)
    with tab_budget:
        from modules.budget import render_budget_inline
        render_budget_inline(cliente, pivot, mesi, ca)


# ─────────────────────────────────────────────────────────────────────────────
# KPI CARDS — inline styles, no class dependency
# ─────────────────────────────────────────────────────────────────────────────

def _render_kpi_cards(kpi, kpi_conf, anno_conf):
    def card(lbl, val, unit, accent, conf_val=None):
        cs = (f"background:#0D1625;border:1px solid rgba(255,255,255,0.07);"
              f"border-left:4px solid {accent};border-radius:12px;padding:16px 18px;")
        ls = "font-size:10px;text-transform:uppercase;letter-spacing:1.4px;color:#475569;font-weight:700;margin-bottom:8px;"
        vs = "font-size:1.4rem;font-weight:800;color:#F1F5F9;letter-spacing:-0.5px;line-height:1;margin-bottom:4px;"
        ds = "font-size:11px;font-weight:600;margin-top:5px;"
        v_str = (f"{val:.1f}%" if unit == '%' else (fmt_eur(val) if val is not None else '—'))
        delta = ""
        if conf_val is not None and conf_val != 0 and val is not None:
            dp  = (val - conf_val) / abs(conf_val) * 100
            clr = "#10B981" if dp >= 0 else "#EF4444"
            sym = "▲" if dp >= 0 else "▼"
            delta = f"<div style='{ds}color:{clr}'>{sym} {abs(dp):.1f}% vs {anno_conf}</div>"
        return (f"<div style='{cs}'><div style='{ls}'>{lbl}</div>"
                f"<div style='{vs}'>{v_str}</div>{delta}</div>")

    defs = [
        ("📈 Ricavi Netti",    kpi.get("ricavi"),        "€", "#1E3A6E", kpi_conf.get("ricavi")),
        ("💹 EBITDA / MOL",    kpi.get("ebitda"),        "€", "#10B981", kpi_conf.get("ebitda")),
        ("📊 EBITDA Margin",   kpi.get("ebitda_margin"), "%", "#7C3AED", kpi_conf.get("ebitda_margin")),
        ("🏆 Risultato Netto", kpi.get("utile_netto"),   "€", "#EF4444", kpi_conf.get("utile_netto")),
    ]
    cols = st.columns(4)
    for i, (lbl, val, unit, accent, cv) in enumerate(defs):
        with cols[i]:
            try:
                st.html(card(lbl, val, unit, accent, cv))
            except AttributeError:
                st.markdown(card(lbl, val, unit, accent, cv), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CE MATRIX — colonne=mesi, righe=voci con drill-down via <details>
# ─────────────────────────────────────────────────────────────────────────────

def _render_tabella_ce(ca, pf, dettaglio, cols_show, pf_conf,
                        anno_conf, mostra_bud, budget, mesi_filtro, schema_cfg=None):
    """
    Matrice CE con:
    - colonne = mesi selezionati + Totale Periodo
    - righe contabili espandibili con <details>/<summary>
    - righe subtotale / totale stilate diversamente
    - confronto anno e budget come colonne aggiuntive
    """

    def fv(v, dash=False):
        try:
            f = float(v)
            if dash and f == 0: return '<span style="color:#334155">—</span>'
            s = f"{abs(f):,.0f}".replace(",","X").replace(".",",").replace("X",".")
            clr = "#10B981" if f > 0 else ("#EF4444" if f < 0 else "#475569")
            txt = f"({s})" if f < 0 else s
            return f'<span style="color:{clr}">{txt}</span>'
        except Exception:
            return '<span style="color:#334155">—</span>'

    # ── CSS per la tabella ──
    st.markdown("""
<style>
.ce-wrap { overflow-x:auto; margin-top:12px; }
.ce-table {
  width:100%; border-collapse:collapse;
  font-family:'DM Sans',sans-serif; font-size:0.81rem;
}
.ce-table th {
  padding:7px 10px; font-size:0.67rem; text-transform:uppercase;
  letter-spacing:1px; color:#475569; font-weight:700;
  text-align:right; border-bottom:2px solid rgba(201,168,76,0.25);
  white-space:nowrap; background:rgba(13,22,37,0.8);
  position:sticky; top:0; z-index:2;
}
.ce-table th.left { text-align:left; min-width:180px; }
.ce-table td { padding:5px 10px; }
.ce-table td.left { text-align:left; }
.ce-table td.right { text-align:right; white-space:nowrap; }
/* contabile rows */
.ce-row-c td.left { color:#94A3B8; font-weight:400; }
.ce-row-c:hover { background:rgba(255,255,255,0.015); }
/* subtotale rows */
.ce-row-s { background:rgba(255,255,255,0.035); border-top:1px solid rgba(255,255,255,0.10); }
.ce-row-s td.left { color:#E2E8F0; font-weight:700; font-size:0.84rem; }
/* totale rows */
.ce-row-t { background:rgba(201,168,76,0.08);
            border-top:2px solid rgba(201,168,76,0.35);
            border-bottom:2px solid rgba(201,168,76,0.35); }
.ce-row-t td.left { color:#C9A84C; font-weight:800; font-size:0.87rem; }
/* separator rows */
.ce-row-sep td { padding:3px 0; }
/* detail rows inside <details> */
.ce-detail-row td.left { color:#475569; padding-left:28px; font-size:0.74rem; }
.ce-detail-row td.right { font-size:0.74rem; color:#475569; }
/* summary (voce name) — arrow expand */
summary.ce-sum {
  cursor:pointer; list-style:none; display:flex;
  align-items:center; gap:5px; color:#94A3B8;
}
summary.ce-sum::before {
  content:'▶'; font-size:8px; color:#475569;
  transition:transform 0.15s; flex-shrink:0;
}
details[open] summary.ce-sum::before { transform:rotate(90deg); }
</style>
""", unsafe_allow_html=True)

    # ── Intestazioni ──
    th = lambda txt, left=False: f"<th class=\"{'left' if left else ''}\">{txt}</th>"

    header = th("Voce", left=True)
    for c in cols_show:
        header += th(c.replace("-", "‑"))
    header += th("<b style='color:#C9A84C'>Totale</b>")
    if pf_conf is not None:
        header += th(f"vs {anno_conf}") + th("Δ %")
    if mostra_bud and budget:
        header += th("Budget") + th("Scost.")

    # ── Righe ──
    rows_html = ""

    for voce in pf.index:
        tipo = _safe_str(pf.loc[voce, '_tipo']) if '_tipo' in pf.columns else 'contabile'

        if tipo == 'separatore':
            ncols = 2 + len(cols_show) + (2 if pf_conf is not None else 0) + (2 if mostra_bud and budget else 0)
            rows_html += f"<tr class='ce-row-sep'><td colspan='{ncols}' style='height:8px'></td></tr>"
            continue

        try:
            val_tot = float(pf.loc[voce, '_PERIODO']) if '_PERIODO' in pf.columns else 0.0
        except Exception:
            val_tot = 0.0

        row_cls = {'contabile': 'ce-row-c', 'subtotale': 'ce-row-s', 'totale': 'ce-row-t'}.get(tipo, 'ce-row-c')

        # Nome voce = descrizione (pivot.index) — SEMPRE description, mai codice
        has_detail = (tipo == 'contabile' and voce in dettaglio
                      and dettaglio[voce] is not None and not dettaglio[voce].empty)
        n_conti = len(dettaglio[voce]) if has_detail else 0
        n_badge = (f" <span style='font-size:0.64rem;color:#334155;font-weight:400'>"
                   f"({n_conti})</span>") if n_conti else ''

        if has_detail:
            # <details> senza "open" = collassato di default
            nome_cell = (f"<details>"
                         f"<summary class='ce-sum'>{voce}{n_badge}</summary>"
                         f"_DETAIL_{voce}_"
                         f"</details>")
        else:
            nome_cell = str(voce)
        td_nome = f"<td class='left'>{nome_cell}</td>"

        # Valori mensili
        tds = ""
        for c in cols_show:
            v = _safe_scalar(pf.loc[voce, c]) if c in pf.columns else 0.0
            tds += f"<td class='right'>{fv(v, dash=(tipo=='contabile'))}</td>"

        # Totale periodo
        tds += f"<td class='right'><b>{fv(val_tot)}</b></td>"

        # Confronto anno
        if pf_conf is not None:
            val_c, dp = 0.0, 0.0
            if voce in pf_conf.index and '_PERIODO' in pf_conf.columns:
                try:
                    val_c = _safe_scalar(pf_conf.loc[voce, '_PERIODO'])
                    dp = (val_tot - val_c) / abs(val_c) * 100 if val_c != 0 else 0.0
                except Exception:
                    pass
            dc = "#10B981" if dp >= 0 else "#EF4444"
            dp_str = (f"<span style='color:{dc}'>{dp:+.1f}%</span>" if val_c != 0 else
                      '<span style="color:#334155">—</span>')
            tds += f"<td class='right'>{fv(val_c, dash=True)}</td><td class='right'>{dp_str}</td>"

        # Budget
        if mostra_bud and budget:
            bud_tot, scost = 0.0, 0.0
            if voce in budget:
                bud_tot = sum(budget[voce].get(m, 0) for m in cols_show)
                scost   = val_tot - bud_tot
            tds += f"<td class='right'>{fv(bud_tot, dash=True)}</td><td class='right'>{fv(scost, dash=True)}</td>"

        row_html = f"<tr class='{row_cls}'>{td_nome}{tds}</tr>"

        # Dettaglio conto (dentro il <details>, placeholder sostituito)
        if has_detail:
            det = dettaglio[voce]
            det_cols = [c for c in cols_show if c in det.columns]
            det_rows = ""
            for conto in det.index:
                dcells = f"<td class='left'>{str(conto)[:55]}</td>"
                for c in cols_show:
                    sv = _safe_scalar(det.loc[conto, c]) if c in det.columns else 0.0
                    dcells += f"<td class='right'>{fv(sv, dash=True)}</td>"
                sv_tot = _safe_scalar(det.loc[conto, 'TOTALE']) if 'TOTALE' in det.columns else 0.0
                dcells += f"<td class='right'><b>{fv(sv_tot, dash=True)}</b></td>"
                if pf_conf is not None:
                    dcells += "<td></td><td></td>"
                if mostra_bud and budget:
                    dcells += "<td></td><td></td>"
                det_rows += f"<tr class='ce-detail-row'>{dcells}</tr>"
            # Inietta det_rows nel placeholder
            row_html = row_html.replace(f"_DETAIL_{voce}_", det_rows)

        rows_html += row_html

    table_html = f"""
<div class='ce-wrap'>
  <table class='ce-table'>
    <thead><tr>{header}</tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>"""
    st.markdown(table_html, unsafe_allow_html=True)

    # ── Export ──
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    exp_rows = []
    for voce in pf.index:
        tipo = _safe_str(pf.loc[voce, '_tipo']) if '_tipo' in pf.columns else 'contabile'
        if tipo == 'separatore':
            continue
        r = {"Voce": voce, "Tipo": tipo}
        for c in cols_show:
            r[c] = _safe_scalar(pf.loc[voce, c]) if c in pf.columns else 0.0
        r["TOTALE"] = _safe_scalar(pf.loc[voce, '_PERIODO']) if '_PERIODO' in pf.columns else 0.0
        exp_rows.append(r)
    if exp_rows:
        csv = pd.DataFrame(exp_rows).to_csv(index=False, decimal=",", sep=";").encode("utf-8-sig")
        st.download_button("⬇️ Esporta CE (CSV)", data=csv,
                           file_name=f"CE_{ca}_{'-'.join(mesi_filtro[:2])}.csv",
                           mime="text/csv")


# ─────────────────────────────────────────────────────────────────────────────
# GRAFICI
# ─────────────────────────────────────────────────────────────────────────────

def _render_grafici(pivot, mesi, kpi):
    # Filtra voci non separatori
    voci = [v for v in pivot.index
            if _safe_str(pivot.loc[v, '_tipo']) != 'separatore'] if '_tipo' in pivot.columns else list(pivot.index)
    cols_mesi = [c for c in mesi if c in pivot.columns]
    if not cols_mesi:
        st.info("Nessun dato temporale."); return

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        voci_sel = st.multiselect("Voci", voci, default=voci[:min(4, len(voci))], key="g_voci")
    with c2:
        tipo = st.radio("Tipo", ["Linee", "Barre", "Area"], horizontal=True, key="g_tipo")
    with c3:
        n_m = st.slider("Mesi", 3, len(cols_mesi), min(12, len(cols_mesi)), key="g_nm")

    mesi_plot = cols_mesi[-n_m:]
    if not voci_sel:
        st.info("Seleziona almeno una voce."); return

    rows = []
    for voce in voci_sel:
        if voce not in pivot.index: continue
        for m in mesi_plot:
            if m in pivot.columns:
                rows.append({'Mese': m, 'Voce': str(voce)[:30],
                             'Importo': _safe_scalar(pivot.loc[voce, m])})
    if not rows:
        st.info("Nessun dato."); return

    df_m = pd.DataFrame(rows)
    cmap = {str(v)[:30]: PALETTE[i % len(PALETTE)] for i, v in enumerate(voci_sel)}

    if tipo == "Linee":
        fig = px.line(df_m, x='Mese', y='Importo', color='Voce', markers=True, color_discrete_map=cmap)
        fig.update_traces(line=dict(width=2.5), marker=dict(size=7))
    elif tipo == "Barre":
        fig = px.bar(df_m, x='Mese', y='Importo', color='Voce', barmode='group', color_discrete_map=cmap)
    else:
        fig = px.area(df_m, x='Mese', y='Importo', color='Voce', color_discrete_map=cmap)

    fig.update_layout(
        **PLOTLY_BASE, height=380,
        xaxis=dict(showgrid=False, tickangle=-30, title='', color='#64748B', tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickformat=',.0f',
                   ticksuffix=' €', color='#64748B', tickfont=dict(size=10), title=''),
        margin=dict(l=0, r=0, t=30, b=0), bargap=0.2,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Waterfall + Pie
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 🌊 Waterfall")
        voce_wf = st.selectbox("Voce waterfall", voci, key="wf_v")
        if voce_wf in pivot.index:
            vals_wf = [_safe_scalar(pivot.loc[voce_wf, m]) for m in mesi_plot]
            fig_wf = go.Figure(go.Waterfall(
                orientation='v', x=mesi_plot, y=vals_wf,
                connector=dict(line=dict(color='rgba(255,255,255,0.1)', width=1)),
                increasing=dict(marker=dict(color='#10B981', line=dict(width=0))),
                decreasing=dict(marker=dict(color='#EF4444', line=dict(width=0))),
            ))
            fig_wf.update_layout(
                **PLOTLY_BASE, height=300,
                xaxis=dict(showgrid=False, tickangle=-30, color='#64748B', tickfont=dict(size=9)),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickformat=',.0f',
                           ticksuffix=' €', color='#64748B'),
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig_wf, use_container_width=True)

    with col_b:
        st.markdown("#### 📊 Composizione")
        mese_pie = st.selectbox("Mese", mesi_plot, index=len(mesi_plot)-1, key="pie_m")
        if mese_pie in pivot.columns:
            vals_pie = {}
            for v in voci_sel:
                if v in pivot.index:
                    val = _safe_scalar(pivot.loc[v, mese_pie])
                    if val > 0:
                        vals_pie[str(v)[:25]] = val
            if vals_pie:
                fig_pie = go.Figure(go.Pie(
                    labels=list(vals_pie.keys()), values=list(vals_pie.values()),
                    marker=dict(colors=PALETTE[:len(vals_pie)], line=dict(color='#060D1A', width=2)),
                    textposition='inside', textinfo='percent+label',
                    insidetextfont=dict(size=10, color='white'), hole=0.35,
                ))
                fig_pie.update_layout(
                    **PLOTLY_BASE, height=300, showlegend=False,
                    margin=dict(l=0, r=0, t=10, b=0),
                )
                st.plotly_chart(fig_pie, use_container_width=True)

    # Margini
    st.markdown("#### 📉 Evoluzione Margini")
    margin_rows = []
    for m in mesi_plot:
        km = calcola_kpi_finanziari(pivot, [m])
        for k, lbl, clr in [
            ('ebitda_margin','EBITDA %','#10B981'),
            ('net_margin','Net Margin %','#1E3A6E'),
            ('cost_labor_pct','% Personale','#EF4444'),
        ]:
            v = km.get(k)
            if v is not None:
                margin_rows.append({'Mese': m, 'KPI': lbl, 'Valore': v, '_c': clr})
    if margin_rows:
        df_mg = pd.DataFrame(margin_rows)
        cmap2 = {r['KPI']: r['_c'] for r in margin_rows}
        fig_mg = px.line(df_mg, x='Mese', y='Valore', color='KPI',
                         markers=True, color_discrete_map=cmap2)
        fig_mg.add_hline(y=0, line_dash='dot', line_color='rgba(255,255,255,0.15)')
        fig_mg.update_traces(line=dict(width=2.5), marker=dict(size=6))
        fig_mg.update_layout(
            **PLOTLY_BASE, height=260,
            yaxis=dict(ticksuffix='%', showgrid=True, gridcolor='rgba(255,255,255,0.05)',
                       color='#64748B', title='', tickfont=dict(size=10)),
            xaxis=dict(showgrid=False, tickangle=-30, color='#64748B', title=''),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_mg, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# ALERT BUDGET
# ─────────────────────────────────────────────────────────────────────────────

def _render_budget_alerts(pf, budget, cols_filtro):
    alerts = []
    for voce in pf.index:
        tipo = _safe_str(pf.loc[voce, '_tipo']) if '_tipo' in pf.columns else 'contabile'
        if tipo != 'contabile' or voce not in budget:
            continue
        val_eff = _safe_scalar(pf.loc[voce, '_PERIODO']) if '_PERIODO' in pf.columns else 0.0
        val_bud = sum(budget[voce].get(m, 0) for m in cols_filtro)
        if val_bud == 0: continue
        pct = (val_eff - val_bud) / abs(val_bud) * 100
        if abs(pct) >= 15:
            alerts.append((voce, val_eff, val_bud, pct))
    if not alerts: return

    st.markdown("#### ⚠️ Alert Budget")
    cols = st.columns(min(len(alerts), 3))
    for i, (voce, eff, bud, pct) in enumerate(alerts[:6]):
        with cols[i % 3]:
            clr = '#EF4444' if pct < 0 else '#F59E0B'
            bg  = 'rgba(239,68,68,0.08)' if pct < 0 else 'rgba(245,158,11,0.08)'
            st.markdown(f"""
<div style='background:{bg};border-left:3px solid {clr};border-radius:8px;padding:12px 14px;margin-bottom:8px'>
  <div style='font-size:0.69rem;font-weight:700;color:{clr};text-transform:uppercase;letter-spacing:.8px'>
    {"▼ Sotto" if pct < 0 else "▲ Sopra"} Budget
  </div>
  <div style='font-weight:700;font-size:0.85rem;margin:4px 0;color:#F1F5F9'>{voce[:32]}</div>
  <div style='font-size:0.78rem;color:#64748B'>
    Effettivo: <b style='color:#F1F5F9'>{fmt_eur(eff)}</b><br>
    Budget: {fmt_eur(bud)}<br>
    <span style='color:{clr};font-weight:700'>{pct:+.1f}%</span>
  </div>
</div>""", unsafe_allow_html=True)
    st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.06);margin:12px 0'>",
                unsafe_allow_html=True)


def _empty_state():
    st.markdown("## 📊 Dashboard")
    st.info("👋 Seleziona un cliente dalla sidebar e carica i dati nel Workspace.")
