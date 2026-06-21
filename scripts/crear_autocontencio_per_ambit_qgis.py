from pathlib import Path

import geopandas as gpd
import pandas as pd


# ---------------------------------------------------------
# Rutes del projecte
# ---------------------------------------------------------

CARPETA_PROJECTE = Path(__file__).resolve().parent.parent
CARPETA_DADES = CARPETA_PROJECTE / "dades"

FITXER_MUNICIPIS = CARPETA_DADES / "municipis_poligons.gpkg"
FITXER_AUTOCONTENCIO = (
    CARPETA_DADES / "autocontencio_estudis_municipis.csv"
)

SORTIDA_GPKG = (
    CARPETA_DADES / "autocontencio_per_ambit.gpkg"
)


# ---------------------------------------------------------
# Llegir dades
# ---------------------------------------------------------

print("Llegint els polígons municipals...")

municipis = gpd.read_file(
    FITXER_MUNICIPIS,
    layer="limadm_municipi",
)

print("Llegint la taula d'autocontenció...")

autocontencio = pd.read_csv(
    FITXER_AUTOCONTENCIO,
    dtype={"codi_muni": str},
)


# ---------------------------------------------------------
# Normalitzar codis municipals
# ---------------------------------------------------------

municipis["codi5"] = (
    municipis["codi5"]
    .astype(str)
    .str.strip()
    .str.zfill(5)
)

autocontencio["codi_muni"] = (
    autocontencio["codi_muni"]
    .astype(str)
    .str.strip()
    .str.zfill(5)
)


# ---------------------------------------------------------
# Afegir indicadors complementaris
# ---------------------------------------------------------

autocontencio["alumnes_externs"] = (
    autocontencio["alumnes_residents_total"]
    - autocontencio["alumnes_interns"]
)

autocontencio["mobilitat_externa_pct"] = (
    100 - autocontencio["autocontencio_pct"]
).round(2)


# ---------------------------------------------------------
# Correspondència entre estudis i noms de capes
# ---------------------------------------------------------

capes = {
    "Total estudis": "autocontencio_total",
    "EDUCACIÓ PRIMÀRIA": "autocontencio_primaria",
    "EDUCACIÓ SECUNDÀRIA OBLIGATÒRIA": "autocontencio_eso",
    "BATXILLERAT": "autocontencio_batxillerat",
    "FORMACIÓ PROFESSIONAL": "autocontencio_fp",
}


# ---------------------------------------------------------
# Crear el GeoPackage
# ---------------------------------------------------------

if SORTIDA_GPKG.exists():
    SORTIDA_GPKG.unlink()

for valor_estudis, nom_capa in capes.items():
    print(f"\nCreant capa: {nom_capa}")

    dades_ambit = autocontencio[
        autocontencio["estudis"] == valor_estudis
    ].copy()

    capa_final = municipis.merge(
        dades_ambit,
        left_on="codi5",
        right_on="codi_muni",
        how="left",
    )

    capa_final["ambit_visor"] = valor_estudis

    capa_final.to_file(
        SORTIDA_GPKG,
        layer=nom_capa,
        driver="GPKG",
    )

    registres_amb_dades = (
        capa_final["autocontencio_pct"]
        .notna()
        .sum()
    )

    print(
        f"Municipis amb dades: "
        f"{registres_amb_dades}"
    )


print("\n" + "=" * 70)
print("GEOPACKAGE CREAT CORRECTAMENT")
print(SORTIDA_GPKG)
print("=" * 70)
