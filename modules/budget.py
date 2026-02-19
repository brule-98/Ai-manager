"""budget.py — Gestione Budget e analisi scostamenti."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from services.data_utils import get_cliente, save_cliente, fmt_eur


def render_budget():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("⚠️ Seleziona un cliente dalla sidebar."); return
    cliente = get_cliente()
    df_db = cliente.get('df_db')
    if df_db is None or not cliente.get('mapping'):
        st.info("Carica i dati e configura la mappatura prima di usare il Budget."); return

    from services.riclassifica import costruisci_ce_riclassificato, get_mesi_disponibili
    schema_att = cliente.get('schema_attivo', '')
    schema_cfg = cliente.get('schemi', {}).get(schema_att, {})
    pivot, _, errore = costruisci_ce_riclassificato(
        df_db, cliente.get('df_piano'), cliente.get('df_ricl'),
        cliente.get('mapping', {}), schema_cfg, cliente.get('rettifiche', [])
    )
    if errore:
        st.error(errore); return

    mesi   = get_mesi_disponibili(pivot)
    budget = cliente.get('budget', {})
    voci   = list(pivot.index)

    st.markdown(f"""
    <div style='margin-bottom:20px'>
        <div style='font-size:10px;text-transform:uppercase;letter-spacing:2px;color:#C9A84C;font-weight:700;margin-bottom:4px'>Budget & Forecast</div>
        <div style='font-size:1.4rem;font-weight:700;color:#F1F5F9'>🎯 {ca}</div>
    </div>""", unsafe_allow_html=True)

    render_budget_inline(cliente, pivot, mesi, ca)


def render_budget_inline(cliente, pivot, mesi, ca):
    budget = cliente.get('budget', {})
    voci   = list(pivot.index)
    cols_mesi = [c for c in mesi if c in pivot.columns]

    tab_crea, tab_scostamenti = st.tabs(["📝 Crea / Carica", "📊 Analisi Scostamenti"])

    with tab_crea:
        _render_crea(cliente, pivot, mesi, ca, budget, voci, cols_mesi)
    with tab_scostamenti:
        _render_scostamenti(pivot, budget, cols_mesi, voci)


def _render_crea(cliente, pivot, mesi, ca, budget, voci, cols_mesi):
    st.markdown("#### Metodo di caricamento budget")

    metodo = st.radio("", [
        "📊 Da anno precedente (automatico)",
        "✏️ Inserimento manuale",
        "📂 Carica da file CSV/Excel"
    ], key="bud_metodo", horizontal=False)

    anni = sorted(set(m[:4] for m in mesi), reverse=True)

    if "precedente" in metodo:
        if len(anni) < 2:
            st.info("Servono almeno 2 anni di dati storici.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                anno_base = st.selectbox("Anno base:", anni[1:], key="bud_base_anno")
            with c2:
                var = st.number_input("Variazione % attesa:", value=5.0, step=0.5,
                                       format="%.1f", key="bud_var")
            with c3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("⚡ Genera", type="primary"):
                    cols_base = [c for c in pivot.columns if c.startswith(str(anno_base))]
                    mult = 1 + var / 100
                    bud_new = {}
                    for voce in voci:
                        bud_new[voce] = {}
                        for m in cols_base:
                            target_m = m.replace(str(anno_base), str(int(anno_base)+1))
                            v = float(pivot.loc[voce, m]) if m in pivot.columns else 0
                            bud_new[voce][target_m] = round(v * mult, 2)
                    save_cliente({'budget': bud_new})
                    st.success(f"✅ Budget {int(anno_base)+1} generato con variazione {var:+.1f}%")
                    st.rerun()

    elif "manuale" in metodo:
        anno_bud = st.selectbox("Anno:", anni, key="bud_anno_man")
        mesi_a   = sorted([m for m in cols_mesi if m.startswith(str(anno_bud))])
        if not mesi_a:
            st.info("Nessun dato per l'anno selezionato.")
            return

        bud_tmp = {v: dict(budget.get(v, {})) for v in voci}
        for voce in voci:
            with st.expander(f"📌 {voce}"):
                ncols = min(len(mesi_a), 4)
                cols  = st.columns(ncols)
                for i, mese in enumerate(mesi_a):
                    with cols[i % ncols]:
                        eff = float(pivot.loc[voce, mese]) if mese in pivot.columns else 0
                        v   = st.number_input(
                            mese, value=float(bud_tmp[voce].get(mese, 0)),
                            step=1000.0, format="%.0f",
                            help=f"Effettivo: {fmt_eur(eff)}",
                            key=f"bud_{voce}_{mese}"
                        )
                        bud_tmp[voce][mese] = v

        if st.button("💾 Salva Budget", type="primary"):
            save_cliente({'budget': bud_tmp})
            st.success("✅ Budget salvato!")
            st.rerun()

    else:  # File
        st.markdown("""**Formato CSV atteso:**
