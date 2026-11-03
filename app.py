from pathlib import Path
import copy
import json

import pandas as pd
import pydeck as pdk
import streamlit as st

# Compatibilitat de la clau ORS:
# - local: fitxer ors_api_key.txt
# - Streamlit Community Cloud: secret ORS_API_KEY
_PROJECTE_INICIAL = Path(__file__).resolve().parent
_FITXER_CLAU_ORS = _PROJECTE_INICIAL / "ors_api_key.txt"

if not _FITXER_CLAU_ORS.exists():
    try:
        _clau_ors = str(st.secrets.get("ORS_API_KEY", "")).strip()
    except Exception:
        _clau_ors = ""

    if _clau_ors:
        _FITXER_CLAU_ORS.write_text(_clau_ors, encoding="utf-8")


from scripts.calcular_escenari_ors import calcular_temps_cap_nou_centre

st.set_page_config(page_title="Visor de mobilitat escolar", page_icon="🗺️", layout="wide")

st.markdown(
    """
    <style>
    /* Redueix l'espai superior de la pàgina */
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
    }

    /* Ajusta la barra lateral */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.2rem;
    }

    /* Alineació vertical dels selectors de la llegenda */
    div[data-testid="stCheckbox"] {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }

    /* Capa flotant de càrrega */
    .visor-loading-overlay {
        position: fixed;
        inset: 0;
        z-index: 999999;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(247, 249, 251, 0.78);
        backdrop-filter: blur(2px);
    }
    .visor-loading-card {
        min-width: 320px;
        max-width: 440px;
        padding: 24px 28px;
        border-radius: 16px;
        background: #FFFFFF;
        border: 1px solid #DDE3E8;
        box-shadow: 0 12px 35px rgba(16, 42, 67, 0.18);
        text-align: center;
        color: #102A43;
    }
    .visor-spinner {
        width: 44px;
        height: 44px;
        margin: 0 auto 14px auto;
        border: 5px solid #E5EAF0;
        border-top-color: #183B56;
        border-radius: 50%;
        animation: visor-spin 0.9s linear infinite;
    }
    @keyframes visor-spin {
        to { transform: rotate(360deg); }
    }
    .visor-progress-track {
        width: 100%;
        height: 8px;
        margin-top: 14px;
        border-radius: 999px;
        overflow: hidden;
        background: #E8EDF2;
    }
    .visor-progress-fill {
        height: 100%;
        border-radius: 999px;
        background: #183B56;
    }

    /* Millora estètica discreta del visor */
    :root {
        --tfm-navy: #102A43;
        --tfm-blue: #183B56;
        --tfm-green: #087F3F;
        --tfm-border: #DDE4EA;
        --tfm-soft: #F6F8FA;
        --tfm-muted: #687786;
    }

    .block-container {
        max-width: none;
        padding-left: 1.6rem;
        padding-right: 1.6rem;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F3F6F9 0%, #EEF2F6 100%);
        border-right: 1px solid #E0E6EC;
    }

    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E1E7EC;
        border-radius: 12px;
        padding: 0.85rem 1rem;
        box-shadow: 0 3px 12px rgba(16, 42, 67, 0.045);
    }

    div[data-testid="stMetric"] label {
        color: #5E6C79;
    }

    /* Evita el control flotant automàtic del gràfic; el visor incorpora un control propi. */
    div[data-testid="stElementToolbar"] {
        display: none !important;
    }

    /* Botó propi superposat dins del mapa, sota els controls de zoom */
    .st-key-mapa_control_superposat {
        position: relative !important;
        display: block !important;
        width: 100% !important;
        max-width: 100% !important;
        height: 0 !important;
        min-height: 0 !important;
        z-index: 50 !important;
        overflow: visible !important;
    }

    /*
    El botó rep una classe pròpia a partir de la key.
    Es col·loca a la dreta del mapa, just sota els botons de zoom.
    */
    .st-key-mapa_control_superposat .st-key-canviar_mida_mapa {
        position: absolute !important;
        top: 92px !important;
        right: 8px !important;
        left: auto !important;
        width: 34px !important;
        min-width: 34px !important;
        margin: 0 !important;
        z-index: 60 !important;
    }

    .st-key-mapa_control_superposat .st-key-canviar_mida_mapa div[data-testid="stButton"] {
        width: 34px !important;
        min-width: 34px !important;
        margin: 0 !important;
    }

    .st-key-mapa_control_superposat .st-key-canviar_mida_mapa button {
        width: 34px !important;
        min-width: 34px !important;
        height: 34px !important;
        min-height: 34px !important;
        padding: 0 !important;
        border-radius: 6px !important;
        border: 1px solid #D5DCE3 !important;
        background: rgba(255, 255, 255, 0.96) !important;
        color: #263746 !important;
        box-shadow: 0 1px 5px rgba(16, 42, 67, 0.16) !important;
        font-size: 18px !important;
        line-height: 1 !important;
    }

    .st-key-mapa_control_superposat .st-key-canviar_mida_mapa button:hover {
        background: #F4F7FA !important;
        border-color: #B9C4CE !important;
    }



    .tfm-header {
        display: grid;
        grid-template-columns: minmax(260px, 0.95fr) minmax(520px, 2.35fr);
        align-items: center;
        gap: 28px;
        padding: 19px 24px;
        margin: 0 calc(-1.6rem) 18px calc(-1.6rem);
        border-left: none;
        border-right: none;
        border-radius: 0;
        background: linear-gradient(135deg, #FFFFFF 0%, #FAFCFD 100%);
        border: 1px solid var(--tfm-border);
        border-radius: 16px;
        box-shadow: 0 7px 24px rgba(16, 42, 67, 0.07);
    }

    .tfm-logos {
        display: flex;
        align-items: center;
        gap: 17px;
        min-width: 0;
    }

    .tfm-logo-master {
        width: min(220px, 49%);
        height: auto;
        object-fit: contain;
    }

    .tfm-logo-uab {
        width: min(185px, 43%);
        height: auto;
        object-fit: contain;
    }

    .tfm-logo-separator {
        width: 1px;
        height: 76px;
        background: #D9E0E6;
        flex: 0 0 auto;
    }

    .tfm-title {
        margin: 0;
        color: var(--tfm-navy);
        font-size: clamp(2rem, 3vw, 3.1rem);
        line-height: 1.06;
        letter-spacing: -0.035em;
        font-weight: 760;
    }

    .tfm-subtitle {
        margin: 10px 0 0 0;
        color: var(--tfm-muted);
        font-size: 0.98rem;
        line-height: 1.55;
        max-width: 820px;
    }

    .tfm-note {
        padding: 14px 16px;
        background: #F2F6FA;
        border: 1px solid #DCE6EF;
        border-radius: 12px;
        color: var(--tfm-navy);
        font-size: 0.87rem;
        line-height: 1.45;
    }

    .tfm-note strong {
        display: block;
        margin-top: 6px;
        color: var(--tfm-blue);
    }

    .tfm-note-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        margin-right: 7px;
        border: 1px solid #8DA3B6;
        border-radius: 50%;
        font-weight: 700;
        color: var(--tfm-blue);
    }

    .tfm-footer {
        display: grid;
        grid-template-columns: minmax(320px, 1.45fr) minmax(160px, 0.5fr) minmax(350px, 1.15fr);
        align-items: center;
        gap: 22px;
        margin-top: 34px;
        padding: 20px 22px;
        border-top: 2px solid #16804A;
        background: #F7F9FB;
        color: var(--tfm-navy);
        border-radius: 12px 12px 0 0;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    .tfm-footer-title {
        font-weight: 700;
    }

    .tfm-footer-author {
        text-align: center;
        font-weight: 650;
    }

    .tfm-footer-sources {
        text-align: right;
    }

    @media (max-width: 1050px) {
        .tfm-header {
            grid-template-columns: 1fr;
            margin-left: -1.6rem;
            margin-right: -1.6rem;
        }

        .tfm-footer {
            grid-template-columns: 1fr;
        }

        .tfm-footer-author,
        .tfm-footer-sources {
            text-align: left;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)

PROJECTE = Path(__file__).resolve().parent
DADES_WEB = PROJECTE / "dades_web"


@st.cache_data
def carregar_fluxos():
    df = pd.read_csv(DADES_WEB / "fluxos_visor.csv", dtype={"ori_cod": str, "des_cod": str})
    df["ori_cod"] = df["ori_cod"].astype(str).str.strip().str.zfill(5)
    df["des_cod"] = df["des_cod"].astype(str).str.strip().str.zfill(5)
    return df


@st.cache_data
def carregar_autocontencio():
    df = pd.read_csv(DADES_WEB / "autocontencio_per_ambit.csv", dtype={"codi_muni": str})
    df["codi_muni"] = df["codi_muni"].astype(str).str.strip().str.zfill(5)
    return df


@st.cache_data
def carregar_caps():
    df = pd.read_csv(DADES_WEB / "caps_municipals.csv", dtype={"codi_mun_2": str})
    df["codi_mun_2"] = df["codi_mun_2"].astype(str).str.strip().str.zfill(5)
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    return df.dropna(subset=["codi_mun_2", "longitud", "latitud"])


@st.cache_data
def carregar_geojson(nom):
    with open(DADES_WEB / nom, "r", encoding="utf-8") as f:
        return json.load(f)


fluxos = carregar_fluxos()
autocontencio = carregar_autocontencio()
caps = carregar_caps()
municipis_geojson = carregar_geojson("municipis.geojson")

if "resultat_escenari" not in st.session_state:
    st.session_state.resultat_escenari = None
if "configuracio_escenari" not in st.session_state:
    st.session_state.configuracio_escenari = None

if "mapa_ampliat" not in st.session_state:
    st.session_state.mapa_ampliat = False


CLASSES_FLUX = ["1–5", "5–10", "10–25", "25–50", ">50"]
CLASSES_TEMPS = ["0-15 min", "15-30 min", "30-45 min", "45-60 min", ">60 min"]
CLASSES_AUTO = ["0–20 %", "20–40 %", "40–60 %", "60–80 %", "80–100 %", "Sense alumnat resident registrat en aquest àmbit",
    "Sense dades"]
CLASSES_ESCENARI = ["1–5", "5–10", "10–25", "25–50", ">50"]

COLORS_FLUX = {
    "1–5": "#D6E4F0",
    "5–10": "#AFCBE0",
    "10–25": "#7FA8C9",
    "25–50": "#4C78A8",
    ">50": "#234F78",
}

COLORS_TEMPS = {
    "0-15 min": "#E6E1EF",
    "15-30 min": "#C7B9D9",
    "30-45 min": "#A995C4",
    "45-60 min": "#8067A0",
    ">60 min": "#59406F",
}

COLORS_AUTO = {
    "0–20 %": "#F7FCF5",
    "20–40 %": "#C7E9C0",
    "40–60 %": "#74C476",
    "60–80 %": "#238B45",
    "80–100 %": "#00441B",
    "Sense alumnat resident registrat en aquest àmbit": "#EFE7DA",
    "Sense dades": "#B8BEC5",
}

COLORS_ESCENARI = {
    "1–5": "#F2A7C4",
    "5–10": "#E875A2",
    "10–25": "#D94F86",
    "25–50": "#B92E68",
    ">50": "#7E1948",
}

COLORS_ACTUAL = {
    "1–5": "#AEB7C1",
    "5–10": "#8995A1",
    "10–25": "#64717E",
    "25–50": "#45525F",
    ">50": "#26313B",
}

AMPLADES_FLUX = {
    "1–5": 1.0,
    "5–10": 2.0,
    "10–25": 3.0,
    "25–50": 4.5,
    ">50": 6.5,
}

AMPLADES_ESCENARI = {
    "1–5": 1.5,
    "5–10": 2.5,
    "10–25": 4.0,
    "25–50": 6.0,
    ">50": 8.0,
}


def hex_a_rgba(hex_color):
    valor = hex_color.lstrip("#")
    return [int(valor[i:i + 2], 16) for i in (0, 2, 4)] + [255]


def classe_flux(v):
    if v <= 5:
        return "1–5"
    if v <= 10:
        return "5–10"
    if v <= 25:
        return "10–25"
    if v <= 50:
        return "25–50"
    return ">50"


def classe_auto(v):
    if pd.isna(v):
        return "Sense dades"
    if v < 20:
        return "0–20 %"
    if v < 40:
        return "20–40 %"
    if v < 60:
        return "40–60 %"
    if v < 80:
        return "60–80 %"
    return "80–100 %"


def color_flux(v):
    return hex_a_rgba(COLORS_FLUX[classe_flux(v)])


def color_temps(c):
    return hex_a_rgba(COLORS_TEMPS.get(c, "#828282"))


def color_auto(v):
    return hex_a_rgba(COLORS_AUTO[classe_auto(v)])


def color_escenari(v, vista):
    categoria = classe_flux(v)
    paleta = COLORS_ACTUAL if vista == "Situació actual" else COLORS_ESCENARI
    return hex_a_rgba(paleta[categoria])


def amplada_flux(v):
    return AMPLADES_FLUX[classe_flux(v)]


def amplada_escenari(v):
    return AMPLADES_ESCENARI[classe_flux(v)]



def format_decimal(valor, decimals=1):
    if pd.isna(valor):
        return "Sense dades"
    return f"{float(valor):.{decimals}f}".replace(".", ",")


def mitjana_ponderada(dades, columna_valor, columna_pes):
    if dades is None or dades.empty:
        return None
    valid = dades.dropna(subset=[columna_valor, columna_pes]).copy()
    valid = valid[valid[columna_pes] > 0]
    if valid.empty:
        return None
    pes_total = valid[columna_pes].sum()
    if pes_total <= 0:
        return None
    return float((valid[columna_valor] * valid[columna_pes]).sum() / pes_total)


def reiniciar_categories_llegenda():
    """Reactiva totes les categories quan canvia el mode o l'àmbit."""
    grups = {
        "flux": CLASSES_FLUX,
        "temps": CLASSES_TEMPS,
        "auto": CLASSES_AUTO,
        "escenari": CLASSES_ESCENARI,
    }
    for prefix, categories in grups.items():
        for categoria in categories:
            st.session_state[f"visible_{prefix}_{categoria}"] = True


def mostrar_carrega(placeholder, percentatge, missatge):
    """Mostra una capa flotant amb un progrés orientatiu per fases."""
    percentatge = max(0, min(100, int(percentatge)))
    placeholder.markdown(
        f"""
        <div class="visor-loading-overlay">
          <div class="visor-loading-card">
            <div class="visor-spinner"></div>
            <div style="font-size:18px;font-weight:700;">El visor està calculant</div>
            <div style="font-size:14px;margin-top:7px;color:#52606D;">{missatge}</div>
            <div class="visor-progress-track">
              <div class="visor-progress-fill" style="width:{percentatge}%;"></div>
            </div>
            <div style="font-size:13px;margin-top:8px;color:#7B8794;">
              Progrés orientatiu · {percentatge}%
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inicialitzar_categories():
    grups = {
        "flux": CLASSES_FLUX,
        "temps": CLASSES_TEMPS,
        "auto": CLASSES_AUTO,
        "escenari": CLASSES_ESCENARI,
    }
    for prefix, categories in grups.items():
        for categoria in categories:
            clau = f"visible_{prefix}_{categoria}"
            if clau not in st.session_state:
                st.session_state[clau] = True


def categories_actives(prefix, categories):
    return [
        categoria
        for categoria in categories
        if st.session_state.get(f"visible_{prefix}_{categoria}", True)
    ]


def fila_llegenda_interactiva(prefix, categoria, color, amplada=4):
    col_check, col_simbol, col_text = st.columns(
        [0.24, 0.62, 1.45],
        gap="small",
        vertical_alignment="center",
    )
    with col_check:
        st.checkbox(
            categoria,
            key=f"visible_{prefix}_{categoria}",
            label_visibility="collapsed",
        )
    with col_simbol:
        st.markdown(
            (
                "<div style='height:28px;display:flex;align-items:center;'>"
                f"<span style='width:50px;border-top:{amplada}px solid {color};"
                "display:inline-block;'></span></div>"
            ),
            unsafe_allow_html=True,
        )
    with col_text:
        st.markdown(
            f"<div style='font-size:13px;line-height:28px;'>{categoria}</div>",
            unsafe_allow_html=True,
        )

def llegenda_flux_interactiva(prefix, titol, categories, colors, amplades):
    st.markdown(f"**{titol}**")
    for categoria in categories:
        fila_llegenda_interactiva(
            prefix,
            categoria,
            colors[categoria],
            amplades[categoria],
        )


def llegenda_temps_interactiva():
    st.markdown("**Temps estimat**")
    for categoria in CLASSES_TEMPS:
        fila_llegenda_interactiva(
            "temps",
            categoria,
            COLORS_TEMPS[categoria],
            4,
        )

    st.markdown("---")
    st.markdown("**Volum d’alumnat**")
    for categoria in ["1–5", "10–25", ">50"]:
        st.markdown(
            (
                "<div style='display:flex;align-items:center;gap:10px;"
                "margin:6px 0;font-size:13px;'>"
                f"<span style='width:48px;border-top:{AMPLADES_FLUX[categoria]}px "
                "solid #8067A0;display:inline-block;'></span>"
                f"<span>{categoria} alumnes</span></div>"
            ),
            unsafe_allow_html=True,
        )


def llegenda_auto_interactiva():
    st.markdown("**Autocontenció**")
    for categoria in CLASSES_AUTO:
        col_check, col_color, col_text = st.columns(
            [0.24, 0.40, 1.55],
            gap="small",
            vertical_alignment="center",
        )
        with col_check:
            st.checkbox(
                categoria,
                key=f"visible_auto_{categoria}",
                label_visibility="collapsed",
            )
        with col_color:
            st.markdown(
                (
                    "<div style='height:24px;display:flex;align-items:center;'>"
                    f"<span style='width:20px;height:12px;background:{COLORS_AUTO[categoria]};"
                    "border:1px solid rgba(0,0,0,.15);display:inline-block;'></span></div>"
                ),
                unsafe_allow_html=True,
            )
        with col_text:
            st.markdown(
                f"<div style='font-size:13px;line-height:28px;'>{categoria}</div>",
                unsafe_allow_html=True,
            )


inicialitzar_categories()

def preparar_geojson_auto(
    base,
    dades,
    categories_actives_mapa,
    codis_amb_dades_totals,
    ambit_seleccionat,
):
    resultat = copy.deepcopy(base)
    idx = dades.drop_duplicates("codi_muni").set_index("codi_muni").to_dict("index")

    for feat in resultat["features"]:
        p = feat["properties"]
        codi = str(p.get("codi5", "")).strip().zfill(5)
        d = idx.get(codi)

        if d is None:
            te_dades_totals = codi in codis_amb_dades_totals

            if ambit_seleccionat != "Total estudis" and te_dades_totals:
                categoria = "Sense alumnat resident registrat en aquest àmbit"
                nom = p.get("NOMMUNI", "Municipi sense nom")
            else:
                categoria = "Sense dades"
                nom = p.get("NOMMUNI", "Municipi sense nom")

            residents = interns = externs = None
            auto = externa = None
        else:
            auto = d["autocontencio_pct"]
            categoria = classe_auto(auto)
            nom = d["nom_muni"]
            residents = d["alumnes_residents_total"]
            interns = d["alumnes_interns"]
            externs = d["alumnes_externs"]
            externa = d["mobilitat_externa_pct"]

        color = (
            hex_a_rgba(COLORS_AUTO[categoria])
            if categoria in categories_actives_mapa
            else [232, 235, 238, 190]
        )

        p.update({
            "nom_muni": nom,
            "alumnes_residents_total": residents,
            "alumnes_interns": interns,
            "alumnes_externs": externs,
            "autocontencio_pct": auto,
            "mobilitat_externa_pct": externa,
            "residents_fmt": (
                "Sense dades"
                if residents is None
                else f"{int(residents):,}".replace(",", ".")
            ),
            "interns_fmt": (
                "Sense dades"
                if interns is None
                else f"{int(interns):,}".replace(",", ".")
            ),
            "externs_fmt": (
                "Sense dades"
                if externs is None
                else f"{int(externs):,}".replace(",", ".")
            ),
            "autocontencio_fmt": format_decimal(auto),
            "mobilitat_externa_fmt": format_decimal(externa),
            "categoria_auto": categoria,
            "situacio_dada": categoria,
            "color": color,
        })

    return resultat

def geojson_municipi(codi):
    if codi is None:
        return None
    feats = [f for f in municipis_geojson["features"] if str(f["properties"].get("codi5", "")).strip().zfill(5) == codi]
    return {"type": "FeatureCollection", "features": feats}


def aplicar_capacitat(candidats, capacitat):
    candidats = candidats.sort_values(["estalvi_min", "flux"], ascending=[False, False]).copy()
    restant = int(capacitat)
    assignats = []
    for _, fila in candidats.iterrows():
        volum = max(int(round(float(fila["flux"]))), 0)
        assignacio = min(volum, restant) if restant > 0 else 0
        assignats.append(assignacio)
        restant -= assignacio
    candidats["alumnat_reassignable"] = assignats
    return candidats[candidats["alumnat_reassignable"] > 0].copy()


def indicadors_escenari(df):
    alumnat = df["alumnat_reassignable"].sum()
    if alumnat <= 0:
        return 0, 0, 0.0, 0.0, 0.0
    actual = (df["temps_ors_min"] * df["alumnat_reassignable"]).sum() / alumnat
    nou = (df["temps_nou_min"] * df["alumnat_reassignable"]).sum() / alumnat
    return int(alumnat), int(df["ori_cod"].nunique()), float(actual), float(nou), float(actual - nou)


st.markdown(
    """
    <div class="tfm-header">
      <div class="tfm-logos">
        <img
          class="tfm-logo-master"
          src="data:image/png;base64,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"
          alt="Màster en Geoinformació"
        />
        <span class="tfm-logo-separator"></span>
        <img
          class="tfm-logo-uab"
          src="data:image/png;base64,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"
          alt="Universitat Autònoma de Barcelona · Departament de Geografia"
        />
      </div>

      <div>
        <h1 class="tfm-title">Visor de mobilitat escolar a Catalunya</h1>
        <p class="tfm-subtitle">
          Explora els desplaçaments de l’alumnat entre municipis, els temps estimats
          de trajecte, l’autocontenció educativa i un possible nou escenari de centre.
        </p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

carrega_global = st.empty()

st.sidebar.header("Opcions de visualització")
mode = st.sidebar.radio(
    "Capa principal",
    ["Fluxos actuals", "Temps estimats", "Autocontenció educativa", "Nou escenari"],
    key="mode_principal",
    on_change=reiniciar_categories_llegenda,
)

ambits_flux = {
    "Educació primària": "Primària",
    "Educació secundària obligatòria (ESO)": "ESO",
    "Batxillerat": "Batxillerat",
    "Formació professional": "FP",
}
ambits_auto = {
    "Total estudis": "Total estudis",
    "Educació primària": "EDUCACIÓ PRIMÀRIA",
    "Educació secundària obligatòria (ESO)": "EDUCACIÓ SECUNDÀRIA OBLIGATÒRIA",
    "Batxillerat": "BATXILLERAT",
    "Formació professional": "FORMACIÓ PROFESSIONAL",
}

municipis = sorted(
    [(f["properties"]["NOMMUNI"], str(f["properties"]["codi5"]).strip().zfill(5)) for f in municipis_geojson["features"]],
    key=lambda x: x[0],
)
opcions_municipis = {"Cap municipi seleccionat": None, **{n: c for n, c in municipis}}

etiqueta_ambit = None
ambit = None
nom_consultat = None
codi_consultat = None
mostrar_relacionats = False
nom_nou = None
codi_nou = None
capacitat = 0
millora = 0.0
vista_comparacio = "Nou escenari"
categories_actives_mapa = []

if mode in ["Fluxos actuals", "Temps estimats"]:
    etiqueta_ambit = st.sidebar.selectbox(
        "Àmbit educatiu",
        list(ambits_flux.keys()),
        key="ambit_flux_temps",
        on_change=reiniciar_categories_llegenda,
    )
    ambit = ambits_flux[etiqueta_ambit]
    categories_actives_mapa = (
        categories_actives("flux", CLASSES_FLUX)
        if mode == "Fluxos actuals"
        else categories_actives("temps", CLASSES_TEMPS)
    )

    nom_consultat = st.sidebar.selectbox("Municipi consultat", list(opcions_municipis.keys()))
    codi_consultat = opcions_municipis[nom_consultat]
    if codi_consultat is not None:
        mostrar_relacionats = st.sidebar.checkbox(
            "Mostrar només fluxos relacionats",
            value=True,
            help="Mostra els fluxos que surten del municipi i els que hi arriben.",
        )

elif mode == "Autocontenció educativa":
    etiqueta_ambit = st.sidebar.selectbox(
        "Àmbit educatiu",
        list(ambits_auto.keys()),
        key="ambit_autocontencio",
        on_change=reiniciar_categories_llegenda,
    )
    ambit = ambits_auto[etiqueta_ambit]
    categories_actives_mapa = categories_actives("auto", CLASSES_AUTO)
    nom_consultat = st.sidebar.selectbox("Municipi consultat", list(opcions_municipis.keys()))
    codi_consultat = opcions_municipis[nom_consultat]

else:
    st.sidebar.subheader("Creació del nou escenari")
    etiqueta_ambit = st.sidebar.selectbox(
        "Àmbit educatiu",
        list(ambits_flux.keys()),
        key="ambit_escenari",
        on_change=reiniciar_categories_llegenda,
    )
    ambit = ambits_flux[etiqueta_ambit]
    opcions_nou = {n: c for n, c in opcions_municipis.items() if c is not None}
    nom_nou = st.sidebar.selectbox("Municipi del nou centre", list(opcions_nou.keys()))
    codi_nou = opcions_nou[nom_nou]
    capacitat = st.sidebar.number_input(
        "Places màximes del nou centre",
        min_value=1,
        max_value=5000,
        value=300,
        step=25,
    )
    millora = st.sidebar.number_input(
        "Millora mínima de temps (min)",
        min_value=0.0,
        max_value=120.0,
        value=10.0,
        step=1.0,
        help="Estalvi mínim necessari perquè un flux es consideri candidat al nou centre.",
    )
    vista_comparacio = st.sidebar.radio(
        "Visualització de l'escenari",
        ["Situació actual", "Nou escenari"],
        index=1,
        help=(
            "Compara els fluxos candidats cap als seus destins actuals "
            "amb els mateixos fluxos redirigits cap al nou centre."
        ),
    )
    categories_actives_mapa = categories_actives("escenari", CLASSES_ESCENARI)

    if st.sidebar.button("Calcular nou escenari", type="primary", width="stretch"):
        fluxos_ambit = fluxos[fluxos["ambit"] == ambit].dropna(
            subset=["ori_cod", "flux", "temps_ors_min", "lon_origen", "lat_origen"]
        ).copy()
        codis_origen = fluxos_ambit["ori_cod"].drop_duplicates().tolist()
        try:
            mostrar_carrega(
                carrega_global,
                15,
                "Preparant els municipis d’origen i la consulta de temps...",
            )
            mostrar_carrega(
                carrega_global,
                30,
                "Calculant els temps cap al municipi proposat. Aquesta fase pot trigar uns instants...",
            )
            temps_nous = calcular_temps_cap_nou_centre(codis_origen, codi_nou)
            mostrar_carrega(
                carrega_global,
                72,
                "Comparant els temps actuals amb els del nou centre...",
            )
            comparacio = fluxos_ambit.merge(
                temps_nous[["ori_cod", "temps_nou_min", "distancia_nova_km"]],
                on="ori_cod",
                how="left",
            ).dropna(subset=["temps_nou_min", "temps_ors_min"])
            comparacio = comparacio[comparacio["ori_cod"] != codi_nou].copy()
            comparacio["estalvi_min"] = (
                comparacio["temps_ors_min"] - comparacio["temps_nou_min"]
            )
            candidats = comparacio[comparacio["estalvi_min"] >= millora].copy()
            candidats["des_nom_actual"] = candidats["des_nom"]
            candidats["nou_centre_nom"] = nom_nou
            mostrar_carrega(
                carrega_global,
                88,
                "Aplicant la capacitat del centre i preparant els resultats...",
            )
            resultat = aplicar_capacitat(candidats, int(capacitat))
            st.session_state.resultat_escenari = resultat
            st.session_state.configuracio_escenari = {
                "ambit": ambit,
                "etiqueta_ambit": etiqueta_ambit,
                "codi_nou_centre": codi_nou,
                "nom_nou_centre": nom_nou,
                "capacitat_maxima": int(capacitat),
                "millora_minima": float(millora),
            }
            mostrar_carrega(
                carrega_global,
                100,
                "Càlcul completat. Preparant la visualització...",
            )
            carrega_global.empty()
            if resultat.empty:
                st.sidebar.warning(
                    "No s'han identificat fluxos que compleixin els criteris indicats."
                )
            else:
                st.sidebar.success("Nou escenari calculat correctament.")
        except Exception as e:
            carrega_global.empty()
            st.session_state.resultat_escenari = None
            st.session_state.configuracio_escenari = None
            st.sidebar.error(f"No s'ha pogut calcular l'escenari: {e}")

mostrar_municipis = st.sidebar.checkbox(
    "Mostrar límits municipals",
    value=True,
    help="Activa o desactiva les divisions administratives municipals.",
)

fluxos_filtrats = pd.DataFrame()
fluxos_mapa = pd.DataFrame()
auto_filtrada = pd.DataFrame()
auto_geojson = None
municipi_geojson = None
nou_centre_geojson = None
punt_nou = pd.DataFrame()
resultat_escenari = None
resultat_escenari_visible = None
config_escenari = None

if mode in ["Fluxos actuals", "Temps estimats"]:
    fluxos_filtrats = fluxos[fluxos["ambit"] == ambit].dropna(
        subset=["lon_origen", "lat_origen", "lon_desti", "lat_desti", "flux"]
    ).copy()
    fluxos_filtrats["classe_flux"] = fluxos_filtrats["flux"].apply(classe_flux)
    fluxos_filtrats["color"] = (
        fluxos_filtrats["flux"].apply(color_flux)
        if mode == "Fluxos actuals"
        else fluxos_filtrats["classe_temps"].apply(color_temps)
    )
    fluxos_filtrats["amplada_flux"] = fluxos_filtrats["flux"].apply(amplada_flux)
    fluxos_filtrats["flux_fmt"] = fluxos_filtrats["flux"].round(0).astype(int).astype(str)
    fluxos_filtrats["temps_fmt"] = fluxos_filtrats["temps_ors_min"].apply(format_decimal)
    fluxos_filtrats["distancia_fmt"] = fluxos_filtrats["distancia_ors_km"].apply(format_decimal)

    if mode == "Fluxos actuals":
        fluxos_mapa = fluxos_filtrats[fluxos_filtrats["classe_flux"].isin(categories_actives_mapa)].copy()
    else:
        fluxos_mapa = fluxos_filtrats[fluxos_filtrats["classe_temps"].isin(categories_actives_mapa)].copy()

    if mostrar_relacionats and codi_consultat is not None:
        fluxos_mapa = fluxos_mapa[
            (fluxos_mapa["ori_cod"] == codi_consultat)
            | (fluxos_mapa["des_cod"] == codi_consultat)
        ].copy()
    municipi_geojson = geojson_municipi(codi_consultat)

elif mode == "Autocontenció educativa":
    auto_filtrada = autocontencio[autocontencio["estudis"] == ambit].copy()
    codis_amb_dades_totals = set(
        autocontencio.loc[
            autocontencio["estudis"] == "Total estudis",
            "codi_muni",
        ].astype(str).str.strip().str.zfill(5)
    )
    auto_geojson = preparar_geojson_auto(
        municipis_geojson,
        auto_filtrada,
        categories_actives_mapa,
        codis_amb_dades_totals,
        ambit,
    )
    municipi_geojson = geojson_municipi(codi_consultat)

else:
    resultat_escenari = st.session_state.resultat_escenari
    config_escenari = st.session_state.configuracio_escenari
    codi_visible = config_escenari["codi_nou_centre"] if config_escenari else codi_nou
    nou_centre_geojson = geojson_municipi(codi_visible)
    punt_nou = caps[caps["codi_mun_2"] == codi_visible].copy()
    if resultat_escenari is not None and not resultat_escenari.empty and not punt_nou.empty:
        resultat_escenari = resultat_escenari.copy()
        resultat_escenari["lon_nou_centre"] = float(punt_nou.iloc[0]["longitud"])
        resultat_escenari["lat_nou_centre"] = float(punt_nou.iloc[0]["latitud"])
        resultat_escenari["classe_escenari"] = resultat_escenari["alumnat_reassignable"].apply(classe_flux)
        resultat_escenari["amplada_escenari"] = resultat_escenari["alumnat_reassignable"].apply(amplada_escenari)
        resultat_escenari["color_escenari"] = resultat_escenari["alumnat_reassignable"].apply(
            lambda v: color_escenari(v, vista_comparacio)
        )
        resultat_escenari["alumnat_fmt"] = resultat_escenari["alumnat_reassignable"].round(0).astype(int).astype(str)
        resultat_escenari["temps_actual_fmt"] = resultat_escenari["temps_ors_min"].apply(format_decimal)
        resultat_escenari["temps_nou_fmt"] = resultat_escenari["temps_nou_min"].apply(format_decimal)
        resultat_escenari["estalvi_fmt"] = resultat_escenari["estalvi_min"].apply(format_decimal)
        resultat_escenari["distancia_actual_fmt"] = resultat_escenari["distancia_ors_km"].apply(format_decimal)
        resultat_escenari["distancia_nova_fmt"] = resultat_escenari["distancia_nova_km"].apply(format_decimal)
        resultat_escenari_visible = resultat_escenari[
            resultat_escenari["classe_escenari"].isin(categories_actives_mapa)
        ].copy()

capes = []
if mostrar_municipis and mode != "Autocontenció educativa":
    capes.append(pdk.Layer(
        "GeoJsonLayer", municipis_geojson, stroked=True, filled=True,
        get_fill_color=[247, 245, 242, 6],
        get_line_color=[165, 174, 183, 235],
        line_width_min_pixels=0.70,
        pickable=False,
    ))

if mode in ["Fluxos actuals", "Temps estimats"]:
    capes.append(pdk.Layer(
        "ArcLayer", data=fluxos_mapa,
        get_source_position=["lon_origen", "lat_origen"],
        get_target_position=["lon_desti", "lat_desti"],
        get_source_color="color", get_target_color="color", get_width="amplada_flux",
        width_min_pixels=0.9, width_max_pixels=8, pickable=True, auto_highlight=True,
    ))
elif mode == "Autocontenció educativa":
    capes.append(pdk.Layer(
        "GeoJsonLayer", auto_geojson, stroked=True, filled=True,
        get_fill_color="properties.color", get_line_color=[130, 138, 146, 125],
        line_width_min_pixels=0.55, pickable=True, auto_highlight=True,
    ))
else:
    if resultat_escenari_visible is not None and not resultat_escenari_visible.empty:
        posicio_desti = ["lon_desti", "lat_desti"] if vista_comparacio == "Situació actual" else ["lon_nou_centre", "lat_nou_centre"]
        capes.append(pdk.Layer(
            "ArcLayer", data=resultat_escenari_visible,
            get_source_position=["lon_origen", "lat_origen"],
            get_target_position=posicio_desti,
            get_source_color="color_escenari",
            get_target_color="color_escenari",
            get_width="amplada_escenari",
            width_min_pixels=1.5,
            width_max_pixels=9,
            pickable=True,
            auto_highlight=True,
        ))

    if vista_comparacio == "Nou escenari" and not punt_nou.empty:
        capes.append(pdk.Layer(
            "ScatterplotLayer", data=punt_nou, get_position=["longitud", "latitud"],
            get_fill_color=[95, 107, 118, 255], get_line_color=[255, 255, 255, 255],
            get_radius=5000, radius_min_pixels=7, radius_max_pixels=18,
            stroked=True, line_width_min_pixels=2, pickable=False,
        ))

if municipi_geojson is not None:
    capes.append(pdk.Layer(
        "GeoJsonLayer", municipi_geojson, stroked=True, filled=True,
        get_fill_color=[244, 201, 93, 105], get_line_color=[193, 139, 0, 255],
        line_width_min_pixels=3, pickable=False,
    ))
if nou_centre_geojson is not None and vista_comparacio == "Nou escenari":
    capes.append(pdk.Layer(
        "GeoJsonLayer", nou_centre_geojson, stroked=True, filled=True,
        get_fill_color=[255, 196, 85, 90], get_line_color=[180, 95, 20, 255],
        line_width_min_pixels=3, pickable=False,
    ))


# Reforç visual dels fluxos relacionats amb el municipi consultat.
# Aquesta capa es dibuixa per sobre del polígon seleccionat perquè els
# desplaçaments molt curts no quedin ocults.
if (
    mode in ["Fluxos actuals", "Temps estimats"]
    and codi_consultat is not None
    and mostrar_relacionats
    and fluxos_mapa is not None
    and not fluxos_mapa.empty
):
    fluxos_consulta_destacats = fluxos_mapa.copy()
    fluxos_consulta_destacats["amplada_consulta"] = (
        fluxos_consulta_destacats["amplada_flux"].clip(lower=3.2)
    )

    capes.append(pdk.Layer(
        "ArcLayer",
        data=fluxos_consulta_destacats,
        get_source_position=["lon_origen", "lat_origen"],
        get_target_position=["lon_desti", "lat_desti"],
        get_source_color="color",
        get_target_color="color",
        get_width="amplada_consulta",
        width_min_pixels=2.8,
        width_max_pixels=9,
        pickable=False,
        auto_highlight=False,
    ))

vista = pdk.ViewState(latitude=41.75, longitude=1.75, zoom=6.7, pitch=0, bearing=0)

if mode in ["Fluxos actuals", "Temps estimats"]:
    tooltip = {
        "html": (
            "<b>Origen:</b> {ori_nom}<br/>"
            "<b>Destinació:</b> {des_nom}<br/>"
            "<b>Àmbit:</b> {ambit}<br/>"
            "<b>Alumnat:</b> {flux_fmt}<br/>"
            "<b>Temps estimat:</b> {temps_fmt} min<br/>"
            "<b>Distància:</b> {distancia_fmt} km"
        ),
        "style": {"backgroundColor": "#17233c", "color": "white", "fontSize": "13px"},
    }
elif mode == "Autocontenció educativa":
    tooltip = {
        "html": (
            "<b>Municipi:</b> {nom_muni}<br/>"
            "<b>Alumnat que hi resideix:</b> {residents_fmt}<br/>"
            "<b>Estudia al mateix municipi:</b> {interns_fmt}<br/>"
            "<b>Estudia en un altre municipi:</b> {externs_fmt}<br/>"
            "<b>Autocontenció:</b> {autocontencio_fmt} %<br/>"
            "<b>Mobilitat externa:</b> {mobilitat_externa_fmt} %"
        ),
        "style": {"backgroundColor": "#17233c", "color": "white", "fontSize": "13px"},
    }
else:
    if vista_comparacio == "Situació actual":
        text_comparacio = (
            "<b>Visualització:</b> Situació actual<br/>"
            "<b>Origen:</b> {ori_nom}<br/>"
            "<b>Destinació actual:</b> {des_nom_actual}<br/>"
            "<b>Alumnat potencialment reassignable:</b> {alumnat_fmt}<br/>"
            "<b>Temps actual:</b> {temps_actual_fmt} min<br/>"
            "<b>Temps cap al nou centre:</b> {temps_nou_fmt} min<br/>"
            "<b>Estalvi potencial:</b> {estalvi_fmt} min"
        )
    else:
        text_comparacio = (
            "<b>Visualització:</b> Nou escenari<br/>"
            "<b>Origen:</b> {ori_nom}<br/>"
            "<b>Destinació actual:</b> {des_nom_actual}<br/>"
            "<b>Nou centre:</b> {nou_centre_nom}<br/>"
            "<b>Alumnat potencialment reassignable:</b> {alumnat_fmt}<br/>"
            "<b>Temps actual:</b> {temps_actual_fmt} min<br/>"
            "<b>Temps nou:</b> {temps_nou_fmt} min<br/>"
            "<b>Estalvi:</b> {estalvi_fmt} min"
        )
    tooltip = {
        "html": text_comparacio,
        "style": {"backgroundColor": "#17233c", "color": "white", "fontSize": "13px"},
    }

def mostrar_llegenda_mapa():
    st.subheader("Llegenda")

    if mode == "Fluxos actuals":
        llegenda_flux_interactiva(
            "flux",
            "Volum d’alumnat",
            CLASSES_FLUX,
            COLORS_FLUX,
            AMPLADES_FLUX,
        )
        st.caption(
            "Marca o desmarca cada rang per decidir quins fluxos es mostren al mapa."
        )

    elif mode == "Temps estimats":
        llegenda_temps_interactiva()
        st.caption(
            "Marca o desmarca els intervals de temps. "
            "L’amplada continua representant el volum d’alumnat."
        )

    elif mode == "Autocontenció educativa":
        llegenda_auto_interactiva()
        st.caption(
            "Les categories desactivades es mantenen en gris clar "
            "per conservar la forma del territori."
        )

    else:
        paleta = COLORS_ACTUAL if vista_comparacio == "Situació actual" else COLORS_ESCENARI
        titol = "Situació actual" if vista_comparacio == "Situació actual" else "Nou escenari"
        llegenda_flux_interactiva(
            "escenari",
            titol,
            CLASSES_ESCENARI,
            paleta,
            AMPLADES_ESCENARI,
        )
        st.caption(
            "Marca o desmarca els rangs d’alumnat potencialment reassignable."
        )
        st.markdown("---")
        st.markdown("**Nou centre proposat**")
        st.markdown(
            "<div style='display:flex;align-items:center;gap:9px;font-size:13px;'>"
            "<span style='width:14px;height:14px;border-radius:50%;"
            "background:#5F6B76;border:2px solid #FFFFFF;"
            "box-shadow:0 0 0 1px #AAB2BA;display:inline-block;'></span>"
            "<span>Punt de localització del nou centre</span></div>",
            unsafe_allow_html=True,
        )


# Control propi superposat dins del mapa.
def control_superposat_mapa():
    simbol = "↙" if st.session_state.mapa_ampliat else "⛶"
    ajuda = (
        "Contraure el mapa"
        if st.session_state.mapa_ampliat
        else "Ampliar el mapa"
    )

    with st.container(key="mapa_control_superposat"):
        if st.button(
            simbol,
            key="canviar_mida_mapa",
            help=ajuda,
        ):
            st.session_state.mapa_ampliat = not st.session_state.mapa_ampliat
            st.rerun()


deck_mapa = pdk.Deck(
    layers=capes,
    initial_view_state=vista,
    tooltip=tooltip,
    map_style=None,
)

if st.session_state.mapa_ampliat:
    control_superposat_mapa()
    st.pydeck_chart(
    deck_mapa,
    use_container_width=True,
    height=900,
    )
    with st.expander("Llegenda i filtres del mapa", expanded=True):
        mostrar_llegenda_mapa()
else:
    col_mapa, col_llegenda = st.columns([5, 1.25])
    with col_mapa:
        control_superposat_mapa()
        st.pydeck_chart(
        deck_mapa,
        use_container_width=True,
        height=650,
        )
    with col_llegenda:
        mostrar_llegenda_mapa()


def text_filtres_actius():
    if mode == "Fluxos actuals":
        rangs = (
            "Tots els rangs de volum"
            if set(categories_actives_mapa) == set(CLASSES_FLUX)
            else "Volum " + ", ".join(categories_actives_mapa)
        )
        municipi = (
            nom_consultat
            if codi_consultat is not None and mostrar_relacionats
            else "Tots els municipis"
        )
        return f"{etiqueta_ambit} · {municipi} · {rangs}"

    if mode == "Temps estimats":
        rangs = (
            "Tots els intervals de temps"
            if set(categories_actives_mapa) == set(CLASSES_TEMPS)
            else "Temps " + ", ".join(categories_actives_mapa)
        )
        municipi = (
            nom_consultat
            if codi_consultat is not None and mostrar_relacionats
            else "Tots els municipis"
        )
        return f"{etiqueta_ambit} · {municipi} · {rangs}"

    if mode == "Autocontenció educativa":
        rangs = (
            "Totes les categories d’autocontenció"
            if set(categories_actives_mapa) == set(CLASSES_AUTO)
            else "Autocontenció " + ", ".join(categories_actives_mapa)
        )
        municipi = nom_consultat if codi_consultat is not None else "Tots els municipis"
        return f"{etiqueta_ambit} · {municipi} · {rangs}"

    rangs = (
        "Tots els rangs d’alumnat reassignable"
        if set(categories_actives_mapa) == set(CLASSES_ESCENARI)
        else "Alumnat reassignable " + ", ".join(categories_actives_mapa)
    )
    municipi = (
        config_escenari["nom_nou_centre"]
        if config_escenari is not None
        else nom_nou
    )
    return f"{etiqueta_ambit} · Nou centre: {municipi} · {rangs}"


st.divider()

if mode in ["Fluxos actuals", "Temps estimats"]:
    st.subheader("Resum dels fluxos visibles")
elif mode == "Autocontenció educativa":
    st.subheader("Resum de l’autocontenció visible")
else:
    st.subheader("Resum de l’escenari visible")

st.markdown(
    f"""
    <div style="padding:10px 14px;margin:4px 0 18px 0;
                border-left:4px solid #183B56;
                background:#F4F7FA;border-radius:6px;
                font-size:14px;color:#102A43;">
        <strong>Filtres actius:</strong> {text_filtres_actius()}
    </div>
    """,
    unsafe_allow_html=True,
)

if mode in ["Fluxos actuals", "Temps estimats"]:
    temps_ponderat = mitjana_ponderada(fluxos_mapa, "temps_ors_min", "flux")
    consulta_activa = codi_consultat is not None and mostrar_relacionats

    if consulta_activa:
        etiqueta_fluxos = "Fluxos d’entrada i sortida"
        etiqueta_alumnat = "Alumnat en aquests fluxos"
        etiqueta_temps = "Temps mitjà ponderat dels fluxos relacionats"
    else:
        etiqueta_fluxos = "Fluxos visibles"
        etiqueta_alumnat = "Alumnat representat"
        etiqueta_temps = "Temps mitjà ponderat per alumnat"

    c1, c2, c3 = st.columns(3)
    c1.metric(
        etiqueta_fluxos,
        f"{len(fluxos_mapa):,}".replace(",", "."),
        help="Cada flux és una relació entre un municipi d’origen i un municipi de destinació.",
    )
    c2.metric(
        etiqueta_alumnat,
        f"{int(fluxos_mapa['flux'].sum()):,}".replace(",", "."),
        help="Un mateix flux pot agrupar diversos alumnes.",
    )
    c3.metric(
        etiqueta_temps,
        "Sense dades" if temps_ponderat is None else f"{temps_ponderat:.1f} min",
        help=(
            "La mitjana es calcula tenint en compte el nombre d’alumnes de cada flux. "
            "Els fluxos amb més alumnat tenen més pes en el resultat."
        ),
    )

    if consulta_activa:
        st.info(
            "El resum inclou els fluxos que surten del municipi i els que hi arriben "
            "des d’altres municipis. No inclou l’alumnat que hi resideix i estudia al mateix municipi."
        )
    else:
        st.info(
            "Els indicadors corresponen als fluxos que es veuen al mapa després d’aplicar "
            "els filtres de l’àmbit educatiu i dels rangs seleccionats."
        )

elif mode == "Autocontenció educativa":
    residents = auto_filtrada["alumnes_residents_total"].sum()
    interns = auto_filtrada["alumnes_interns"].sum()
    global_auto = interns / residents * 100 if residents > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Municipis amb dades",
        f"{len(auto_filtrada):,}".replace(",", "."),
        help="Nombre de municipis amb informació disponible per a l’àmbit seleccionat.",
    )
    c2.metric(
        "Alumnat que hi resideix",
        f"{int(residents):,}".replace(",", "."),
        help=(
            "Alumnat que viu als municipis analitzats. Inclou tant qui estudia al mateix municipi "
            "com qui estudia en un altre municipi."
        ),
    )
    c3.metric(
        "Autocontenció global",
        f"{global_auto:.1f} %",
        help="Percentatge d’alumnat que viu i estudia al mateix municipi.",
    )
    st.info(
        "L’autocontenció permet observar fins a quin punt el municipi reté l’alumnat que hi resideix. "
        "Les categories desactivades a la llegenda es mostren en gris clar."
    )

else:
    if resultat_escenari_visible is None or resultat_escenari_visible.empty or config_escenari is None:
        st.info("Defineix els paràmetres del nou centre i prem «Calcular nou escenari».")
    else:
        alumnat, municipis_afectats, temps_actual, temps_nou, estalvi = indicadors_escenari(resultat_escenari_visible)
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Alumnes que podrien passar al nou centre",
            f"{alumnat:,}".replace(",", "."),
            help=(
                "Alumnat dels fluxos que compleixen la millora mínima de temps i que es troben "
                "dins de les places definides."
            ),
        )
        c2.metric(
            "Municipis d’on podrien venir",
            municipis_afectats,
            help="Nombre de municipis d’origen dels fluxos potencialment reassignables.",
        )
        c3.metric(
            "Temps mitjà que es podria estalviar",
            f"{estalvi:.1f} min",
            help="Diferència ponderada entre el temps actual i el temps estimat cap al nou centre.",
        )

        c4, c5, c6 = st.columns(3)
        c4.metric("Temps mitjà actual", f"{temps_actual:.1f} min")
        c5.metric("Temps mitjà amb el nou centre", f"{temps_nou:.1f} min")
        c6.metric("Places màximes del nou centre", config_escenari["capacitat_maxima"])

        st.info(
            f"L’escenari proposa un nou centre a {config_escenari['nom_nou_centre']} per a "
            f"{config_escenari['etiqueta_ambit']}. S’han considerat els fluxos amb una millora "
            f"mínima de {config_escenari['millora_minima']:.1f} minuts."
        )
        st.warning(
            "Aquest és un escenari orientatiu. No representa una assignació real d’alumnat i no incorpora "
            "preferències familiars, criteris d’admissió, places disponibles, especialitats formatives "
            "ni transport públic."
        )

