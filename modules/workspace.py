"""workspace.py — Caricamento dati, mappatura conti, import mappatura CSV."""
import streamlit as st
import pandas as pd
import io
from services.data_utils import smart_load, find_column, get_cliente, save_cliente, get_api_key
from services.riclassifica import get_label_map


def render_workspace():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("Seleziona o crea un cliente dalla sidebar."); return

    cliente = get_cliente()
    _header(ca)

    tab1, tab2, tab3 = st.tabs(["📂 Caricamento File", "🔗 Mappatura Conti", "🔑 API Key"])
    with tab1: _render_caricamento(ca, cliente)
    with tab2: _render_mappatura(ca, cliente)
    with tab3: _render_api_tab()


def _header(ca):
    st.markdown(f"""
    <div style='margin-bottom:20px;padding:20px 24px;background:#1A2744;border-radius:12px;
                border:1px solid rgba(201,168,76,0.2)'>
        <div style='font-size:10px;text-transform:uppercase;letter-spacing:2px;
                    color:#C9A84C;font-weight:700;margin-bottom:4px'>Workspace</div>
        <div style='font-size:1.4rem;font-weight:700;color:#F1F5F9'>🗂️ {ca}</div>
        <div style='font-size:0.82rem;color:#94A3B8'>Gestione dati contabili e configurazione mappatura</div>
    </div>""", unsafe_allow_html=True)


def _card_status(label, ok, detail=""):
    color = '#10B981' if ok else '#F59E0B'
    bg    = 'rgba(16,185,129,0.1)' if ok else 'rgba(245,158,11,0.1)'
    em    = '✅' if ok else '⏳'
    det_html = f"<div style='color:#94A3B8;font-size:0.75rem;margin-top:3px'>{detail}</div>" if detail else ''
    st.markdown(
        f"<div style='background:{bg};border:1px solid {color}44;border-radius:10px;"
        f"padding:12px 16px;text-align:center'>"
        f"<div style='color:{color};font-weight:700;font-size:0.88rem'>{em} {label}</div>"
        f"{det_html}</div>", unsafe_allow_html=True)


# ── CARICAMENTO ───────────────────────────────────────────────────────────────
def _render_caricamento(ca, cliente):
    st.markdown("""
    <div style='background:rgba(30,58,110,0.3);border:1px solid rgba(59,130,246,0.2);
                border-radius:10px;padding:14px 18px;font-size:0.84rem;color:#94A3B8;margin-bottom:20px'>
    Carica i tre file richiesti. Formati: <b style='color:#E2E8F0'>CSV</b> (sep. ; o ,) e
    <b style='color:#E2E8F0'>Excel (.xlsx)</b>.
    Encoding italiano (latin1/utf-8) gestito automaticamente.
    </div>""", unsafe_allow_html=True)

    def upload_block(col, num, label, hint, field):
        with col:
            st.markdown(f"<div style='font-size:0.78rem;font-weight:600;color:#C9A84C;margin-bottom:8px'>{num}. {label}</div>", unsafe_allow_html=True)
            st.caption(hint)
            f = st.file_uploader(label, type=["csv","xlsx","xls"],
                                  key=f"u_{field}_{ca}", label_visibility="collapsed")
            if f:
                df = smart_load(f)
                if df is not None and not df.empty:
                    save_cliente({field: df})
                    st.success(f"✅ {len(df)} righe")
                    with st.expander("Anteprima"):
                        st.caption(f"Colonne: {list(df.columns)}")
                        st.dataframe(df.head(6), use_container_width=True)
                else:
                    st.error("Errore lettura — verifica formato e separatore")
            elif cliente.get(field) is not None:
                df_cur = cliente[field]
                st.markdown(f"<div style='font-size:0.78rem;color:#10B981;padding:6px 0'>📋 {len(df_cur)} righe in memoria</div>", unsafe_allow_html=True)
                with st.expander("Anteprima"):
                    st.caption(f"Colonne: {list(df_cur.columns)}")
                    st.dataframe(df_cur.head(6), use_container_width=True)

    c1, c2, c3 = st.columns(3)
    upload_block(c1, "1", "Piano dei Conti",    "Atteso: Codice, Descrizione",     "df_piano")
    upload_block(c2, "2", "DB Contabile",        "Atteso: Data, Conto, Saldo",       "df_db")
    upload_block(c3, "3", "Schema Riclassifica", "Atteso: Codice, Descrizione voce", "df_ricl")

    st.markdown("---")
    stati = [
        ("Piano dei Conti", 'df_piano', lambda c: f"{len(c.get('df_piano', pd.DataFrame()))} conti"),
        ("DB Contabile",    'df_db',    lambda c: f"{len(c.get('df_db',    pd.DataFrame()))} righe"),
        ("Schema Ricl.",    'df_ricl',  lambda c: f"{len(c.get('df_ricl',  pd.DataFrame()))} voci"),
    ]
    cols = st.columns(3)
    for i, (nome, field, det_fn) in enumerate(stati):
        ok = cliente.get(field) is not None and not cliente[field].empty
        with cols[i]:
            _card_status(nome, ok, det_fn(cliente) if ok else "Non caricato")