```
Voce;2024-01;2024-02;...
Ricavi vendite;100000;120000;...
```""")
        f = st.file_uploader("Carica file:", type=['csv','xlsx'], key="bud_file_up")
        if f:
            try:
                if f.name.endswith('.xlsx'):
                    df_b = pd.read_excel(f, index_col=0, dtype=str)
                else:
                    df_b = pd.read_csv(f, sep=';', index_col=0, encoding='utf-8-sig', dtype=str)
                bud_new = {}
                for voce in df_b.index:
                    bud_new[str(voce)] = {}
                    for col in df_b.columns:
                        try:
                            bud_new[str(voce)][str(col)] = float(
                                str(df_b.loc[voce, col]).replace(',','.').replace(' ','')
                            )
                        except Exception:
                            pass
                save_cliente({'budget': bud_new})
                st.success(f"✅ Budget caricato: {len(bud_new)} voci")
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")

    if budget:
        st.markdown("---")
        n_voci_bud = len([v for v in budget if budget[v]])
        st.markdown(f"<div style='color:#10B981;font-size:0.82rem'>✅ Budget attivo: {n_voci_bud} voci configurate</div>", unsafe_allow_html=True)
        if st.button("🗑️ Cancella budget", key="bud_del_btn"):
            save_cliente({'budget': {}})
            st.rerun()


def _render_scostamenti(pivot, budget, cols_mesi, voci):
    if not budget:
        st.info("Nessun budget configurato. Usa il tab 'Crea / Carica'."); return

    # Calcolo scostamenti
    rows = []
    for voce in voci:
        if voce not in budget:
            continue
        for m in cols_mesi:
            eff = float(pivot.loc[voce, m]) if m in pivot.columns else 0
            bud = budget[voce].get(m, 0)
            if bud == 0:
                continue
            sc  = eff - bud
            pct = sc / abs(bud) * 100
            rows.append({'Voce': voce, 'Mese': m, 'Effettivo': eff, 'Budget': bud, 'Scostamento': sc, 'Sc%': pct})

    if not rows:
        st.info("Nessun dato di confronto disponibile.")
        return

    df_sc = pd.DataFrame(rows)

    # Alert intelligenti
    st.markdown("#### ⚡ Alert Intelligenti (soglia adattiva)")
    alerts = _alert_intelligenti(pivot, budget, cols_mesi, voci)
    if alerts:
        for a in alerts:
            color = "#EF4444" if a['tipo'] == 'NEG' else "#F59E0B"
            bg    = "rgba(239,68,68,0.06)" if a['tipo'] == 'NEG' else "rgba(245,158,11,0.06)"
            st.markdown(f"""
            <div style='background:{bg};border:1px solid {color}33;border-radius:10px;
                        padding:14px 18px;margin:6px 0;display:flex;justify-content:space-between;align-items:center'>
                <div>
                    <div style='font-weight:700;color:#E2E8F0;font-size:0.88rem'>⚠ {a["voce"]}</div>
                    <div style='color:#64748B;font-size:0.8rem;margin-top:2px'>{a["motivo"]}</div>
                </div>
                <div style='text-align:right'>
                    <div style='color:{color};font-weight:700;font-size:1rem'>{a["sc_pct"]:+.1f}%</div>
                    <div style='color:#475569;font-size:0.75rem'>{a["mese"]}</div>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.success("✅ Nessun alert significativo")

    # Grafico per voce
    st.markdown("---")
    st.markdown("#### 📊 Effettivo vs Budget per Voce")
    voce_sel = st.selectbox("Voce:", [v for v in voci if v in budget], key="sc_voce_sel")
    df_v = df_sc[df_sc['Voce'] == voce_sel].sort_values('Mese')

    if not df_v.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='Effettivo', x=df_v['Mese'], y=df_v['Effettivo'],
            marker_color='#3B82F6', opacity=0.8
        ))
        fig.add_trace(go.Scatter(
            name='Budget', x=df_v['Mese'], y=df_v['Budget'],
            mode='lines+markers',
            line=dict(color='#C9A84C', width=2.5, dash='dot'),
            marker=dict(size=7)
        ))
        fig.update_layout(
            plot_bgcolor='#0A1628', paper_bgcolor='#0A1628',
            font=dict(color='#94A3B8', size=11),
            height=320,
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color='#94A3B8')),
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(showgrid=False, tickangle=-30, tickfont=dict(color='#64748B')),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.04)',
                       tickformat=',.0f', ticksuffix=' €', tickfont=dict(color='#64748B')),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Tabella riepilogo
    st.markdown("---")
    st.markdown("#### Riepilogo scostamenti per voce")
    riepilogo = df_sc.groupby('Voce').agg(
        Effettivo=('Effettivo','sum'),
        Budget=('Budget','sum'),
        Scostamento=('Scostamento','sum')
    ).reset_index()
    riepilogo['Sc%'] = (riepilogo['Scostamento'] / riepilogo['Budget'].replace(0, float('nan')) * 100).round(1)

    def color_cell(val):
        try:
            v = float(val)
            if v <= -20: return 'color: #EF4444; font-weight:700'
            if v <= -10: return 'color: #F59E0B'
            if v >= 10:  return 'color: #10B981'
            return 'color: #94A3B8'
        except Exception:
            return ''

    st.dataframe(
        riepilogo.style
            .format({'Effettivo': lambda x: fmt_eur(x),
                     'Budget': lambda x: fmt_eur(x),
                     'Scostamento': lambda x: fmt_eur(x),
                     'Sc%': '{:+.1f}%'})
            .applymap(color_cell, subset=['Sc%']),
        use_container_width=True, height=350
    )


