# Import python packages
import os

import streamlit as st

try:
    from snowflake.snowpark import Session
    from snowflake.snowpark.functions import col
except Exception:
    Session = None
    col = None

st.set_page_config(page_title="Adam Smoothies", page_icon="🥤", layout="centered")


def _read_secret(key: str, env_name: str) -> str:
    try:
        secrets = st.secrets.get("snowflake", {})
    except Exception:
        secrets = {}

    value = secrets.get(key) or os.getenv(env_name, "")
    return str(value).strip() if value is not None else ""


def _create_session():
    if Session is None or col is None:
        return None, "demo"

    host = _read_secret("host", "SNOWFLAKE_HOST")
    account = _read_secret("account", "SNOWFLAKE_ACCOUNT")

    config = {
        "user": _read_secret("user", "SNOWFLAKE_USER"),
        "password": _read_secret("password", "SNOWFLAKE_PASSWORD"),
        "role": _read_secret("role", "SNOWFLAKE_ROLE"),
        "warehouse": _read_secret("warehouse", "SNOWFLAKE_WAREHOUSE"),
        "database": _read_secret("database", "SNOWFLAKE_DATABASE"),
        "schema": _read_secret("schema", "SNOWFLAKE_SCHEMA"),
    }

    if host:
        config["host"] = host
    elif account:
        config["account"] = account

    required = ["user", "password", "warehouse"]
    if not all(config.get(key) for key in required) or not (host or account):
        return None, "demo"

    try:
        session = Session.builder.configs({k: v for k, v in config.items() if v}).create()
        return session, "snowflake"
    except Exception as exc:
        st.warning(f"Connexion Snowflake impossible : {exc}")
        return None, "demo"


DEFAULT_FRUITS = [
    "Banane",
    "Fraise",
    "Mangue",
    "Ananas",
    "Kiwi",
    "Orange",
]


st.title("Adam Smoothies")
st.caption("Créez votre smoothie personnalisé en quelques clics.")
st.markdown("Choisissez vos fruits, donnez un nom à votre commande et envoyez-la.")

col_left, col_right = st.columns([1.2, 0.8], gap="large")

with col_left:
    name_on_order = st.text_input("Nom sur la commande", placeholder="Ex. Alex")

with col_right:
    st.markdown("### État")
    st.caption("Le mode démo fonctionne sans identifiants Snowflake.")

session = None
fruit_options = DEFAULT_FRUITS
fruit_table = [{"FRUIT_NAME": fruit, "SEARCH_ON": fruit} for fruit in DEFAULT_FRUITS]
mode = "demo"
status_label = "Mode démo"

session, mode = _create_session()

if mode == "snowflake" and session is not None:
    try:
        fruit_rows = session.table("smoothies.public.fruit_options").select(col("FRUIT_NAME"), col("SEARCH_ON")).collect()
        fruit_options = [row["SEARCH_ON"] if row.get("SEARCH_ON") else row["FRUIT_NAME"] for row in fruit_rows]
        fruit_table = [
            {"FRUIT_NAME": row["FRUIT_NAME"], "SEARCH_ON": row.get("SEARCH_ON") or row["FRUIT_NAME"]}
            for row in fruit_rows
        ]
        status_label = "Connexion Snowflake"
    except Exception as exc:
        st.warning(f"Impossible de lire la table Snowflake : {exc}")
        fruit_options = DEFAULT_FRUITS
        fruit_table = [{"FRUIT_NAME": fruit, "SEARCH_ON": fruit} for fruit in DEFAULT_FRUITS]
        mode = "demo"
        status_label = "Mode démo"

st.info(f"État actuel : {status_label} — la liste affichée est {'en direct Snowflake' if mode == 'snowflake' else 'locale'}.")

INGREDIENTS_LIST = st.multiselect(
    "Choisissez jusqu’à 5 ingrédients :",
    fruit_options,
    max_selections=5,
    help="Vous pouvez sélectionner entre 1 et 5 fruits.",
)

if INGREDIENTS_LIST:
    ingredients_string = " ".join(INGREDIENTS_LIST)
    customer_name = name_on_order.strip() or "Client"

    st.progress(min(len(INGREDIENTS_LIST), 5) / 5, text=f"{len(INGREDIENTS_LIST)} fruit(s) sélectionné(s) sur 5")

    preview = st.container(border=True)
    with preview:
        st.write(f"**Commande de {customer_name}**")
        st.write("Ingrédients : " + ingredients_string)

    my_insert_stmt = (
        "insert into smoothies.public.orders(ingredients, name_on_order) "
        f"values ('{ingredients_string}', '{customer_name}')"
    )

    time_to_insert = st.button("Valider la commande", type="primary")
    if time_to_insert:
        if mode == "snowflake" and session is not None:
            session.sql(my_insert_stmt).collect()
            st.success(f"Votre smoothie est commandé, {customer_name} !", icon="✅")
        else:
            st.info("Commande simulée en mode démo. Connectez l’application à Snowflake pour enregistrer la commande.")
else:
    st.caption("Sélectionnez au moins un fruit pour voir l’aperçu de votre commande.")

st.subheader("Liste des fruits disponibles")
st.dataframe(fruit_table, width="stretch", hide_index=True)