# ── MAPPATURA ─────────────────────────────────────────────────────────────────
def _render_mappatura(ca, cliente):
    st.markdown("""
    <div style='font-size:1.1rem;font-weight:700;color:#F1F5F9;margin-bottom:4px'>
        🔗 Mappatura Conti → Schema Riclassifica
    </div>
    <div style='font-size:0.82rem;color:#94A3B8;margin-bottom:20px'>
        Associa ogni conto alla voce del CE riclassificato.
        Le <b style='color:#C9A84C'>descrizioni</b> sono mostrate al posto dei codici tecnici.
    </div>""", unsafe_allow_html=True)

    df_piano = cliente.get('df_piano')
    df_ricl  = cliente.get('df_ricl')
    mapping  = cliente.get('mapping', {})

    if df_piano is None or df_ricl is None:
        st.warning("⚠️ Carica prima Piano dei Conti e Schema Riclassifica (Tab 1).")
        return

    col_cod_piano  = find_column(df_piano, ['Codice','codice','CodConto','Conto','conto','ID','cod'])
    col_desc_piano = find_column(df_piano, ['Descrizione','descrizione','Nome','nome','Conto','conto'])
    col_cod_ricl   = find_column(df_ricl,  ['Codice','codice','ID','id','Voce','voce'])
    col_desc_ricl  = find_column(df_ricl,  ['Descrizione','descrizione','Nome','nome','Voce','voce'])

    if not col_cod_piano:
        st.error(f"Colonna Codice non trovata nel piano. Colonne: {list(df_piano.columns)[:8]}")
        return
    if not col_cod_ricl:
        st.error(f"Colonna Codice non trovata nello schema. Colonne: {list(df_ricl.columns)[:8]}")
        return

    label_map = get_label_map(df_ricl)

    voci_options = ['— Non mappato —']
    desc_to_cod  = {}
    for _, row in df_ricl.iterrows():
        cod  = str(row[col_cod_ricl]).strip()
        desc = str(row[col_desc_ricl]).strip() if col_desc_ricl and col_desc_ricl != col_cod_ricl else cod
        if desc.lower() in ('nan','none','') or cod.lower() in ('nan','none',''):
            continue
        voci_options.append(desc)
        desc_to_cod[desc] = cod

    n_tot     = len(df_piano)
    n_mappati = len([v for v in mapping.values() if v])
    pct       = n_mappati / n_tot * 100 if n_tot > 0 else 0

    # Stats cards
    for col, lbl, val, clr in zip(
        st.columns(4),
        ['Totale', 'Mappati', 'Da mappare', 'Completamento'],
        [n_tot, n_mappati, n_tot - n_mappati, f"{pct:.0f}%"],
        ['#F1F5F9', '#10B981', '#F59E0B', '#C9A84C']
    ):
        col.markdown(
            f"<div style='background:#111827;border-radius:10px;padding:14px;text-align:center'>"
            f"<div style='font-size:0.68rem;color:#64748B;text-transform:uppercase;letter-spacing:1px'>{lbl}</div>"
            f"<div style='font-size:1.4rem;font-weight:700;color:{clr}'>{val}</div></div>",
            unsafe_allow_html=True)

    st.progress(pct / 100)

    # ── SEZIONE IMPORT/EXPORT MAPPATURA ──────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📥 Import / Export Mappatura")

    col_imp, col_exp = st.columns(2)

    with col_imp:
        st.markdown("<div style='font-size:0.84rem;color:#E2E8F0;font-weight:600;margin-bottom:8px'>📤 Importa mappatura da CSV/Excel</div>", unsafe_allow_html=True)
        st.caption("Il file deve avere colonne: **Codice** (conto), **VoceCodice** (codice voce riclassifica)")
        f_import = st.file_uploader("Importa mappatura", type=["csv","xlsx","xls"],
                                     key=f"import_map_{ca}", label_visibility="collapsed")
        if f_import:
            df_imp = smart_load(f_import)
            if df_imp is not None and not df_imp.empty:
                col_conto_imp  = find_column(df_imp, ['Codice','codice','CodConto','conto','Conto'])
                col_voce_imp   = find_column(df_imp, ['VoceCodice','voce_codice','CodiceVoce','Voce','voce','Mapping','mapping'])
                if col_conto_imp and col_voce_imp:
                    nuovi = 0
                    for _, row in df_imp.iterrows():
                        conto = str(row[col_conto_imp]).strip()
                        voce  = str(row[col_voce_imp]).strip()
                        if conto and voce and voce.lower() not in ('nan','none',''):
                            mapping[conto] = voce
                            nuovi += 1
                    save_cliente({'mapping': mapping})
                    st.success(f"✅ Importati {nuovi} mapping. Ricarica la pagina.")
                    st.rerun()
                else:
                    st.error(f"Colonne non trovate. Trovate: {list(df_imp.columns)}")
            else:
                st.error("File non leggibile.")

    with col_exp:
        st.markdown("<div style='font-size:0.84rem;color:#E2E8F0;font-weight:600;margin-bottom:8px'>📥 Esporta mappatura attuale</div>", unsafe_allow_html=True)
        st.caption("Esporta la mappatura corrente come CSV per modificarla offline")
        if mapping:
            rows_exp = []
            for conto, voce_cod in mapping.items():
                # Descrizione conto
                if col_desc_piano and col_desc_piano != col_cod_piano:
                    match = df_piano[df_piano[col_cod_piano].astype(str) == conto]
                    desc_conto = str(match.iloc[0][col_desc_piano]) if not match.empty else ''
                else:
                    desc_conto = ''
                desc_voce = label_map.get(str(voce_cod), str(voce_cod))
                rows_exp.append({'Codice': conto, 'DescrizioneConto': desc_conto,
                                  'VoceCodice': voce_cod, 'DescrizioneVoce': desc_voce})
            df_exp = pd.DataFrame(rows_exp)
            csv_exp = df_exp.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button("⬇️ Scarica Mappatura CSV", data=csv_exp,
                               file_name=f"mappatura_{ca}.csv", mime="text/csv",
                               use_container_width=True)
            # Template vuoto
            template_rows = []
            for _, row in df_piano.iterrows():
                conto = str(row[col_cod_piano]).strip()
                desc  = str(row[col_desc_piano]).strip() if col_desc_piano and col_desc_piano != col_cod_piano else ''
                template_rows.append({'Codice': conto, 'DescrizioneConto': desc, 'VoceCodice': '', 'DescrizioneVoce': ''})
            df_tpl = pd.DataFrame(template_rows)
            csv_tpl = df_tpl.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button("📋 Template vuoto (tutti i conti)", data=csv_tpl,
                               file_name=f"template_mappatura_{ca}.csv", mime="text/csv",
                               use_container_width=True)
        else:
            st.info("Nessuna mappatura da esportare.")
            if df_piano is not None:
                template_rows = []
                for _, row in df_piano.iterrows():
                    conto = str(row[col_cod_piano]).strip()
                    desc  = str(row[col_desc_piano]).strip() if col_desc_piano and col_desc_piano != col_cod_piano else ''
                    template_rows.append({'Codice': conto, 'DescrizioneConto': desc, 'VoceCodice': '', 'DescrizioneVoce': ''})
                df_tpl = pd.DataFrame(template_rows)
                csv_tpl = df_tpl.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
                st.download_button("📋 Scarica template per compilare offline", data=csv_tpl,
                                   file_name=f"template_mappatura_{ca}.csv", mime="text/csv",
                                   use_container_width=True)

    # ── AI MAPPING ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🤖 Mappatura Automatica con AI")

    col_ai1, col_ai2 = st.columns(2)
    with col_ai1:
        if st.button("🤖 Mappa TUTTI i conti con AI", use_container_width=True,
                      help="Claude analizza ogni conto e lo associa alla voce più appropriata"):
            _run_ai_mapping(df_piano, df_ricl, mapping, full=True)
    with col_ai2:
        n_nuovi = n_tot - n_mappati
        if st.button(f"✨ Mappa solo i {n_nuovi} nuovi (AI)", use_container_width=True,
                      disabled=(n_nuovi == 0)):
            _run_ai_mapping(df_piano, df_ricl, mapping, full=False)

    # ── REVISIONE MANUALE ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ✏️ Revisione Manuale")
    st.markdown("<div style='font-size:0.78rem;color:#94A3B8;margin-bottom:12px'>🟢 = mappato &nbsp;·&nbsp; 🔴 = non mappato</div>", unsafe_allow_html=True)

    col_f1, col_f2 = st.columns([2, 3])
    with col_f1:
        filtro = st.radio("Mostra:", ["Tutti", "Non mappati", "Mappati"],
                           horizontal=True, key="filt_map")
    with col_f2:
        cerca_conto = st.text_input("Cerca conto:", placeholder="codice o descrizione…",
                                     key="cerca_conto_input", label_visibility="collapsed")

    conti_df = df_piano.copy()
    mappati_set = {k for k, v in mapping.items() if v}
    if filtro == "Non mappati":
        conti_df = conti_df[~conti_df[col_cod_piano].astype(str).isin(mappati_set)]
    elif filtro == "Mappati":
        conti_df = conti_df[conti_df[col_cod_piano].astype(str).isin(mappati_set)]
    if cerca_conto:
        q = cerca_conto.lower()
        mask = conti_df[col_cod_piano].astype(str).str.lower().str.contains(q)
        if col_desc_piano and col_desc_piano != col_cod_piano:
            mask = mask | conti_df[col_desc_piano].astype(str).str.lower().str.contains(q)
        conti_df = conti_df[mask]

    if len(conti_df) > 80:
        st.info(f"Mostro 80/{len(conti_df)} conti. Usa cerca/filtro per restringere.")
        conti_df = conti_df.head(80)

    for _, row in conti_df.iterrows():
        codice = str(row[col_cod_piano]).strip()
        desc   = str(row.get(col_desc_piano, '')).strip() if col_desc_piano and col_desc_piano != col_cod_piano else ''

        cod_att = mapping.get(codice)
        if cod_att:
            desc_att = label_map.get(str(cod_att), str(cod_att))
            idx = voci_options.index(desc_att) if desc_att in voci_options else 0
        else:
            idx = 0

        dot = "🟢" if cod_att else "🔴"
        col_a, col_b = st.columns([2, 3])
        with col_a:
            trunc = desc[:35] + ('…' if len(desc) > 35 else '') if desc else ''
            desc_html = f" <span style='color:#64748B'>— {trunc}</span>" if trunc else ''
            st.markdown(
                f"<div style='padding:9px 4px;font-size:0.82rem'>"
                f"{dot} <b style='color:#E2E8F0'>{codice}</b>{desc_html}"
                f"</div>", unsafe_allow_html=True)
        with col_b:
            sel = st.selectbox("_", voci_options, index=idx,
                               label_visibility="collapsed",
                               key=f"mmap_{ca}_{codice}")
            if sel == '— Non mappato —':
                mapping.pop(codice, None)
            else:
                mapping[codice] = desc_to_cod.get(sel, sel)

    save_cliente({'mapping': mapping})
    st.markdown("---")
    if st.button("💾 Salva Mappatura", type="primary"):
        save_cliente({'mapping': mapping})
        st.success(f"✅ Mappatura salvata — {len([v for v in mapping.values() if v])} conti mappati")


