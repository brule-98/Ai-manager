import streamlit as st
import pandas as pd
from services.data_utils import get_cliente, save_cliente, find_column, fmt_eur


def render_rettifiche():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("⚠️ Seleziona un cliente dalla sidebar.")
        return

    cliente = get_cliente()
    df_piano = cliente.get('df_piano')
    rettifiche = cliente.get('rettifiche', [])

    st.markdown(f"## ✏️ Rettifiche Extra-Contabili — {ca}")
    st.markdown("""
    <div style='background:#EEF2FF; border-left:4px solid #7C3AED; padding:12px 16px; border-radius:6px; font-size:0.85rem; margin-bottom:1.2rem;'>
    Le rettifiche extra-contabili sono scritture di aggiustamento che vengono sommate al DB contabile
    senza modificare i dati originali. Utili per ratei, risconti, rettifiche di fine periodo o simulazioni.
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["➕ Nuova Rettifica", "📋 Rettifiche Inserite"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: NUOVA RETTIFICA
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### Inserimento Rettifica")

        if df_piano is None:
            st.warning("⚠️ Carica prima il Piano dei Conti nel Workspace per selezionare i conti.")
            # Permetti inserimento manuale come fallback
            conto_options = []
            use_manual = True
        else:
            col_cod = find_column(df_piano, ['Codice', 'codice', 'codice conto', 'Codice Conto', 'CODICE', 'Conto', 'conto'])
            col_desc = find_column(df_piano, ['Descrizione', 'descrizione', 'conto', 'Conto', 'Nome', 'nome'])
            if col_cod:
                if col_desc:
                    conto_options = [f"{r[col_cod]} — {r[col_desc]}" for _, r in df_piano.iterrows()]
                    conto_map = {f"{r[col_cod]} — {r[col_desc]}": str(r[col_cod]) for _, r in df_piano.iterrows()}
                else:
                    conto_options = df_piano[col_cod].astype(str).tolist()
                    conto_map = {v: v for v in conto_options}
                use_manual = False
            else:
                conto_options = []
                use_manual = True

        with st.form("form_rettifica", clear_on_submit=True):
            c1, c2 = st.columns(2)

            with c1:
                if use_manual or not conto_options:
                    conto_input = st.text_input("Conto *", placeholder="es. 700001")
                    conto_sel = conto_input
                    conto_cod = conto_input
                else:
                    conto_sel = st.selectbox("Conto *", conto_options, key="rtt_conto_sel")
                    conto_cod = conto_map.get(conto_sel, conto_sel)

                descrizione = st.text_input("Descrizione *", placeholder="es. Rateo attivo interesse maturato")
                data_rtt = st.date_input("Data competenza")

            with c2:
                importo = st.number_input(
                    "Importo (€) *",
                    value=0.0,
                    step=100.0,
                    format="%.2f",
                    help="Positivo = aumento del saldo / Negativo = riduzione del saldo"
                )
                note = st.text_area("Note", placeholder="Dettaglio o riferimento documentale...", height=80)

                tipo = st.selectbox("Tipo rettifica:", [
                    "Rateo attivo", "Rateo passivo", "Risconto attivo", "Risconto passivo",
                    "Ammortamento extracontabile", "Accantonamento", "Altro"
                ])

            st.markdown("---")
            submitted = st.form_submit_button("➕ Aggiungi Rettifica", type="primary", use_container_width=False)

            if submitted:
                if not conto_cod.strip():
                    st.error("Inserisci il conto.")
                elif not descrizione.strip():
                    st.error("Inserisci una descrizione.")
                elif importo == 0:
                    st.warning("L'importo è 0. Inserisci un valore diverso da zero.")
                else:
                    nuova = {
                        'id': len(rettifiche) + 1,
                        'conto': conto_cod.strip(),
                        'conto_label': conto_sel if not use_manual else conto_cod,
                        'descrizione': descrizione.strip(),
                        'importo': importo,
                        'data': data_rtt.strftime('%d/%m/%Y'),
                        'mese': data_rtt.strftime('%Y-%m'),
                        'tipo': tipo,
                        'note': note.strip(),
                        'attiva': True
                    }
                    rettifiche.append(nuova)
                    save_cliente({'rettifiche': rettifiche})
                    st.success(f"✅ Rettifica aggiunta: {descrizione} — {fmt_eur(importo)}")
                    st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: RETTIFICHE INSERITE
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### Rettifiche Extra-Contabili Registrate")

        if not rettifiche:
            st.info("Nessuna rettifica inserita per questo cliente.")
            return

        # Stats
        rtt_attive = [r for r in rettifiche if r.get('attiva', True)]
        totale_pos = sum(r['importo'] for r in rtt_attive if r['importo'] > 0)
        totale_neg = sum(r['importo'] for r in rtt_attive if r['importo'] < 0)
        effetto_netto = totale_pos + totale_neg

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Totale rettifiche", len(rettifiche))
        c2.metric("Attive", len(rtt_attive))
        c3.metric("Effetto + (incremento)", fmt_eur(totale_pos))
        c4.metric("Effetto netto", fmt_eur(effetto_netto))

        st.markdown("---")

        # Tabella interattiva
        df_rtt = pd.DataFrame(rettifiche)
        cols_show = ['id', 'conto', 'descrizione', 'tipo', 'importo', 'data', 'mese', 'attiva']
        cols_show = [c for c in cols_show if c in df_rtt.columns]
        df_display = df_rtt[cols_show].copy()
        df_display.columns = ['ID', 'Conto', 'Descrizione', 'Tipo', 'Importo (€)', 'Data', 'Mese', 'Attiva']

        # Formatta importo
        df_display['Importo (€)'] = df_display['Importo (€)'].apply(lambda x: fmt_eur(x, show_sign=True))

        st.dataframe(df_display, use_container_width=True, height=300)

        st.markdown("---")
        st.markdown("#### Gestione Rettifiche")

        c1, c2 = st.columns(2)
        with c1:
            id_sel = st.number_input("ID rettifica da modificare:", min_value=1,
                                      max_value=max(r['id'] for r in rettifiche), step=1,
                                      key="rtt_id_sel")

        with c2:
            azione = st.selectbox("Azione:", ["Disattiva (escludi dal CE)", "Riattiva", "Elimina definitivamente"],
                                   key="rtt_azione")

        if st.button("Applica", key="btn_applica_rtt"):
            idx = next((i for i, r in enumerate(rettifiche) if r['id'] == id_sel), None)
            if idx is not None:
                if azione == "Disattiva (escludi dal CE)":
                    rettifiche[idx]['attiva'] = False
                    st.success("Rettifica disattivata.")
                elif azione == "Riattiva":
                    rettifiche[idx]['attiva'] = True
                    st.success("Rettifica riattivata.")
                elif azione == "Elimina definitivamente":
                    rettifiche.pop(idx)
                    st.success("Rettifica eliminata.")
                save_cliente({'rettifiche': rettifiche})
                st.rerun()
            else:
                st.error(f"ID {id_sel} non trovato.")

        # Export
        if rettifiche:
            csv = df_display.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button("⬇️ Esporta Rettifiche CSV", data=csv,
                                file_name=f"rettifiche_{ca}.csv", mime="text/csv")
