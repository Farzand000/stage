import streamlit as st
import pandas as pd
import numpy as np
import pgeocode
import pydeck as pdk
import calendar
from streamlit_autorefresh import st_autorefresh

# ------------------ CONFIG ------------------

st.set_page_config(layout="wide")
st_autorefresh(interval=1000, key="refresh")

LAND_CONFIG = {
    "United States": {"file": "us.csv", "code": "us", "zoom": 4, "currency": "$"},
    "United Kingdom": {"file": "uk_cleaned.csv", "code": "gb", "zoom": 5, "currency": "£"},
}

st.sidebar.header("Instellingen")
land = st.sidebar.selectbox("Selecteer land", LAND_CONFIG.keys())
config = LAND_CONFIG[land]

# ------------------ DATA ------------------

df = pd.read_csv(config["file"])

df["Created at"] = (
    pd.to_datetime(df["Created at"], errors="coerce", utc=True)
      .dt.tz_localize(None)
)

df["Jaar"] = df["Created at"].dt.year
df["Maand"] = df["Created at"].dt.month
df["Subtotal"] = pd.to_numeric(df["Subtotal"], errors="coerce")

# ------------------ FILTERS ------------------

st.sidebar.header("Filters")

maanden = sorted(df["Maand"].dropna().unique())
jaren = sorted(df["Jaar"].dropna().unique())

gekozen_maanden = st.sidebar.multiselect("Maanden", maanden, maanden)
gekozen_jaren = st.sidebar.multiselect("Jaren", jaren, jaren)

df = df[df["Maand"].isin(gekozen_maanden) & df["Jaar"].isin(gekozen_jaren)]

if df.empty:
    st.warning("Geen data beschikbaar voor deze filters.")
    st.stop()

# ------------------ BAR CHART MAAND ------------------

subtotaal = (
    df.groupby("Maand")["Subtotal"]
      .sum()
      .reset_index()
)

subtotaal["Maand"] = subtotaal["Maand"].apply(lambda x: calendar.month_name[int(x)])

st.subheader(f"Subtotaal per maand - {land}")
st.bar_chart(subtotaal.set_index("Maand"))

# ------------------ ZIP DATA ------------------

zip_data = (
    df.groupby("Shipping Zip")["Subtotal"]
      .sum()
      .dropna()
      .reset_index()
)

zip_data["Shipping Zip"] = zip_data["Shipping Zip"].astype(str)

if zip_data.empty:
    st.warning("Geen postcode data beschikbaar.")
    st.stop()

# ------------------ GEOCODING ------------------

@st.cache_data
def geocode(zips, country):
    nomi = pgeocode.Nominatim(country)
    coords = nomi.query_postal_code(zips)
    return coords[["latitude", "longitude"]]

coords = geocode(zip_data["Shipping Zip"], config["code"])
zip_data = pd.concat([zip_data, coords], axis=1).dropna()

if zip_data.empty:
    st.error("Postcodes konden niet geocode worden.")
    st.stop()

# ------------------ MAP STYLE ------------------

max_omzet = zip_data["Subtotal"].max()

zip_data["color"] = zip_data["Subtotal"].apply(
    lambda x: [255, int(255 * (1 - x / max_omzet)), 0, 180]
)

zip_data["radius"] = np.sqrt(zip_data["Subtotal"]) * 200

layer = pdk.Layer(
    "ScatterplotLayer",
    data=zip_data,
    get_position='[longitude, latitude]',
    get_radius="radius",
    get_fill_color="color",
    pickable=True,
)

view_state = pdk.ViewState(
    latitude=zip_data["latitude"].mean(),
    longitude=zip_data["longitude"].mean(),
    zoom=config["zoom"],
)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={
        "html": f"<b>Postcode:</b> {{Shipping Zip}}<br/><b>Omzet:</b> {config['currency']}{{Subtotal}}",
        "style": {"backgroundColor": "black", "color": "white"},
    },
)

# ------------------ STEDEN ------------------

if "Shipping City" in df.columns:

    city_data = (
        df.groupby("Shipping City")["Subtotal"]
          .sum()
          .dropna()
          .reset_index()
    )

    if not city_data.empty:

        st.subheader(f"Omzet per Stad ({config['currency']})")

        col1, col2 = st.columns(2)

        with col1:
            weergave = st.radio("Weergave:", ["Top 10", "Alles"])

        with col2:
            sorteer = st.selectbox(
                "Sorteer op:",
                ["Omzet ↓", "Omzet ↑", "A → Z", "Z → A"]
            )

        sort_map = {
            "Omzet ↓": ("Subtotal", False),
            "Omzet ↑": ("Subtotal", True),
            "A → Z": ("Shipping City", True),
            "Z → A": ("Shipping City", False),
        }

        col_sort, asc = sort_map[sorteer]
        city_data = city_data.sort_values(col_sort, ascending=asc)

        if weergave == "Top 10":
            city_data = city_data.head(10)

        st.bar_chart(city_data.set_index("Shipping City"))

    else:
        st.warning("Geen stad data beschikbaar.")

else:
    st.warning("Kolom 'Shipping City' niet gevonden.")

# ------------------ MAP ------------------

st.subheader(f"Omzet per Postcode - {land}")
st.pydeck_chart(deck)