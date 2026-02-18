import streamlit as st
import pandas as pd
from services.data_utils import smart_load, find_column, get_cliente, save_cliente
from services.ai_mapper import ai_suggest_mapping, ai_suggest_new_accounts


def render_workspace():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("⚠️ Seleziona o crea un cliente dalla sidebar per iniziare.")
        return

    cliente = get_cliente()

    st.markdown(f"## 🗂️ Workspace Dati — {ca}")
    st.markdown("Carica i file del cliente e configura la mappatura dei conti.")

    tab1, tab2, tab3 = st.tabs(["📂 Caricamento File", "🔗 Mappatura Conti", "🔑 Configurazione API"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: CARICAMENTO FILE
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### Importazione dati contabili")
        st.markdown("""
        <div style='background:#EEF2FF; border-left:4px solid #1A3A7A; padding:12px 16px; border-radius:6px; font-size:0.85rem; margin-bottom:1rem;'>
        Carica i tre file richiesti. Sono supportati i formati <b>CSV</b> (separatore ; o ,) e <b>Excel (.xlsx)</b>.
        I caratteri speciali italiani vengono gestiti automaticamente.
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("**1. Piano dei Conti**")
            st.caption("Colonne minime: Codice, Descrizione")
            u_piano = st.file_uploader("Piano dei Conti", type=["csv", "xlsx", "xls"],
                                        key=f"u_piano_{ca}", label_visibility="collapsed")
            if u_piano:
                df = smart_load(u_piano)
                if df is not None:
                    save_cliente({'df_piano': df})
                    st.success(f"✅ {len(df)} conti caricati")
                    st.dataframe(df.head(5), use_container_width=True, height=180)
                else:
                    st.error("Errore lettura file")
            elif cliente.get('df_piano') is not None:
                st.info(f"📋 Piano caricato: {len(cliente['df_piano'])} conti")

        with c2:
            st.markdown("**2. DB Contabile / Movimenti**")
            st.caption("Colonne minime: Data, Conto, Saldo/Importo")
            u_db = st.file_uploader("DB Contabile", type=["csv", "xlsx", "xls"],
                                     key=f"u_db_{ca}", label_visibility="collapsed")
            if u_db:
                df = smart_load(u_db)
                if df is not None:
                    save_cliente({'df_db': df})
                    st.success(f"✅ {len(df)} righe caricate")
                    st.dataframe(df.head(5), use_container_width=True, height=180)
                else:
                    st.error("Errore lettura file")
            elif cliente.get('df_db') is not None:
                st.info(f"📋 DB caricato: {len(cliente['df_db'])} righe")

        with c3:
            st.markdown("**3. Schema di Riclassifica**")
            st.caption("Colonne minime: Codice, Descrizione voce CE")
            u_ricl = st.file_uploader("Schema Riclassifica", type=["csv", "xlsx", "xls"],
                                       key=f"u_ricl_{ca}", label_visibility="collapsed")
            if u_ricl:
                df = smart_load(u_ricl)
                if df is not None:
                    save_cliente({'df_ricl': df})
                    st.success(f"✅ {len(df)} voci schema")
                    st.dataframe(df.head(5), use_container_width=True, height=180)
                else:
                    st.error("Errore lettura file")
            elif cliente.get('df_ricl') is not None:
                st.info(f"📋 Schema caricato: {len(cliente['df_ricl'])} voci")

        # Stato caricamento
        st.markdown("---")
        stati = {
            'Piano dei Conti': cliente.get('df_piano') is not None,
            'DB Contabile': cliente.get('df_db') is not None,
            'Schema Riclassifica': cliente.get('df_ricl') is not None,
        }
        cols = st.columns(3)
        for i, (nome, ok) in enumerate(stati.items()):
            with cols[i]:
                if ok:
                    st.markdown(f"<div style='text-align:center; padding:10px; background:#D1FAE5; border-radius:8px; color:#065F46; font-weight:500; font-size:0.85rem;'>✅ {nome}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='text-align:center; padding:10px; background:#FEF3C7; border-radius:8px; color:#92400E; font-weight:500; font-size:0.85rem;'>⏳ {nome}</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: MAPPATURA CONTI
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### Mappatura Conti → Schema Riclassifica")

        df_piano = cliente.get('df_piano')
        df_ricl = cliente.get('df_ricl')
        mapping = cliente.get('mapping', {})

        if df_piano is None or df_ricl is None:
            st.warning("⚠️ Carica prima il Piano dei Conti e lo Schema di Riclassifica (Tab 1)")
            return

        # Individua colonne chiave
        col_cod_piano = find_column(df_piano, ['Codice', 'codice', 'codice conto', 'Codice Conto', 'CODICE', 'conto', 'Conto'])
        col_desc_piano = find_column(df_piano, ['Descrizione', 'descrizione', 'conto', 'Conto', 'Nome', 'nome', 'DESCRIZIONE'])
        col_cod_ricl = find_column(df_ricl, ['Codice', 'codice', 'Voce', 'voce', 'ID', 'id', 'Codice Voce'])
        col_desc_ricl = find_column(df_ricl, ['Descrizione', 'descrizione', 'voce', 'Voce', 'Nome', 'nome'])

        if not col_cod_piano:
            st.error("Non trovo la colonna 'Codice' nel piano dei conti. Rinomina la colonna e ricarica.")
            return
        if not col_cod_ricl:
            st.error("Non trovo la colonna 'Codice' nello schema di riclassifica. Rinomina la colonna e ricarica.")
            return

        # Opzioni voci riclassifica
        voci_ricl = df_ricl[col_cod_ricl].astype(str).tolist()
        if col_desc_ricl:
            voci_ricl_label = {
                str(row[col_cod_ricl]): f"{row[col_cod_ricl]} — {row[col_desc_ricl]}"
                for _, row in df_ricl.iterrows()
            }
        else:
            voci_ricl_label = {v: v for v in voci_ricl}

        # Sezione AI
        st.markdown("#### 🤖 Mappatura Automatica con AI")

        n_mappati = len([v for v in mapping.values() if v])
        n_totale = len(df_piano)
        n_nuovi = n_totale - n_mappati

        col_stat1, col_stat2, col_stat3 = st.columns(3)
        col_stat1.metric("Conti totali", n_totale)
        col_stat2.metric("Già mappati", n_mappati)
        col_stat3.metric("Da mappare", n_nuovi)

        col_ai1, col_ai2 = st.columns(2)

        with col_ai1:
            if st.button("🤖 Mappa TUTTI i conti con AI", use_container_width=True,
                          help="Rimappa tutti i conti, inclusi quelli già mappati"):
                _esegui_mapping_ai(df_piano, df_ricl, mapping, full=True)

        with col_ai2:
            if st.button("✨ Mappa solo conti NUOVI con AI", use_container_width=True,
                          help="Aggiunge la mappatura solo per i conti non ancora mappati",
                          disabled=(n_nuovi == 0)):
                _esegui_mapping_ai(df_piano, df_ricl, mapping, full=False)

        # Mappatura manuale
        st.markdown("---")
        st.markdown("#### ✏️ Mappatura Manuale / Revisione")
        st.caption("Puoi modificare o completare manualmente la mappatura qui sotto.")

        voci_options = ['(non mappato)'] + list(voci_ricl_label.values())

        # Filtro per visualizzazione
        filtro = st.radio("Visualizza:", ["Tutti", "Solo non mappati", "Solo mappati"],
                           horizontal=True, key="filtro_mapping")

        conti_da_mostrare = df_piano.copy()
        if filtro == "Solo non mappati":
            conti_da_mostrare = conti_da_mostrare[
                ~conti_da_mostrare[col_cod_piano].astype(str).isin(
                    [k for k, v in mapping.items() if v]
                )
            ]
        elif filtro == "Solo mappati":
            conti_da_mostrare = conti_da_mostrare[
                conti_da_mostrare[col_cod_piano].astype(str).isin(
                    [k for k, v in mapping.items() if v]
                )
            ]

        # Mostra massimo 50 alla volta per performance
        if len(conti_da_mostrare) > 50:
            st.info(f"Mostro 50 di {len(conti_da_mostrare)} conti. Usa il filtro per restringere.")
            conti_da_mostrare = conti_da_mostrare.head(50)

        for _, row in conti_da_mostrare.iterrows():
            codice = str(row[col_cod_piano])
            desc = str(row[col_desc_piano]) if col_desc_piano else codice
            voce_attuale = mapping.get(codice, None)

            # Determina indice corrente nel selectbox
            if voce_attuale and voce_attuale in voci_ricl_label:
                label_attuale = voci_ricl_label[voce_attuale]
                idx = voci_options.index(label_attuale) if label_attuale in voci_options else 0
            else:
                idx = 0

            col_a, col_b = st.columns([2, 3])
            with col_a:
                st.markdown(f"<div style='padding:8px 0; font-size:0.84rem;'><b>{codice}</b> — {desc}</div>",
                            unsafe_allow_html=True)
            with col_b:
                sel = st.selectbox(
                    f"Voce_{codice}",
                    options=voci_options,
                    index=idx,
                    label_visibility="collapsed",
                    key=f"map_{ca}_{codice}"
                )
                # Aggiorna mapping in real time
                if sel == '(non mappato)':
                    mapping.pop(codice, None)
                else:
                    # Ricava codice dalla label
                    for k, v in voci_ricl_label.items():
                        if v == sel:
                            mapping[codice] = k
                            break

        save_cliente({'mapping': mapping})

        st.markdown("---")
        if st.button("💾 Salva Mappatura", type="primary", use_container_width=False):
            save_cliente({'mapping': mapping})
            st.success(f"✅ Mappatura salvata: {len([v for v in mapping.values() if v])} conti mappati")


def _esegui_mapping_ai(df_piano, df_ricl, mapping_corrente, full=True):
    """Wrapper per chiamata AI con spinner e gestione errori."""
    ca = st.session_state.get('cliente_attivo')

    api_key = st.session_state.get('anthropic_api_key', '')
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass

    if not api_key:
        st.error("⚠️ Configura la API Key Anthropic nel Tab 'Configurazione API'")
        return

    with st.spinner("🤖 AI in elaborazione... potrebbe richiedere 20-40 secondi"):
        try:
            from services.ai_mapper import ai_suggest_mapping, ai_suggest_new_accounts
            if full:
                nuovo_mapping = ai_suggest_mapping(df_piano, df_ricl, mapping_corrente)
            else:
                nuovo_mapping = ai_suggest_new_accounts(df_piano, df_ricl, mapping_corrente)

            mapping_corrente.update(nuovo_mapping)
            save_cliente({'mapping': mapping_corrente})
            n = len([v for v in nuovo_mapping.values() if v])
            st.success(f"✅ AI ha mappato {n} conti con successo!")
            st.rerun()
        except Exception as e:
            st.error(f"Errore AI: {e}")


def render_api_tab():
    """Tab configurazione API Key."""
    st.markdown("### 🔑 Configurazione API Anthropic")
    st.markdown("""
    <div style='background:#FEF3C7; border-left:4px solid #D97706; padding:12px 16px; border-radius:6px; font-size:0.84rem; margin-bottom:1rem;'>
    La chiave API è necessaria per utilizzare la mappatura automatica con AI.
    Puoi ottenerla su <a href='https://console.anthropic.com' target='_blank'>console.anthropic.com</a>.
    In produzione, inseriscila nel file <code>.streamlit/secrets.toml</code>.
    </div>
    """, unsafe_allow_html=True)

    current = st.session_state.get('anthropic_api_key', '')
    key_display = current[:8] + '...' + current[-4:] if len(current) > 15 else ''

    if key_display:
        st.success(f"✅ API Key configurata: {key_display}")

    new_key = st.text_input("Inserisci API Key:", type="password",
                             placeholder="sk-ant-api03-...",
                             help="La chiave viene salvata solo nella sessione corrente")

    if st.button("Salva API Key") and new_key.strip():
        st.session_state['anthropic_api_key'] = new_key.strip()
        st.success("✅ API Key salvata per questa sessione")
        st.rerun()


# Override render_workspace per includere il tab API
_original_render = render_workspace

def render_workspace():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("⚠️ Seleziona o crea un cliente dalla sidebar per iniziare.")
        return

    cliente = get_cliente()

    st.markdown(f"## 🗂️ Workspace Dati — {ca}")
    st.markdown("Carica i file del cliente e configura la mappatura dei conti.")

    tab1, tab2, tab3 = st.tabs(["📂 Caricamento File", "🔗 Mappatura Conti", "🔑 API Key"])

    with tab1:
        _render_caricamento(ca, cliente)

    with tab2:
        _render_mappatura(ca, cliente)

    with tab3:
        render_api_tab()


def _render_caricamento(ca, cliente):
    st.markdown("### Importazione dati contabili")
    st.markdown("""
    <div style='background:#EEF2FF; border-left:4px solid #1A3A7A; padding:12px 16px; border-radius:6px; font-size:0.85rem; margin-bottom:1rem;'>
    Carica i tre file richiesti. Sono supportati <b>CSV</b> (separatore ; o ,) e <b>Excel (.xlsx)</b>.
    I caratteri speciali italiani (encoding latin1/utf-8) vengono gestiti automaticamente.
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**1. Piano dei Conti**")
        st.caption("Colonne attese: Codice, Descrizione")
        u_piano = st.file_uploader("Piano dei Conti", type=["csv", "xlsx", "xls"],
                                    key=f"u_piano_{ca}", label_visibility="collapsed")
        if u_piano:
            df = smart_load(u_piano)
            if df is not None:
                save_cliente({'df_piano': df})
                st.success(f"✅ {len(df)} conti caricati")
                with st.expander("Anteprima"):
                    st.dataframe(df.head(8), use_container_width=True)
            else:
                st.error("Errore lettura file")
        elif cliente.get('df_piano') is not None:
            st.info(f"📋 {len(cliente['df_piano'])} conti in memoria")
            with st.expander("Anteprima"):
                st.dataframe(cliente['df_piano'].head(8), use_container_width=True)

    with c2:
        st.markdown("**2. DB Contabile / Movimenti**")
        st.caption("Colonne attese: Data, Conto, Saldo")
        u_db = st.file_uploader("DB Contabile", type=["csv", "xlsx", "xls"],
                                 key=f"u_db_{ca}", label_visibility="collapsed")
        if u_db:
            df = smart_load(u_db)
            if df is not None:
                save_cliente({'df_db': df})
                st.success(f"✅ {len(df)} movimenti caricati")
                with st.expander("Anteprima"):
                    st.dataframe(df.head(8), use_container_width=True)
            else:
                st.error("Errore lettura file")
        elif cliente.get('df_db') is not None:
            st.info(f"📋 {len(cliente['df_db'])} righe in memoria")
            with st.expander("Anteprima"):
                st.dataframe(cliente['df_db'].head(8), use_container_width=True)

    with c3:
        st.markdown("**3. Schema di Riclassifica**")
        st.caption("Colonne attese: Codice, Descrizione voce CE")
        u_ricl = st.file_uploader("Schema Riclassifica", type=["csv", "xlsx", "xls"],
                                   key=f"u_ricl_{ca}", label_visibility="collapsed")
        if u_ricl:
            df = smart_load(u_ricl)
            if df is not None:
                save_cliente({'df_ricl': df})
                st.success(f"✅ {len(df)} voci schema")
                with st.expander("Anteprima"):
                    st.dataframe(df.head(8), use_container_width=True)
            else:
                st.error("Errore lettura file")
        elif cliente.get('df_ricl') is not None:
            st.info(f"📋 {len(cliente['df_ricl'])} voci in memoria")
            with st.expander("Anteprima"):
                st.dataframe(cliente['df_ricl'].head(8), use_container_width=True)

    st.markdown("---")
    stati = {
        'Piano dei Conti': cliente.get('df_piano') is not None,
        'DB Contabile': cliente.get('df_db') is not None,
        'Schema Riclassifica': cliente.get('df_ricl') is not None,
    }
    cols = st.columns(3)
    for i, (nome, ok) in enumerate(stati.items()):
        with cols[i]:
            color, bg, emoji = ('#065F46', '#D1FAE5', '✅') if ok else ('#92400E', '#FEF3C7', '⏳')
            st.markdown(
                f"<div style='text-align:center; padding:10px; background:{bg}; border-radius:8px; color:{color}; font-weight:500; font-size:0.85rem;'>{emoji} {nome}</div>",
                unsafe_allow_html=True
            )


def _render_mappatura(ca, cliente):
    st.markdown("### Mappatura Conti → Schema Riclassifica")

    df_piano = cliente.get('df_piano')
    df_ricl = cliente.get('df_ricl')
    mapping = cliente.get('mapping', {})

    if df_piano is None or df_ricl is None:
        st.warning("⚠️ Carica prima il Piano dei Conti e lo Schema di Riclassifica (Tab 1)")
        return

    col_cod_piano = find_column(df_piano, ['Codice', 'codice', 'codice conto', 'Codice Conto', 'CODICE', 'conto', 'Conto', 'ID'])
    col_desc_piano = find_column(df_piano, ['Descrizione', 'descrizione', 'conto', 'Conto', 'Nome', 'nome'])
    col_cod_ricl = find_column(df_ricl, ['Codice', 'codice', 'Voce', 'voce', 'ID', 'id'])
    col_desc_ricl = find_column(df_ricl, ['Descrizione', 'descrizione', 'voce', 'Voce', 'Nome', 'nome'])

    if not col_cod_piano:
        st.error("Colonna 'Codice' non trovata nel piano dei conti.")
        return
    if not col_cod_ricl:
        st.error("Colonna 'Codice' non trovata nello schema di riclassifica.")
        return

    voci_ricl = df_ricl[col_cod_ricl].astype(str).tolist()
    if col_desc_ricl:
        voci_ricl_label = {
            str(r[col_cod_ricl]): f"{r[col_cod_ricl]} — {r[col_desc_ricl]}"
            for _, r in df_ricl.iterrows()
        }
    else:
        voci_ricl_label = {v: v for v in voci_ricl}

    # Stats
    n_mappati = len([v for v in mapping.values() if v])
    n_totale = len(df_piano)
    n_nuovi = n_totale - n_mappati
    pct = round(n_mappati / n_totale * 100) if n_totale > 0 else 0

    st.markdown(f"""
    <div style='display:flex; gap:16px; margin-bottom:1rem;'>
        <div class='metric-card' style='flex:1'><div class='label'>Totale Conti</div><div class='value'>{n_totale}</div></div>
        <div class='metric-card' style='flex:1; border-left-color:#059669'><div class='label'>Mappati</div><div class='value' style='color:#059669'>{n_mappati} <span style='font-size:0.9rem'>({pct}%)</span></div></div>
        <div class='metric-card' style='flex:1; border-left-color:#D97706'><div class='label'>Da mappare</div><div class='value' style='color:#D97706'>{n_nuovi}</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 🤖 Mappatura Automatica con AI")
    col_ai1, col_ai2 = st.columns(2)

    with col_ai1:
        if st.button("🤖 Mappa TUTTI i conti (AI)", use_container_width=True):
            _esegui_mapping_ai(df_piano, df_ricl, mapping, full=True)

    with col_ai2:
        if st.button("✨ Mappa solo i NUOVI (AI)", use_container_width=True, disabled=(n_nuovi == 0)):
            _esegui_mapping_ai(df_piano, df_ricl, mapping, full=False)

    st.markdown("---")
    st.markdown("#### ✏️ Revisione e Correzione Manuale")

    filtro = st.radio("Mostra:", ["Tutti", "Solo non mappati", "Solo mappati"],
                       horizontal=True, key="filtro_map_main")

    conti_df = df_piano.copy()
    if filtro == "Solo non mappati":
        conti_df = conti_df[~conti_df[col_cod_piano].astype(str).isin([k for k, v in mapping.items() if v])]
    elif filtro == "Solo mappati":
        conti_df = conti_df[conti_df[col_cod_piano].astype(str).isin([k for k, v in mapping.items() if v])]

    if len(conti_df) > 60:
        st.info(f"Mostro 60/{len(conti_df)} conti. Usa i filtri per restringere.")
        conti_df = conti_df.head(60)

    voci_options = ['— Non mappato —'] + list(voci_ricl_label.values())

    for _, row in conti_df.iterrows():
        codice = str(row[col_cod_piano])
        desc = str(row.get(col_desc_piano, '')) if col_desc_piano else ''
        voce_cod = mapping.get(codice)
        label_att = voci_ricl_label.get(voce_cod, '— Non mappato —')
        idx = voci_options.index(label_att) if label_att in voci_options else 0

        col_a, col_b = st.columns([2, 3])
        with col_a:
            mapped_dot = "🟢" if voce_cod else "🔴"
            st.markdown(f"<div style='padding:9px 4px; font-size:0.83rem;'>{mapped_dot} <b>{codice}</b> &nbsp; {desc}</div>",
                        unsafe_allow_html=True)
        with col_b:
            sel = st.selectbox("x", voci_options, index=idx,
                               label_visibility="collapsed", key=f"mmap_{ca}_{codice}")
            if sel == '— Non mappato —':
                mapping.pop(codice, None)
            else:
                for k, v in voci_ricl_label.items():
                    if v == sel:
                        mapping[codice] = k
                        break

    save_cliente({'mapping': mapping})

    st.markdown("---")
    colb1, colb2 = st.columns([1, 4])
    with colb1:
        if st.button("💾 Salva Mappatura", type="primary"):
            save_cliente({'mapping': mapping})
            st.success(f"✅ Mappatura aggiornata — {len([v for v in mapping.values() if v])} conti mappati")
