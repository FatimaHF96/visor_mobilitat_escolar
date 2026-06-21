# Visor de mobilitat escolar a Catalunya

## Execució local

1. Obre Anaconda Prompt.
2. Activa l'entorn:

   conda activate mobilidade

3. Entra a la carpeta del projecte:

   cd "C:\\Users\\byfat\\OneDrive\\Documents\\2n Q master\\TFM\\visor_mobilitat_escolar"

4. Executa:

   streamlit run app.py

El fitxer `ors_api_key.txt` ha de ser a l'arrel del projecte i no s'ha de publicar.

## Publicació amb Streamlit Community Cloud

1. Puja el projecte a GitHub.
2. No pugis `ors_api_key.txt`.
3. A la configuració de secrets de l'aplicació afegeix:

   ORS_API_KEY = "LA_TEVA_CLAU"

4. Selecciona `app.py` com a fitxer principal.
5. Streamlit instal·larà les dependències de `requirements.txt`.

## Recomanació per a la defensa

Conserva les dues opcions:

- versió local estable;
- versió web publicada.

Abans de la defensa, comprova la versió local i guarda captures dels quatre modes.
