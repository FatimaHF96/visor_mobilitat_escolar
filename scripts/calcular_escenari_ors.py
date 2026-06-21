from pathlib import Path
import time

import pandas as pd
import requests


# ---------------------------------------------------------
# Rutes del projecte
# ---------------------------------------------------------

CARPETA_PROJECTE = Path(__file__).resolve().parent.parent
CARPETA_DADES_WEB = CARPETA_PROJECTE / "dades_web"
CARPETA_RESULTATS = CARPETA_PROJECTE / "resultats"

FITXER_CLAU_ORS = CARPETA_PROJECTE / "ors_api_key.txt"
FITXER_FLUXOS = CARPETA_DADES_WEB / "fluxos_visor.csv"
FITXER_CAPS = CARPETA_DADES_WEB / "caps_municipals.csv"

FITXER_CACHE = (
    CARPETA_RESULTATS / "temps_escenaris_ors.csv"
)

CARPETA_RESULTATS.mkdir(
    parents=True,
    exist_ok=True,
)


# ---------------------------------------------------------
# Configuració ORS
# ---------------------------------------------------------

URL_MATRIX = (
    "https://api.openrouteservice.org/"
    "v2/matrix/driving-car"
)

MIDA_BLOC = 40
PAUSA_ENTRE_PETICIONS = 1.0
MAX_INTENTS = 5
ESPERA_INICIAL_429 = 20


# ---------------------------------------------------------
# Funcions auxiliars
# ---------------------------------------------------------

def llegir_clau_ors() -> str:
    if not FITXER_CLAU_ORS.exists():
        raise FileNotFoundError(
            "No existeix el fitxer ors_api_key.txt "
            "a la carpeta principal del projecte."
        )

    clau = FITXER_CLAU_ORS.read_text(
        encoding="utf-8"
    ).strip()

    if not clau:
        raise ValueError(
            "El fitxer ors_api_key.txt està buit."
        )

    return clau


def carregar_caps() -> pd.DataFrame:
    caps = pd.read_csv(
        FITXER_CAPS,
        dtype={"codi_mun_2": str},
    )

    caps["codi_mun_2"] = (
        caps["codi_mun_2"]
        .astype(str)
        .str.strip()
        .str.zfill(5)
    )

    caps["longitud"] = pd.to_numeric(
        caps["longitud"],
        errors="coerce",
    )

    caps["latitud"] = pd.to_numeric(
        caps["latitud"],
        errors="coerce",
    )

    caps = caps.dropna(
        subset=[
            "codi_mun_2",
            "longitud",
            "latitud",
        ]
    )

    return caps


def carregar_cache() -> pd.DataFrame:
    if not FITXER_CACHE.exists():
        return pd.DataFrame(
            columns=[
                "ori_cod",
                "nou_centre_cod",
                "temps_nou_min",
                "distancia_nova_km",
            ]
        )

    cache = pd.read_csv(
        FITXER_CACHE,
        dtype={
            "ori_cod": str,
            "nou_centre_cod": str,
        },
    )

    cache["ori_cod"] = (
        cache["ori_cod"]
        .astype(str)
        .str.strip()
        .str.zfill(5)
    )

    cache["nou_centre_cod"] = (
        cache["nou_centre_cod"]
        .astype(str)
        .str.strip()
        .str.zfill(5)
    )

    return cache


def guardar_cache(cache: pd.DataFrame) -> None:
    cache = cache.drop_duplicates(
        subset=[
            "ori_cod",
            "nou_centre_cod",
        ],
        keep="last",
    )

    cache.to_csv(
        FITXER_CACHE,
        index=False,
        encoding="utf-8-sig",
    )


# ---------------------------------------------------------
# Càlcul amb ORS
# ---------------------------------------------------------

