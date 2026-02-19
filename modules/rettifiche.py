"""rettifiche.py — Rettifiche extra-contabili."""
import streamlit as st
import pandas as pd
from services.data_utils import get_cliente, save_cliente, find_column, fmt_eur


def render_rettifiche():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("⚠️ Seleziona un cliente dalla sidebar."); return
    cliente  = get_cliente()
    df_piano = cliente.get('df_piano')
    retts    = cliente.get('rettifiche', [])

    st.markdown(f"""
    <div style='margin-bottom:20px'>
        <div style='font-size:10px;text-transform:uppercase;letter-spacing:2px;color:#C9A84C;font-weight:700;margin-bottom:4px'>Rettifiche Extra-Contabili</div>
        <div style='font-size:1.4rem;font-weight:700;color:#F1F5F9'>✏️ {ca}</div>
        <div style='font-size:0.8rem;color:#475569'>Scritture di rettifica che non modificano il DB contabile originale</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style='background:rgba(139,92,246,0.06);border-left:3px solid #8B5CF6;
                border-radius:0 10px 10px 0;padding:12px 16px;font-size:0.83rem;color:#64748B;margin-bottom:20px'>
    Le rettifiche sono sommate ai dati contabili <strong style='color:#E2E8F0'>senza modificare i file originali</strong>.
    Attivabili/disattivabili singolarmente per simulazioni e analisi what-if.
    </div>""", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["➕ Nuova Rettifica", "📋 Elenco Rettifiche"])

    with tab1:
        # Costruisci opzioni conto
        if df_piano is not None:
            col_cod  = find_column(df_piano, ['Codice','codice','CodConto','Conto','conto'])
            col_desc = find_column(df_piano, ['Descrizione','descrizione','Nome','nome','Conto','conto'])
            if col_cod:
                if col_desc and col_desc != col_cod:
                    opts = [f"{r[col_cod]} — {r[col_desc]}" for _, r in df_piano.iterrows()]
                    cod_map = {f"{r[col_cod]} — {r[col_desc]}": str(r[col_cod]) for _, r in df_piano.iterrows()}
                else:
                    opts = df_piano[col_cod].astype(str).tolist()
                    cod_map = {v: v for v in opts}
                use_select = True
            else:
                use_select = False; opts = []; cod_map = {}
        else:
            use_select = False; opts = []; cod_map = {}

        with st.form("form_rett", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                if use_select and opts:
                    conto_sel = st.selectbox("Conto *", opts, key="rtt_conto")
                    conto_cod = cod_map.get(conto_sel, conto_sel)
                else:
                    conto_cod = st.text_input("Conto *", placeholder="es. 700001", key="rtt_conto_m")
                    conto_sel = conto_cod
                desc_rtt = st.text_input("Descrizione *", placeholder="es. Rateo attivo interessi")
                tipo_rtt = st.selectbox("Tipo:", [
                    "Rateo attivo","Rateo passivo","Risconto attivo","Risconto passivo",
                    "Ammortamento extracontabile","Accantonamento","Simulazione","Altro"
                ])
            with c2:
                importo = st.number_input("Importo (€) *", value=0.0, step=100.0,
                                           format="%.2f",
                                           help="+pos aumenta il saldo, -neg lo riduce")
                data_rtt = st.date_input("Data competenza")
                note_rtt = st.text_area("Note", height=68, placeholder="Riferimento documentale…")

            if st.form_submit_button("➕ Aggiungi Rettifica", type="primary"):
                if not conto_cod.strip():
                    st.error("Inserisci il conto.")
                elif not desc_rtt.strip():
                    st.error("Inserisci una descrizione.")
                elif importo == 0:
                    st.warning("Importo è 0.")
                else:
                    retts.append({
                        'id': len(retts) + 1,
                        'conto': conto_cod.strip(),
                        'conto_label': conto_sel,
                        'descrizione': desc_rtt.strip(),
                        'importo': importo,
                        'data': data_rtt.strftime('%d/%m/%Y'),
                        'mese': data_rtt.strftime('%Y-%m'),
                        'tipo': tipo_rtt,
                        'note': note_rtt.strip(),
                        'attiva': True
                    })
                    save_cliente({'rettifiche': retts})
                    st.success(f"✅ Rettifica aggiunta: {desc_rtt} — {fmt_eur(importo)}")
                    st.rerun()

    with tab2:
        if not retts:
            st.info("Nessuna rettifica inserita.")
            return

        attive  = [r for r in retts if r.get('attiva', True)]
        tot_pos = sum(r['importo'] for r in attive if r['importo'] > 0)
        tot_neg = sum(r['importo'] for r in attive if r['importo'] < 0)

        c1, c2, c3 = st.columns(3)
        c1.metric("Totale", len(retts))
        c2.metric("Effetto +", fmt_eur(tot_pos))
        c3.metric("Effetto netto", fmt_eur(tot_pos + tot_neg))

        # Tabella
        df_r = pd.DataFrame(retts)
        show_cols = [c for c in ['id','conto','descrizione','tipo','importo','data','attiva'] if c in df_r.columns]
        st.dataframe(df_r[show_cols].style.format({'importo': lambda x: fmt_eur(float(x))}),
                     use_container_width=True, height=280)

        st.markdown("---")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            id_sel = st.number_input("ID rettifica:", min_value=1,
                                      max_value=max(r['id'] for r in retts), step=1, key="rtt_id")
        with col_g2:
            azione = st.selectbox("Azione:", ["Disattiva","Riattiva","Elimina"], key="rtt_az")
        if st.button("Applica"):
            idx = next((i for i, r in enumerate(retts) if r['id'] == id_sel), None)
            if idx is not None:
                if azione == "Disattiva":     retts[idx]['attiva'] = False
                elif azione == "Riattiva":    retts[idx]['attiva'] = True
                elif azione == "Elimina":     retts.pop(idx)
                save_cliente({'rettifiche': retts})
                st.rerun()

        csv = df_r[show_cols].to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("⬇️ Esporta CSV", data=csv,
                            file_name=f"rettifiche_{ca}.csv", mime="text/csv")