# Informació específica del municipi consultat
if codi_consultat is not None and mode != "Nou escenari":
    st.divider()
    st.subheader(f"Municipi consultat: {nom_consultat}")

    if mode == "Autocontenció educativa":
        estudi_consulta = ambit
        dada = autocontencio[
            (autocontencio["codi_muni"] == codi_consultat)
            & (autocontencio["estudis"] == estudi_consulta)
        ]
        if not dada.empty:
            fila = dada.iloc[0]
            c1, c2, c3 = st.columns(3)
            c1.metric(
                "Alumnat que hi resideix",
                f"{int(fila['alumnes_residents_total']):,}".replace(",", "."),
                help="Alumnat que viu al municipi, tant si hi estudia com si es desplaça a un altre municipi.",
            )
            c2.metric("Estudia al mateix municipi", f"{int(fila['alumnes_interns']):,}".replace(",", "."))
            c3.metric("Estudia en un altre municipi", f"{int(fila['alumnes_externs']):,}".replace(",", "."))
            c4, c5 = st.columns(2)
            c4.metric("Autocontenció", f"{fila['autocontencio_pct']:.1f} %")
            c5.metric("Mobilitat externa", f"{fila['mobilitat_externa_pct']:.1f} %")
        else:
            st.warning("No hi ha dades disponibles per a aquest municipi i àmbit.")
    else:
        fluxos_consulta = fluxos_mapa.copy()
        sortida = fluxos_consulta[fluxos_consulta["ori_cod"] == codi_consultat].copy()
        entrada = fluxos_consulta[fluxos_consulta["des_cod"] == codi_consultat].copy()
        relacionats = pd.concat([sortida, entrada], ignore_index=True)
        temps_relacionats = mitjana_ponderada(relacionats, "temps_ors_min", "flux")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fluxos de sortida", f"{len(sortida):,}".replace(",", "."))
        c2.metric("Alumnat que surt", f"{int(sortida['flux'].sum()):,}".replace(",", "."))
        c3.metric("Fluxos d’entrada", f"{len(entrada):,}".replace(",", "."))
        c4.metric("Alumnat que arriba", f"{int(entrada['flux'].sum()):,}".replace(",", "."))
        if temps_relacionats is not None:
            st.metric(
                "Temps mitjà ponderat dels fluxos relacionats",
                f"{temps_relacionats:.1f} min",
                help="Mitjana dels temps d’entrada i sortida ponderada pel nombre d’alumnes de cada flux.",
            )

        estudi = {
            "Primària": "EDUCACIÓ PRIMÀRIA",
            "ESO": "EDUCACIÓ SECUNDÀRIA OBLIGATÒRIA",
            "Batxillerat": "BATXILLERAT",
            "FP": "FORMACIÓ PROFESSIONAL",
        }.get(ambit)
        dada = autocontencio[
            (autocontencio["codi_muni"] == codi_consultat)
            & (autocontencio["estudis"] == estudi)
        ]
        if not dada.empty:
            st.metric(
                "Autocontenció",
                f"{dada.iloc[0]['autocontencio_pct']:.1f} %",
                help="Percentatge d’alumnat que viu i estudia al mateix municipi.",
            )