# ── API TAB ───────────────────────────────────────────────────────────────────
def _render_api_tab():
    st.markdown("### 🔑 API Key Anthropic")
    st.markdown("""
    <div style='background:rgba(245,158,11,0.08);border-left:3px solid #F59E0B;
                border-radius:0 10px 10px 0;padding:14px 18px;font-size:0.83rem;
                color:#94A3B8;margin-bottom:20px'>
    La chiave API è necessaria per la <b style='color:#E2E8F0'>mappatura automatica AI</b>
    e per il <b style='color:#E2E8F0'>CFO Agent</b>.<br>
    Ottienila su <a href='https://console.anthropic.com' target='_blank'
    style='color:#C9A84C'>console.anthropic.com</a>
    </div>""", unsafe_allow_html=True)

    current = st.session_state.get('anthropic_api_key', '')
    if not current:
        try:
            current = st.secrets.get('ANTHROPIC_API_KEY', '')
            if current:
                st.session_state['anthropic_api_key'] = current
        except Exception:
            pass

    if current:
        masked = current[:12] + '•' * 16 + current[-4:]
        st.markdown(f"<div style='color:#10B981;font-size:0.85rem;margin-bottom:12px'>✅ API Key attiva: <code style='color:#10B981'>{masked}</code></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#EF4444;font-size:0.85rem;margin-bottom:12px'>🔴 Nessuna API Key configurata</div>", unsafe_allow_html=True)

    new_key = st.text_input("Inserisci API Key:", type="password",
                             placeholder="sk-ant-api03-…", key="ws_api_key_input")
    if st.button("Salva API Key", type="primary") and new_key.strip():
        st.session_state['anthropic_api_key'] = new_key.strip()
        st.success("✅ Salvata per questa sessione")
        st.rerun()

    with st.expander("ℹ️ Come configurare in produzione"):
        st.code('# .streamlit/secrets.toml\nANTHROPIC_API_KEY = "sk-ant-api03-..."', language="toml")
        st.caption("Questo file NON deve essere committato su GitHub.")


# ── AI MAPPING HELPER ─────────────────────────────────────────────────────────
def _run_ai_mapping(df_piano, df_ricl, mapping_corrente, full=True):
    api_key = get_api_key()
    if not api_key:
        st.error("Configura la API Key nel tab '🔑 API Key'.")
        return

    with st.spinner("🤖 Claude in elaborazione… potrebbe richiedere 30-60 secondi"):
        try:
            from services.ai_mapper import ai_suggest_mapping, ai_suggest_new_accounts
            if full:
                nuovo = ai_suggest_mapping(df_piano, df_ricl, mapping_corrente)
            else:
                nuovo = ai_suggest_new_accounts(df_piano, df_ricl, mapping_corrente)
            mapping_corrente.update(nuovo)
            save_cliente({'mapping': mapping_corrente})
            n = len([v for v in nuovo.values() if v])
            st.success(f"✅ AI ha mappato {n} conti su {len(nuovo)} analizzati")
            st.rerun()
        except Exception as e:
            err = str(e)
            if '401' in err or 'invalid x-api-key' in err.lower():
                st.error("🔑 API Key non valida. Verifica su console.anthropic.com")
            else:
                st.error(f"Errore: {err}")
