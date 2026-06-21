from pathlib import Path

import geopandas as gpd
import pandas as pd


# ---------------------------------------------------------
# Rutes del projecte
# ---------------------------------------------------------

CARPETA_PROJECTE = Path(__file__).resolve().parent.parent
CARPETA_DADES = CARPETA_PROJECTE / "dades"
CARPETA_WEB = CARPETA_PROJECTE / "dades_web"

CARPETA_WEB.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Fitxers d'entrada
# ---------------------------------------------------------

FITXER_FLUXOS = (
    CARPETA_DADES
    / "linies_od_25_26_estudis_caps_amb_temps_ors.gpkg"
)

FITXER_AUTOCONTENCIO = (
    CARPETA_DADES
    / "autocontencio_estudis_municipis.gpkg"
)

FITXER_CAPS = CARPETA_DADES / "caps_municipi.gpkg"

FITXER_MUNICIPIS = CARPETA_DADES / "municipis_poligons.gpkg"


# ---------------------------------------------------------
# 1. Preparar els fluxos
# ---------------------------------------------------------

print("Llegint la capa de fluxos...")

fluxos = gpd.read_file(
    FITXER_FLUXOS,
    layer="linies_od_caps_amb_temps_ors",
)

camps_fluxos = [
    "ori_cod",
    "ori_nom",
    "des_cod",
    "des_nom",
    "estudis",
    "ambit",
    "tipus_centre",
    "flux",
    "temps_ors_min",
    "distancia_ors_km",
    "classe_temps",
    "x_ori_cap",
    "y_ori_cap",
    "x_des_cap",
    "y_des_cap",
]

fluxos_net = fluxos[camps_fluxos].copy()

# Convertir les coordenades UTM dels caps municipals a longitud/latitud
punts_origen = gpd.GeoSeries(
    gpd.points_from_xy(
        fluxos_net["x_ori_cap"],
        fluxos_net["y_ori_cap"],
    ),
    crs="EPSG:25831",
).to_crs("EPSG:4326")

punts_desti = gpd.GeoSeries(
    gpd.points_from_xy(
        fluxos_net["x_des_cap"],
        fluxos_net["y_des_cap"],
    ),
    crs="EPSG:25831",
).to_crs("EPSG:4326")

fluxos_net["lon_origen"] = punts_origen.x
fluxos_net["lat_origen"] = punts_origen.y
fluxos_net["lon_desti"] = punts_desti.x
fluxos_net["lat_desti"] = punts_desti.y

# Eliminar les coordenades UTM, que ja no seran necessàries al visor
fluxos_net = fluxos_net.drop(
    columns=[
        "x_ori_cap",
        "y_ori_cap",
        "x_des_cap",
        "y_des_cap",
    ]
)

# Assegurar tipus numèrics
fluxos_net["flux"] = pd.to_numeric(
    fluxos_net["flux"],
    errors="coerce",
)

fluxos_net["temps_ors_min"] = pd.to_numeric(
    fluxos_net["temps_ors_min"],
    errors="coerce",
)

fluxos_net["distancia_ors_km"] = pd.to_numeric(
    fluxos_net["distancia_ors_km"],
    errors="coerce",
)

ruta_fluxos = CARPETA_WEB / "fluxos_visor.csv"

fluxos_net.to_csv(
    ruta_fluxos,
    index=False,
    encoding="utf-8-sig",
)

print(f"Fluxos exportats: {ruta_fluxos}")
print(f"Registres: {len(fluxos_net):,}")
print(
    "Àmbits disponibles:",
    sorted(fluxos_net["ambit"].dropna().unique().tolist()),
)


# ---------------------------------------------------------
# 2. Preparar els municipis
# ---------------------------------------------------------

print("\nLlegint els polígons municipals...")

municipis = gpd.read_file(
    FITXER_MUNICIPIS,
    layer="limadm_municipi",
)

municipis = municipis[
    [
        "codi5",
        "NOMMUNI",
        "NOMCOMAR",
        "geometry",
    ]
].copy()

# Simplificació lleugera per reduir el pes del visor
# Es fa abans de convertir a coordenades geogràfiques.
municipis["geometry"] = municipis.geometry.simplify(
    tolerance=50,
    preserve_topology=True,
)

municipis = municipis.to_crs("EPSG:4326")

ruta_municipis = CARPETA_WEB / "municipis.geojson"

municipis.to_file(
    ruta_municipis,
    driver="GeoJSON",
)

print(f"Municipis exportats: {ruta_municipis}")
print(f"Municipis: {len(municipis):,}")


# ---------------------------------------------------------
# 3. Preparar l'autocontenció
# ---------------------------------------------------------

print("\nLlegint la capa d'autocontenció...")