def _alert_intelligenti(pivot, budget, cols_mesi, voci) -> list:
    """Alert con soglia adattiva basata su volatilità storica."""
    alerts = []
    for voce in voci:
        if voce not in budget or voce not in pivot.index:
            continue
        sc_list = []
        for m in cols_mesi:
            eff = float(pivot.loc[voce, m]) if m in pivot.columns else 0
            bud = budget[voce].get(m, 0)
            if bud != 0:
                sc_list.append((eff - bud) / abs(bud) * 100)
        if len(sc_list) < 2:
            continue

        finestra = sc_list[-5:]
        media = np.mean(finestra)
        std   = np.std(finestra)
        soglia = max(abs(media) + 1.5 * std, 15)

        ultimo_m = cols_mesi[-1]
        eff_u = float(pivot.loc[voce, ultimo_m]) if ultimo_m in pivot.columns else 0
        bud_u = budget[voce].get(ultimo_m, 0)
        if bud_u == 0:
            continue
        sc_u = (eff_u - bud_u) / abs(bud_u) * 100

        if abs(sc_u) >= soglia:
            alerts.append({
                'voce': voce,
                'mese': ultimo_m,
                'sc_pct': sc_u,
                'tipo': 'NEG' if sc_u < 0 else 'POS',
                'motivo': f"Scostamento {sc_u:+.1f}% supera soglia adattiva {soglia:.1f}% (media±1.5σ su {len(finestra)} periodi)"
            })
    return sorted(alerts, key=lambda x: abs(x['sc_pct']), reverse=True)
