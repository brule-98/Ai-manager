"""workspace.py — Caricamento file, mappatura conti, import/export."""
import streamlit as st
import pandas as pd
from services.data_utils import (
    smart_load, find_column, get_cliente, save_cliente,
    get_mapping, set_mapping, get_api_key
)
from services.riclassifica import get_label_map


def render_workspace():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("Seleziona un cliente dalla sidebar per iniziare.")
        return

    cliente = get_cliente()
    if cliente is None:
        st.error("Errore: cliente non trovato in sessione.")
        return

    st.markdown("""
<div style='background:linear-gradient(135deg,#0D1625,#0F2044);
            border:1px solid rgba(201,168,76,0.15);border-radius:14px;
            padding:22px 28px;margin-bottom:24px'>
    <div style='font-size:9px;text-transform:uppercase;letter-spacing:4px;color:#C9A84C;font-weight:700;margin-bottom:4px'>Workspace</div>
    <div style='font-size:1.35rem;font-weight:800;color:#F1F5F9'>🗂️ """ + ca + """</div>
    <div style='font-size:0.78rem;color:#475569;margin-top:3px'>Caricamento file · Mappatura conti · Import/Export</div>
</div>""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📂 File", "🔗 Mappatura", "🔑 API Key"])
    with tab1:
        _tab_file(ca, cliente)
    with tab2:
        _tab_mappatura(ca, cliente)
    with tab3:
        _tab_api()


# ── TAB FILE ──────────────────────────────────────────────────────────────────
def _tab_file(ca, cliente):
    st.markdown("""<div style='font-size:0.8rem;color:#64748B;margin-bottom:20px;
        padding:10px 14px;background:rgba(255,255,255,0.03);border-radius:8px;
        border-left:3px solid rgba(201,168,76,0.4)'>
        Carica i tre file richiesti. Formati supportati: <b style='color:#CBD5E1'>CSV</b>
        (sep. ; o ,) e <b style='color:#CBD5E1'>Excel (.xlsx)</b>.
        Encoding italiano (latin1/utf-8) gestito automaticamente.
    </div>""", unsafe_allow_html=True)

    def upload_block(col, label, field, hint):
        with col:
            has = cliente.get(field) is not None
            bord = 'rgba(16,185,129,0.35)' if has else 'rgba(255,255,255,0.07)'
            st.markdown(
                "<div style='border:1px solid " + bord + ";border-radius:10px;"
                "padding:14px 16px;margin-bottom:8px;background:rgba(255,255,255,0.02)'>"
                "<div style='font-size:0.7rem;font-weight:700;color:#C9A84C;"
                "text-transform:uppercase;letter-spacing:1px;margin-bottom:6px'>" + label + "</div>"
                "<div style='font-size:0.73rem;color:#334155;margin-bottom:8px'>" + hint + "</div>"
                "</div>",
                unsafe_allow_html=True
            )
            f = st.file_uploader(label, type=["csv","xlsx","xls","xlsm"],
                                  key="up_" + field + "_" + ca,
                                  label_visibility="collapsed")
            if f is not None:
                df = smart_load(f)
                if df is not None and not df.empty:
                    save_cliente({field: df})
                    st.success("✅ {} righe caricate — colonne: {}".format(
                        len(df), list(df.columns)[:6]))
                    with st.expander("Anteprima"):
                        st.dataframe(df.head(5), use_container_width=True)
                else:
                    st.error("⚠️ File non leggibile. Verifica formato, separatore e encoding.")
            elif has:
                df_cur = cliente[field]
                st.markdown(
                    "<div style='font-size:0.76rem;color:#10B981;padding:4px 2px'>"
                    "✅ {} righe in memoria</div>".format(len(df_cur)),
                    unsafe_allow_html=True
                )

    c1, c2, c3 = st.columns(3)
    upload_block(c1, "1. Piano dei Conti",     "df_piano", "Colonne: Codice, Descrizione")
    upload_block(c2, "2. DB Contabile",         "df_db",    "Colonne: Data, CodConto, Importo")
    upload_block(c3, "3. Schema Riclassifica",  "df_ricl",  "Colonne: Codice, Descrizione")

    # Stato caricamento
    st.markdown("---")
    cols = st.columns(3)
    for i, (nome, field) in enumerate([("Piano Conti","df_piano"),("DB Contabile","df_db"),("Schema Ricl.","df_ricl")]):
        ok = cliente.get(field) is not None and not cliente[field].empty
        n  = len(cliente[field]) if ok else 0
        clr = '#10B981' if ok else '#EF4444'
        sym = '✓' if ok else '○'
        cols[i].markdown(
            "<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);"
            "border-radius:10px;padding:14px;text-align:center'>"
            "<div style='font-size:0.65rem;text-transform:uppercase;letter-spacing:1px;color:#475569;margin-bottom:4px'>" + nome + "</div>"
            "<div style='font-size:1.4rem;font-weight:800;color:" + clr + "'>" + sym + "</div>"
            "<div style='font-size:0.72rem;color:#475569'>" + (str(n) + " righe" if ok else "Non caricato") + "</div>"
            "</div>",
            unsafe_allow_html=True
        )


# ── TAB MAPPATURA ─────────────────────────────────────────────────────────────
def _tab_mappatura(ca, cliente):
    df_piano = cliente.get('df_piano')
    df_ricl  = cliente.get('df_ricl')

    if df_piano is None or df_ricl is None:
        st.warning("⚠️ Carica prima **Piano dei Conti** e **Schema Riclassifica** nel tab File.")
        return

    col_cod_piano  = find_column(df_piano, ['Codice','codice','CodConto','Conto','conto','ID','cod'])
    col_desc_piano = find_column(df_piano, ['Descrizione','descrizione','Nome','nome'])
    col_cod_ricl   = find_column(df_ricl,  ['Codice','codice','ID','id','Voce','voce'])
    col_desc_ricl  = find_column(df_ricl,  ['Descrizione','descrizione','Nome','nome','Voce','voce'])

    if not col_cod_piano:
        st.error("Colonna Codice non trovata nel Piano. Colonne: {}".format(list(df_piano.columns)[:8]))
        return
    if not col_cod_ricl:
        st.error("Colonna Codice non trovata nello Schema. Colonne: {}".format(list(df_ricl.columns)[:8]))
        return

    label_map = get_label_map(df_ricl)

    # Opzioni dropdown voci riclassifica
    voci_options = ['— Non mappato —']
    desc_to_cod  = {}
    for _, row in df_ricl.iterrows():
        cod  = str(row[col_cod_ricl]).strip()
        desc = str(row[col_desc_ricl]).strip() if (col_desc_ricl and col_desc_ricl != col_cod_ricl) else cod
        if desc.lower() in ('nan','none','') or cod.lower() in ('nan','none',''):
            continue
        voci_options.append(desc)
        desc_to_cod[desc] = cod

    # Legge mapping DIRETTAMENTE da session_state
    mapping = get_mapping()

    n_tot     = len(df_piano)
    n_mappati = len([v for v in mapping.values() if v])
    pct       = (n_mappati / n_tot) if n_tot > 0 else 0.0

    # KPI cards
    cols4 = st.columns(4)
    for col, lbl, val, clr in [
        (cols4[0], "Totale",       str(n_tot),              '#F1F5F9'),
        (cols4[1], "Mappati",      str(n_mappati),          '#10B981'),
        (cols4[2], "Da mappare",   str(n_tot - n_mappati),  '#F59E0B'),
        (cols4[3], "Completamento","{:.0f}%".format(pct*100),'#C9A84C'),
    ]:
        col.markdown(
            "<div style='background:#0D1625;border:1px solid rgba(255,255,255,0.07);border-radius:10px;"
            "padding:14px;text-align:center'>"
            "<div style='font-size:0.63rem;text-transform:uppercase;letter-spacing:1.2px;color:#475569;margin-bottom:6px'>" + lbl + "</div>"
            "<div style='font-size:1.5rem;font-weight:800;color:" + clr + ";font-variant-numeric:tabular-nums'>" + val + "</div>"
            "</div>",
            unsafe_allow_html=True
        )
    st.progress(float(max(0.0, min(1.0, pct))))

    # ── IMPORT / EXPORT ────────────────────────────────────────────────────
    with st.expander("📥 Import / Export Mappatura", expanded=(n_mappati == 0)):
        c_imp, c_exp = st.columns(2)

        with c_imp:
            st.markdown("**Importa da CSV/Excel**")
            st.caption("Colonne richieste: `Codice` (conto) e `VoceCodice` (codice schema)")
            f_imp = st.file_uploader("Importa", type=["csv","xlsx","xls"],
                                      key="imp_map_" + ca, label_visibility="collapsed")
            if f_imp is not None:
                df_imp = smart_load(f_imp)
                if df_imp is not None and not df_imp.empty:
                    col_c = find_column(df_imp, ['Codice','codice','CodConto','conto'])
                    col_v = find_column(df_imp, ['VoceCodice','voce_codice','CodiceVoce','Voce','Mapping','mapping'])
                    if col_c and col_v:
                        m = dict(mapping)
                        nuovi = 0
                        for _, row in df_imp.iterrows():
                            conto = str(row[col_c]).strip()
                            voce  = str(row[col_v]).strip()
                            if conto and voce and voce.lower() not in ('nan','none',''):
                                m[conto] = voce
                                nuovi += 1
                        set_mapping(m)
                        st.success("✅ {} mapping importati. Ricarica la pagina.".format(nuovi))
                        st.rerun()
                    else:
                        st.error("Colonne non trovate. Presenti: {}".format(list(df_imp.columns)))
                else:
                    st.error("File non leggibile.")

        with c_exp:
            st.markdown("**Export / Template**")
            rows_e = []
            for _, row in df_piano.iterrows():
                conto = str(row[col_cod_piano]).strip()
                desc  = str(row[col_desc_piano]).strip() if col_desc_piano else ''
                voce_cod  = mapping.get(conto, '')
                voce_desc = label_map.get(voce_cod, '') if voce_cod else ''
                rows_e.append({'Codice': conto, 'DescrizioneConto': desc,
                                'VoceCodice': voce_cod, 'DescrizioneVoce': voce_desc})
            df_exp = pd.DataFrame(rows_e)
            csv_exp = df_exp.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button(
                "⬇️ Scarica mappatura (template + attuale)",
                data=csv_exp,
                file_name="mappatura_" + ca + ".csv",
                mime="text/csv",
                use_container_width=True
            )
            st.caption("Il file mostra la mappatura attuale. Compila VoceCodice e re-importa.")

    # ── AI MAPPING ────────────────────────────────────────────────────────
    st.markdown("---")
    c_ai1, c_ai2 = st.columns(2)
    with c_ai1:
        if st.button("🤖 Mappa tutti con AI", use_container_width=True, key="ai_map_all"):
            _run_ai_mapping(df_piano, df_ricl, full=True)
    with c_ai2:
        n_vuoti = n_tot - n_mappati
        if st.button("✨ Mappa {} non mappati (AI)".format(n_vuoti),
                      use_container_width=True, key="ai_map_new", disabled=(n_vuoti == 0)):
            _run_ai_mapping(df_piano, df_ricl, full=False)

    # ── REVISIONE MANUALE ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("<div style='font-size:0.72rem;font-weight:700;color:#C9A84C;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px'>✏️ Revisione Manuale</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 2, 3])
    with c1:
        filtro = st.radio("", ["Tutti","Non mappati","Mappati"],
                           horizontal=True, key="filt_map", label_visibility="collapsed")
    with c2:
        cerca = st.text_input("", placeholder="🔍 Cerca conto…",
                               key="cerca_conto", label_visibility="collapsed")

    # Filtra
    conti_df = df_piano.copy()
    m_set = {k for k, v in mapping.items() if v}
    if filtro == "Non mappati":
        conti_df = conti_df[~conti_df[col_cod_piano].astype(str).isin(m_set)]
    elif filtro == "Mappati":
        conti_df = conti_df[conti_df[col_cod_piano].astype(str).isin(m_set)]
    if cerca:
        q = cerca.lower()
        mask = conti_df[col_cod_piano].astype(str).str.lower().str.contains(q, na=False)
        if col_desc_piano:
            mask = mask | conti_df[col_desc_piano].astype(str).str.lower().str.contains(q, na=False)
        conti_df = conti_df[mask]

    if len(conti_df) > 100:
        st.caption("Mostro 100/{} conti. Usa il filtro per restringere.".format(len(conti_df)))
        conti_df = conti_df.head(100)

    # Header
    h1, h2, h3 = st.columns([3, 1, 4])
    for col, txt in [(h1,"Conto"), (h2,""), (h3,"Voce Riclassifica")]:
        col.markdown(
            "<div style='font-size:0.67rem;font-weight:700;color:#334155;text-transform:uppercase;"
            "letter-spacing:1px;padding:4px;border-bottom:1px solid rgba(255,255,255,0.06)'>"
            + txt + "</div>",
            unsafe_allow_html=True
        )

    # CRITICO: ogni widget legge/scrive DIRETTAMENTE in session_state
    for _, row in conti_df.iterrows():
        codice = str(row[col_cod_piano]).strip()
        desc   = str(row.get(col_desc_piano, '')).strip() if col_desc_piano else ''

        # Legge mapping live da session_state
        current_mapping = get_mapping()
        cod_att  = current_mapping.get(codice)
        desc_att = label_map.get(str(cod_att), str(cod_att)) if cod_att else None
        idx      = (voci_options.index(desc_att)
                    if desc_att and desc_att in voci_options else 0)

        col_a, col_b, col_c = st.columns([3, 1, 4])
        with col_a:
            trunc = (desc[:38] + '…') if len(desc) > 38 else desc
            st.markdown(
                "<div style='padding:8px 4px;font-size:0.81rem'>"
                "<b style='color:#CBD5E1'>" + codice + "</b>"
                "<span style='color:#334155;font-size:0.76rem'> " + trunc + "</span>"
                "</div>",
                unsafe_allow_html=True
            )
        with col_b:
            dot = "🟢" if cod_att else "🔴"
            st.markdown("<div style='padding:8px 2px;text-align:center'>" + dot + "</div>",
                        unsafe_allow_html=True)
        with col_c:
            sel = st.selectbox("", voci_options, index=idx,
                               label_visibility="collapsed",
                               key="map_" + ca + "_" + codice)
            # Aggiornamento IMMEDIATO in session_state
            live = get_mapping()
            if sel == '— Non mappato —':
                live.pop(codice, None)
            else:
                live[codice] = desc_to_cod.get(sel, sel)
            set_mapping(live)

    st.markdown("---")
    if st.button("💾 Salva Mappatura", type="primary", key="save_map_btn"):
        save_cliente({'mapping': get_mapping()})
        n_ok = len([v for v in get_mapping().values() if v])
        st.success("✅ {} conti mappati salvati con successo.".format(n_ok))


# ── TAB API KEY ────────────────────────────────────────────────────────────────
def _tab_api():
    st.markdown("### 🔑 API Key Anthropic")
    st.markdown("""<div style='background:rgba(245,158,11,0.08);border-left:3px solid #F59E0B;
        border-radius:0 8px 8px 0;padding:12px 16px;font-size:0.82rem;color:#94A3B8;margin-bottom:20px'>
        Necessaria per <b style='color:#E2E8F0'>mappatura AI</b> e <b style='color:#E2E8F0'>CFO Agent</b>.
        Ottienila su <a href='https://console.anthropic.com' target='_blank' style='color:#C9A84C'>console.anthropic.com</a>
    </div>""", unsafe_allow_html=True)

    current = get_api_key()
    if current:
        masked = current[:8] + '•' * 20 + current[-4:]
        st.markdown("<div style='color:#10B981;font-size:0.84rem;margin-bottom:12px'>✅ Attiva: <code style='color:#10B981'>{}</code></div>".format(masked), unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#EF4444;font-size:0.84rem;margin-bottom:12px'>🔴 Non configurata</div>", unsafe_allow_html=True)

    new_key = st.text_input("Inserisci API Key:", type="password", placeholder="sk-ant-api03-…")
    if st.button("Salva API Key", type="primary") and new_key.strip():
        st.session_state['anthropic_api_key'] = new_key.strip()
        st.success("✅ Salvata per questa sessione")
        st.rerun()

    with st.expander("ℹ️ Configurazione permanente (Streamlit Cloud)"):
        st.code('[secrets]\nANTHROPIC_API_KEY = "sk-ant-api03-..."', language="toml")
        st.caption("Aggiungi in Settings → Secrets su Streamlit Cloud. Non committare nel repo.")


# ── AI MAPPING ────────────────────────────────────────────────────────────────
def _run_ai_mapping(df_piano, df_ricl, full=True):
    api_key = get_api_key()
    if not api_key:
        st.error("⚠️ Configura prima la API Key nel tab 🔑.")
        return
    spinner_msg = "🤖 Claude sta analizzando i conti…" if full else "✨ Claude mappa i conti non ancora mappati…"
    with st.spinner(spinner_msg):
        try:
            from services.ai_mapper import ai_suggest_mapping, ai_suggest_new_accounts
            current = get_mapping()
            if full:
                nuovo = ai_suggest_mapping(df_piano, df_ricl, current)
            else:
                nuovo = ai_suggest_new_accounts(df_piano, df_ricl, current)
            m = dict(current)
            m.update(nuovo)
            set_mapping(m)
            save_cliente({'mapping': m})
            n = len([v for v in nuovo.values() if v])
            st.success("✅ AI ha mappato {} conti su {} analizzati.".format(n, len(nuovo)))
            st.rerun()
        except Exception as e:
            err = str(e)
            if '401' in err or 'invalid' in err.lower():
                st.error("🔑 API Key non valida. Verifica su console.anthropic.com")
            elif 'overloaded' in err.lower():
                st.error("⏳ Claude è temporaneamente sovraccarico. Riprova tra un minuto.")
            else:
                st.error("Errore AI: {}".format(err[:200]))