autocontencio = gpd.read_file(
    FITXER_AUTOCONTENCIO,
    layer="autocontencio_total_estudis",
)

autocontencio = autocontencio[
    [
        "codi5",
        "nom_muni",
        "alumnes_residents_total",
        "alumnes_interns",
        "autocontencio_pct",
        "estudis",
        "geometry",
    ]
].copy()

autocontencio["alumnes_externs"] = (
    autocontencio["alumnes_residents_total"]
    - autocontencio["alumnes_interns"]
)

autocontencio["mobilitat_externa_pct"] = (
    100 - autocontencio["autocontencio_pct"]
)

autocontencio["geometry"] = autocontencio.geometry.simplify(
    tolerance=50,
    preserve_topology=True,
)

autocontencio = autocontencio.to_crs("EPSG:4326")

ruta_autocontencio = (
    CARPETA_WEB / "autocontencio_total.geojson"
)

autocontencio.to_file(
    ruta_autocontencio,
    driver="GeoJSON",
)

print(f"Autocontenció exportada: {ruta_autocontencio}")
print(f"Municipis: {len(autocontencio):,}")


# ---------------------------------------------------------
# 4. Preparar els caps municipals
# ---------------------------------------------------------

print("\nLlegint els caps municipals...")

caps = gpd.read_file(
    FITXER_CAPS,
    layer="municipis_punts",
)

caps_net = caps[
    [
        "codi_mun_2",
        "municipi",
        "cap_de_mun",
        "comarca",
        "longitud",
        "latitud",
    ]
].copy()

ruta_caps = CARPETA_WEB / "caps_municipals.csv"

caps_net.to_csv(
    ruta_caps,
    index=False,
    encoding="utf-8-sig",
)

print(f"Caps municipals exportats: {ruta_caps}")
print(f"Caps municipals: {len(caps_net):,}")


# ---------------------------------------------------------
# . Preparar l'autocontenció per àmbit educatiu
# ---------------------------------------------------------
6
print("\nPreparant l'autocontenció per àmbit educatiu...")

ruta_auto_ambits = (
    CARPETA_DADES / "autocontencio_estudis_municipis.csv"
)

auto_ambits = pd.read_csv(
    ruta_auto_ambits,
    dtype={"codi_muni": str},
)

# Normalitzar el codi municipal a cinc dígits
auto_ambits["codi_muni"] = (
    auto_ambits["codi_muni"]
    .astype(str)
    .str.strip()
    .str.zfill(5)
)

# Conservar només els àmbits principals del visor
estudis_visibles = [
    "Total estudis",
    "EDUCACIÓ PRIMÀRIA",
    "EDUCACIÓ SECUNDÀRIA OBLIGATÒRIA",
    "BATXILLERAT",
    "FORMACIÓ PROFESSIONAL",
]

auto_ambits = auto_ambits[
    auto_ambits["estudis"].isin(estudis_visibles)
].copy()

# Conservar només municipis presents a la capa municipal catalana
codis_municipis = set(
    municipis["codi5"]
    .astype(str)
    .str.strip()
    .str.zfill(5)
)

auto_ambits = auto_ambits[
    auto_ambits["codi_muni"].isin(codis_municipis)
].copy()

# Crear camps complementaris
auto_ambits["alumnes_externs"] = (
    auto_ambits["alumnes_residents_total"]
    - auto_ambits["alumnes_interns"]
)

auto_ambits["mobilitat_externa_pct"] = (
    100 - auto_ambits["autocontencio_pct"]
).round(2)

ruta_auto_ambits_sortida = (
    CARPETA_WEB / "autocontencio_per_ambit.csv"
)

auto_ambits.to_csv(
    ruta_auto_ambits_sortida,
    index=False,
    encoding="utf-8-sig",
)

print(
    f"Autocontenció per àmbit exportada: "
    f"{ruta_auto_ambits_sortida}"
)

print(
    "Categories disponibles:",
    sorted(auto_ambits["estudis"].dropna().unique().tolist()),
)

print(f"Registres exportats: {len(auto_ambits):,}")


# ---------------------------------------------------------
# 7. Crear el contorn general de Catalunya
# ---------------------------------------------------------

print("\nCreant el contorn general de Catalunya...")

contorn = municipis.dissolve()

contorn = contorn[["geometry"]].copy()
contorn["nom"] = "Catalunya"

ruta_contorn = CARPETA_WEB / "catalunya_contorn.geojson"

contorn.to_file(
    ruta_contorn,
    driver="GeoJSON",
)

print(f"Contorn exportat: {ruta_contorn}")


# ---------------------------------------------------------
# Resum final
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("PREPARACIÓ FINALITZADA CORRECTAMENT")
print(f"Carpeta de sortida: {CARPETA_WEB}")
print("=" * 70)