# ---------------------------------------------------------
# Detall i descàrrega del nou escenari
# ---------------------------------------------------------

if (
    mode == "Nou escenari"
    and resultat_escenari_visible is not None
    and not resultat_escenari_visible.empty
    and config_escenari is not None
):
    st.divider()
    st.subheader("Detall dels fluxos potencialment reassignables")

    st.caption(
        "Els registres s'ordenen de més a menys estalvi de temps. "
        "L'assignació s'atura quan s'assoleix la capacitat màxima definida."
    )

    taula_escenari = resultat_escenari_visible[
        [
            "ori_cod",
            "ori_nom",
            "des_cod",
            "des_nom_actual",
            "nou_centre_nom",
            "alumnat_reassignable",
            "temps_ors_min",
            "temps_nou_min",
            "estalvi_min",
            "distancia_ors_km",
            "distancia_nova_km",
        ]
    ].copy()

    taula_escenari = taula_escenari.sort_values(
        ["estalvi_min", "alumnat_reassignable"],
        ascending=[False, False],
    )

    columnes_numeriques = [
        "temps_ors_min",
        "temps_nou_min",
        "estalvi_min",
        "distancia_ors_km",
        "distancia_nova_km",
    ]

    taula_escenari[columnes_numeriques] = (
        taula_escenari[columnes_numeriques].round(1)
    )

    taula_escenari = taula_escenari.rename(
        columns={
            "ori_cod": "Codi origen",
            "ori_nom": "Municipi d'origen",
            "des_cod": "Codi destinació actual",
            "des_nom_actual": "Destinació actual",
            "nou_centre_nom": "Nou centre proposat",
            "alumnat_reassignable": "Alumnat potencialment reassignable",
            "temps_ors_min": "Temps actual (min)",
            "temps_nou_min": "Temps nou (min)",
            "estalvi_min": "Estalvi estimat (min)",
            "distancia_ors_km": "Distància actual (km)",
            "distancia_nova_km": "Distància nova (km)",
        }
    )

    st.dataframe(
        taula_escenari,
        width="stretch",
        hide_index=True,
        column_config={
            "Alumnat potencialment reassignable": st.column_config.NumberColumn(
                format="%d"
            ),
            "Temps actual (min)": st.column_config.NumberColumn(format="%.1f"),
            "Temps nou (min)": st.column_config.NumberColumn(format="%.1f"),
            "Estalvi estimat (min)": st.column_config.NumberColumn(format="%.1f"),
            "Distància actual (km)": st.column_config.NumberColumn(format="%.1f"),
            "Distància nova (km)": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    csv_escenari = taula_escenari.to_csv(
        index=False,
        encoding="utf-8-sig",
    ).encode("utf-8-sig")

    nom_fitxer_escenari = (
        "nou_escenari_"
        f"{config_escenari['codi_nou_centre']}_"
        f"{config_escenari['ambit'].lower()}.csv"
    )

    st.download_button(
        label="Descarregar resultat de l'escenari en CSV",
        data=csv_escenari,
        file_name=nom_fitxer_escenari,
        mime="text/csv",
        width="stretch",
    )

    st.info(
        "La taula representa una redistribució potencial basada en "
        "l'estalvi de temps estimat i la capacitat indicada. No equival "
        "a una previsió de matrícula ni a una proposta definitiva de "
        "planificació educativa."
    )


st.markdown(
    """
    <footer class="tfm-footer">
      <div>
        <div class="tfm-footer-title">
          Anàlisi espacial de la mobilitat escolar no universitària a Catalunya
        </div>
        <div>
          Fluxos intermunicipals, temps de desplaçament i visor cartogràfic interactiu
        </div>
      </div>

      <div class="tfm-footer-author">
        <span style="font-weight:500;color:#687786;">Elaborat per:</span><br/>
        Fatima Hamza
      </div>

      <div class="tfm-footer-sources">
        <strong>Fonts:</strong> Dades Obertes Catalunya, OpenStreetMap i OpenRouteService.
      </div>
    </footer>
    """,
    unsafe_allow_html=True,
)