def calcular_temps_cap_nou_centre(
    codis_origen: list[str],
    codi_nou_centre: str,
) -> pd.DataFrame:
    """
    Calcula el temps i la distància des de diversos
    caps municipals fins al cap municipal proposat
    per al nou centre.

    Els resultats es guarden en una memòria cau CSV.
    """

    clau_ors = llegir_clau_ors()
    caps = carregar_caps()
    cache = carregar_cache()

    codis_origen = [
        str(codi).strip().zfill(5)
        for codi in codis_origen
    ]

    codi_nou_centre = (
        str(codi_nou_centre)
        .strip()
        .zfill(5)
    )

    # Evitar calcular origen = nou centre
    codis_origen = [
        codi
        for codi in codis_origen
        if codi != codi_nou_centre
    ]

    # Resultats ja disponibles a la cache
    claus_cache = set(
        zip(
            cache["ori_cod"],
            cache["nou_centre_cod"],
        )
    )

    codis_pendents = [
        codi
        for codi in codis_origen
        if (
            codi,
            codi_nou_centre,
        ) not in claus_cache
    ]

    if not codis_pendents:
        return cache[
            (
                cache["ori_cod"].isin(
                    codis_origen
                )
            )
            & (
                cache["nou_centre_cod"]
                == codi_nou_centre
            )
        ].copy()

    caps_indexats = caps.set_index(
        "codi_mun_2"
    )

    if codi_nou_centre not in caps_indexats.index:
        raise ValueError(
            "No s'ha trobat el cap municipal "
            f"del municipi {codi_nou_centre}."
        )

    centre = caps_indexats.loc[
        codi_nou_centre
    ]

    coordenada_centre = [
        float(centre["longitud"]),
        float(centre["latitud"]),
    ]

    headers = {
        "Authorization": clau_ors,
        "Content-Type": "application/json",
    }

    nous_resultats = []

    total_blocs = (
        len(codis_pendents)
        + MIDA_BLOC
        - 1
    ) // MIDA_BLOC

    for numero_bloc, inici in enumerate(
        range(
            0,
            len(codis_pendents),
            MIDA_BLOC,
        ),
        start=1,
    ):
        bloc_codis = codis_pendents[
            inici:inici + MIDA_BLOC
        ]

        bloc_caps = caps_indexats.loc[
            caps_indexats.index.intersection(
                bloc_codis
            )
        ].copy()

        # Respectar l'ordre original del bloc
        bloc_caps = bloc_caps.reindex(
            [
                codi
                for codi in bloc_codis
                if codi in bloc_caps.index
            ]
        )

        codis_valids = bloc_caps.index.tolist()

        coordenades_origen = [
            [
                float(fila["longitud"]),
                float(fila["latitud"]),
            ]
            for _, fila in bloc_caps.iterrows()
        ]

        # Els orígens ocupen les primeres posicions.
        # El nou centre és l'última localització.
        locations = (
            coordenades_origen
            + [coordenada_centre]
        )

        index_centre = len(locations) - 1

        payload = {
            "locations": locations,
            "sources": list(
                range(len(coordenades_origen))
            ),
            "destinations": [index_centre],
            "metrics": [
                "duration",
                "distance",
            ],
            "units": "m",
        }

        print(
            f"Bloc {numero_bloc}/{total_blocs}: "
            f"{len(codis_valids)} orígens"
        )

        resposta = None

        for intent in range(1, MAX_INTENTS + 1):
            try:
                resposta = requests.post(
                    URL_MATRIX,
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
            except requests.RequestException as error:
                if intent == MAX_INTENTS:
                    raise RuntimeError(
                        "No s'ha pogut connectar amb ORS "
                        f"després de {MAX_INTENTS} intents: {error}"
                    ) from error

                espera = ESPERA_INICIAL_429 * intent

                print(
                    "Error temporal de connexió amb ORS. "
                    f"Nou intent en {espera} segons..."
                )

                time.sleep(espera)
                continue

            if resposta.status_code == 200:
                break

            if resposta.status_code == 429:
                if intent == MAX_INTENTS:
                    raise RuntimeError(
                        "ORS continua indicant que s'ha superat "
                        "el límit temporal de peticions després de "
                        f"{MAX_INTENTS} intents."
                    )

                retry_after = resposta.headers.get(
                    "Retry-After"
                )

                if retry_after is not None:
                    try:
                        espera = max(
                            int(float(retry_after)),
                            1,
                        )
                    except ValueError:
                        espera = (
                            ESPERA_INICIAL_429
                            * intent
                        )
                else:
                    espera = (
                        ESPERA_INICIAL_429
                        * intent
                    )

                print(
                    "ORS ha assolit temporalment el límit "
                    "de peticions (error 429). "
                    f"Nou intent en {espera} segons..."
                )

                time.sleep(espera)
                continue

            if 500 <= resposta.status_code < 600:
                if intent == MAX_INTENTS:
                    raise RuntimeError(
                        "Error temporal del servidor ORS "
                        f"{resposta.status_code} després de "
                        f"{MAX_INTENTS} intents: "
                        f"{resposta.text}"
                    )

                espera = 10 * intent

                print(
                    "ORS ha retornat un error temporal "
                    f"{resposta.status_code}. "
                    f"Nou intent en {espera} segons..."
                )

                time.sleep(espera)
                continue

            raise RuntimeError(
                "Error ORS "
                f"{resposta.status_code}: "
                f"{resposta.text}"
            )

        if resposta is None or resposta.status_code != 200:
            raise RuntimeError(
                "No s'ha obtingut una resposta correcta d'ORS."
            )

        dades = resposta.json()

        duracions = dades.get(
            "durations",
            [],
        )

        distancies = dades.get(
            "distances",
            [],
        )

        for posicio, codi_origen in enumerate(
            codis_valids
        ):
            duracio_s = None
            distancia_m = None

            if (
                posicio < len(duracions)
                and duracions[posicio]
            ):
                duracio_s = (
                    duracions[posicio][0]
                )

            if (
                posicio < len(distancies)
                and distancies[posicio]
            ):
                distancia_m = (
                    distancies[posicio][0]
                )

            nous_resultats.append(
                {
                    "ori_cod": codi_origen,
                    "nou_centre_cod": (
                        codi_nou_centre
                    ),
                    "temps_nou_min": (
                        duracio_s / 60
                        if duracio_s is not None
                        else None
                    ),
                    "distancia_nova_km": (
                        distancia_m / 1000
                        if distancia_m is not None
                        else None
                    ),
                }
            )

        # Guardar després de cada bloc
        cache = pd.concat(
            [
                cache,
                pd.DataFrame(nous_resultats),
            ],
            ignore_index=True,
        )

        guardar_cache(cache)

        nous_resultats = []

        time.sleep(
            PAUSA_ENTRE_PETICIONS
        )

    cache = carregar_cache()

    return cache[
        (
            cache["ori_cod"].isin(
                codis_origen
            )
        )
        & (
            cache["nou_centre_cod"]
            == codi_nou_centre
        )
    ].copy()


# ---------------------------------------------------------
# Prova directa del script
# ---------------------------------------------------------

if __name__ == "__main__":
    fluxos = pd.read_csv(
        FITXER_FLUXOS,
        dtype={
            "ori_cod": str,
            "des_cod": str,
        },
    )

    fluxos["ori_cod"] = (
        fluxos["ori_cod"]
        .astype(str)
        .str.strip()
        .str.zfill(5)
    )

    # Prova amb cinc municipis d'origen
    codis_prova = (
        fluxos[
            fluxos["ambit"] == "Primària"
        ]["ori_cod"]
        .dropna()
        .drop_duplicates()
        .head(5)
        .tolist()
    )

    # Abrera
    codi_centre_prova = "08001"

    print(
        "Orígens de prova:",
        codis_prova,
    )

    print(
        "Municipi proposat:",
        codi_centre_prova,
    )

    resultat = calcular_temps_cap_nou_centre(
        codis_prova,
        codi_centre_prova,
    )

    print("\nResultat:")
    print(resultat.to_string(index=False))

