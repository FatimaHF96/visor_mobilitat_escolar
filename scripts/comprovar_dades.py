from pathlib import Path

import geopandas as gpd

try:
    import pyogrio
except ImportError:
    pyogrio = None


# Carpeta principal del proyecto
CARPETA_PROJECTE = Path(__file__).resolve().parent.parent
CARPETA_DADES = CARPETA_PROJECTE / "dades"

FITXERS = [
    "linies_od_25_26_estudis_caps_amb_temps_ors.gpkg",
    "autocontencio_estudis_municipis.gpkg",
    "caps_municipi.gpkg",
    "catalunya_contorn_final.gpkg",
    "municipis_poligons.gpkg",
]


def obtenir_capes(ruta: Path) -> list[str]:
    """Retorna les capes internes d'un GeoPackage."""
    if pyogrio is not None:
        return [fila[0] for fila in pyogrio.list_layers(ruta)]

    # Alternativa si pyogrio no està disponible
    import fiona

    return list(fiona.listlayers(ruta))


def comprovar_fitxer(nom_fitxer: str) -> None:
    ruta = CARPETA_DADES / nom_fitxer

    print("\n" + "=" * 90)
    print(f"FITXER: {nom_fitxer}")
    print(f"RUTA: {ruta}")

    if not ruta.exists():
        print("ERROR: el fitxer no existeix.")
        return

    try:
        capes = obtenir_capes(ruta)
        print(f"CAPES INTERNES: {capes}")

        for capa in capes:
            print("\n" + "-" * 70)
            print(f"CAPA: {capa}")

            gdf = gpd.read_file(ruta, layer=capa)

            print(f"Nombre de registres: {len(gdf):,}")
            print(f"CRS: {gdf.crs}")
            print(f"Tipus de geometria: {gdf.geom_type.unique().tolist()}")
            print("Camps:")
            for camp in gdf.columns:
                print(f"  - {camp}")

            print("\nPrimers 3 registres:")
            print(gdf.drop(columns="geometry", errors="ignore").head(3).to_string())

    except Exception as error:
        print(f"ERROR EN LLEGIR EL FITXER: {error}")


def main() -> None:
    print(f"Carpeta de dades: {CARPETA_DADES}")

    if not CARPETA_DADES.exists():
        print("ERROR: no existeix la carpeta 'dades'.")
        return

    for fitxer in FITXERS:
        comprovar_fitxer(fitxer)

    print("\n" + "=" * 90)
    print("COMPROVACIÓ FINALITZADA")


if __name__ == "__main__":
    main()

