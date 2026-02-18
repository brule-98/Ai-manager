import streamlit as st
import pandas as pd
from services.data_utils import get_cliente, save_cliente, find_column


def render_configurazione():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("⚠️ Seleziona un cliente dalla sidebar.")
        return

    cliente = get_cliente()
    df_ricl = cliente.get('df_ricl')
    schemi = cliente.get('schemi', {})
    schema_attivo = cliente.get('schema_attivo', '')

    st.markdown(f"## ⚙️ Configurazione Schema — {ca}")
    st.markdown("""
    <div style='background:#FEF3C7; border-left:4px solid #D97706; padding:12px 16px; border-radius:6px; font-size:0.85rem; margin-bottom:1.2rem;'>
    Qui puoi configurare l'ordine delle voci nel CE, il segno (le voci di costo vanno invertite di segno
    per mostrare valori positivi nel report), e identificare le righe di subtotale da evidenziare in grassetto.
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🗂️ Gestione Schemi", "⚙️ Configurazione Voci"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: GESTIONE SCHEMI
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### Schemi di Riclassificazione")
        st.markdown("Puoi avere più schemi (es. CE Gestionale, CE Civilistico, CE per Area) e passare da uno all'altro nella Dashboard.")

        # Lista schemi esistenti
        if schemi:
            st.markdown("**Schemi configurati:**")
            for nome_schema, config in schemi.items():
                n_voci = len(config)
                is_active = nome_schema == schema_attivo
                col_a, col_b, col_c = st.columns([3, 1, 1])
                with col_a:
                    badge = "🟢 **ATTIVO**" if is_active else "⚪"
                    st.markdown(f"{badge} &nbsp; **{nome_schema}** &nbsp; ({n_voci} voci configurate)")
                with col_b:
                    if not is_active:
                        if st.button("Attiva", key=f"attiva_{nome_schema}"):
                            save_cliente({'schema_attivo': nome_schema})
                            st.success(f"Schema '{nome_schema}' attivato")
                            st.rerun()
                with col_c:
                    if st.button("Elimina", key=f"elimina_{nome_schema}"):
                        del schemi[nome_schema]
                        if schema_attivo == nome_schema:
                            save_cliente({'schemi': schemi, 'schema_attivo': ''})
                        else:
                            save_cliente({'schemi': schemi})
                        st.rerun()
        else:
            st.info("Nessuno schema configurato. Creane uno qui sotto.")

        st.markdown("---")
        st.markdown("#### Crea nuovo schema")

        with st.form("form_nuovo_schema"):
            nome_nuovo = st.text_input("Nome schema *", placeholder="es. CE Gestionale 2024")
            st.form_submit_button_pressed = st.form_submit_button("Crea Schema")
            if st.form_submit_button_pressed:
                n = nome_nuovo.strip()
                if not n:
                    st.error("Inserisci un nome per lo schema.")
                elif n in schemi:
                    st.error(f"Schema '{n}' già esistente.")
                else:
                    # Inizializza con voci dal df_ricl se disponibile
                    config_init = {}
                    if df_ricl is not None:
                        col_cod = find_column(df_ricl, ['Codice', 'codice', 'Voce', 'voce', 'ID'])
                        col_desc = find_column(df_ricl, ['Descrizione', 'descrizione', 'voce', 'Voce', 'Nome'])
                        for i, (_, row) in enumerate(df_ricl.iterrows()):
                            voce = str(row[col_cod]) if col_cod else f"voce_{i}"
                            config_init[voce] = {
                                'ordine': i * 10,
                                'segno': 1,
                                'subtotale': False,
                                'descrizione_override': str(row[col_desc]) if col_desc else voce
                            }
                    schemi[n] = config_init
                    save_cliente({'schemi': schemi, 'schema_attivo': n})
                    st.success(f"✅ Schema '{n}' creato con {len(config_init)} voci")
                    st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: CONFIGURAZIONE VOCI
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### Configurazione Voci dello Schema")

        if not schemi:
            st.info("Crea prima uno schema nel tab 'Gestione Schemi'.")
            return

        schema_sel = st.selectbox("Schema da configurare:",
                                   list(schemi.keys()),
                                   index=list(schemi.keys()).index(schema_attivo) if schema_attivo in schemi else 0,
                                   key="conf_schema_sel")

        config = schemi.get(schema_sel, {})

        if not config:
            st.info("Schema vuoto. Carica lo Schema di Riclassifica nel Workspace per popolare automaticamente.")
            # Possibilità di aggiungere voce manuale
            _form_aggiungi_voce(schema_sel, config, schemi)
            return

        st.markdown(f"**Configurazione: {schema_sel}** ({len(config)} voci)")
        st.markdown("""
        <div style='font-size:0.8rem; color:#6B7280; margin-bottom:1rem;'>
        ⚙️ <b>Segno:</b> +1 = mantieni segno contabile (es. ricavi), -1 = inverti (es. costi mostrati come positivi)<br>
        📌 <b>Subtotale:</b> la voce viene evidenziata in grassetto nel report come riga di totale
        </div>
        """, unsafe_allow_html=True)

        # Tabella di configurazione
        col_headers = st.columns([1, 3, 1, 1, 1, 1])
        col_headers[0].markdown("**Ordine**")
        col_headers[1].markdown("**Voce**")
        col_headers[2].markdown("**Segno**")
        col_headers[3].markdown("**Subtotale**")
        col_headers[4].markdown("**Etichetta**")
        col_headers[5].markdown("**Azioni**")

        config_updated = dict(config)
        voci_ordinate = sorted(config.keys(), key=lambda v: config[v].get('ordine', 999))

        for voce in voci_ordinate:
            cfg = config[voce]
            cols = st.columns([1, 3, 1, 1, 2, 1])

            with cols[0]:
                new_ord = st.number_input(
                    "ord", value=int(cfg.get('ordine', 0)), step=10,
                    label_visibility="collapsed", key=f"ord_{schema_sel}_{voce}"
                )
                config_updated[voce]['ordine'] = new_ord

            with cols[1]:
                st.markdown(f"<div style='padding:8px 4px; font-size:0.83rem; color:#374151;'>{voce}</div>",
                            unsafe_allow_html=True)

            with cols[2]:
                segno = st.selectbox(
                    "segno", [1, -1],
                    index=0 if cfg.get('segno', 1) == 1 else 1,
                    format_func=lambda x: "+1 (mantieni)" if x == 1 else "-1 (inverti)",
                    label_visibility="collapsed", key=f"sgn_{schema_sel}_{voce}"
                )
                config_updated[voce]['segno'] = segno

            with cols[3]:
                subtotale = st.checkbox(
                    "st", value=cfg.get('subtotale', False),
                    label_visibility="collapsed", key=f"sub_{schema_sel}_{voce}"
                )
                config_updated[voce]['subtotale'] = subtotale

            with cols[4]:
                label_ov = st.text_input(
                    "label", value=cfg.get('descrizione_override', voce),
                    label_visibility="collapsed", key=f"lbl_{schema_sel}_{voce}"
                )
                config_updated[voce]['descrizione_override'] = label_ov

            with cols[5]:
                if st.button("🗑️", key=f"del_{schema_sel}_{voce}", help="Elimina voce"):
                    del config_updated[voce]
                    schemi[schema_sel] = config_updated
                    save_cliente({'schemi': schemi})
                    st.rerun()

        st.markdown("---")

        col_save1, col_save2 = st.columns([1, 4])
        with col_save1:
            if st.button("💾 Salva Configurazione", type="primary"):
                schemi[schema_sel] = config_updated
                save_cliente({'schemi': schemi, 'schema_attivo': schema_sel})
                st.success(f"✅ Configurazione schema '{schema_sel}' salvata")
                st.rerun()

        st.markdown("---")
        _form_aggiungi_voce(schema_sel, config_updated, schemi)


def _form_aggiungi_voce(schema_sel, config, schemi):
    """Form per aggiungere una voce manualmente."""
    with st.expander("➕ Aggiungi voce manualmente"):
        with st.form(f"form_add_voce_{schema_sel}"):
            c1, c2, c3, c4 = st.columns(4)
            codice_v = c1.text_input("Codice voce *")
            label_v = c2.text_input("Etichetta display")
            segno_v = c3.selectbox("Segno", [1, -1],
                                    format_func=lambda x: "+1 mantieni" if x == 1 else "-1 inverti")
            subtot_v = c4.checkbox("È subtotale")

            if st.form_submit_button("Aggiungi"):
                cod = codice_v.strip()
                if not cod:
                    st.error("Inserisci il codice voce.")
                elif cod in config:
                    st.error("Voce già esistente.")
                else:
                    config[cod] = {
                        'ordine': (max([v.get('ordine', 0) for v in config.values()], default=0) + 10),
                        'segno': segno_v,
                        'subtotale': subtot_v,
                        'descrizione_override': label_v.strip() or cod
                    }
                    schemi[schema_sel] = config
                    save_cliente({'schemi': schemi})
                    st.success(f"Voce '{cod}' aggiunta.")
                    st.rerun()
