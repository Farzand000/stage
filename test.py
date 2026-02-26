import streamlit as st
import pandas as pd
import numpy as np
import pgeocode
import pydeck as pdk
import calendar

st.set_page_config(layout="wide")


# DATA INLADEN


us = pd.read_csv("us.csv")
uk = pd.read_csv("uk_cleaned.csv")

us["Country"] = "US"
uk["Country"] = "UK"

df = pd.concat([us, uk], ignore_index=True)


# DATUM VERWERKEN


df["Created at"] = pd.to_datetime(df["Created at"], errors="coerce", utc=True)

if df["Created at"].dt.tz is not None:
    df["Created at"] = df["Created at"].dt.tz_localize(None)

df["Jaar"] = df["Created at"].dt.year
df["Maand"] = df["Created at"].dt.month

df["Subtotal"] = pd.to_numeric(df["Subtotal"], errors="coerce")


# FILTERS


st.sidebar.header("Filters")

gekozen_land = st.sidebar.multiselect(
    "Selecteer land",
    options=df["Country"].unique(),
    default=df["Country"].unique()
)

gekozen_maanden = st.sidebar.multiselect(
    "Selecteer maand(en)",
    options=sorted(df["Maand"].dropna().unique()),
    default=sorted(df["Maand"].dropna().unique())
)

gekozen_jaren = st.sidebar.multiselect(
    "Selecteer Jaar(en)",
    options=sorted(df["Jaar"].dropna().unique()),
    default=sorted(df["Jaar"].dropna().unique())
)

df_filtered = df[
    (df["Country"].isin(gekozen_land)) &
    (df["Maand"].isin(gekozen_maanden)) &
    (df["Jaar"].isin(gekozen_jaren))
]

if df_filtered.empty:
    st.warning("Geen data voor gekozen filters.")
    st.stop()


# BAR CHART


subtotaal = (
    df_filtered
    .groupby("Maand")["Subtotal"]
    .sum()
    .reset_index()
)

subtotaal["Maand"] = subtotaal["Maand"].apply(lambda x: calendar.month_name[int(x)])

st.subheader("Subtotaal per maand")
st.bar_chart(subtotaal.set_index("Maand"))


# ZIP / POSTCODE DATA


zip_data = (
    df_filtered
    .groupby(["Country", "Shipping Zip"])["Subtotal"]
    .sum()
    .reset_index()
)

zip_data = zip_data.dropna(subset=["Shipping Zip"])
zip_data["Shipping Zip"] = zip_data["Shipping Zip"].astype(str)


# GEOCODING (US + UK)


@st.cache_data
def geocode_data(data):
    nomi_us = pgeocode.Nominatim("us")
    nomi_uk = pgeocode.Nominatim("gb")

    latitudes = []
    longitudes = []

    for _, row in data.iterrows():
        if row["Country"] == "US":
            info = nomi_us.query_postal_code(row["Shipping Zip"])
        else:
            info = nomi_uk.query_postal_code(row["Shipping Zip"])

        latitudes.append(info.latitude)
        longitudes.append(info.longitude)

    data["latitude"] = latitudes
    data["longitude"] = longitudes

    return data

zip_data = geocode_data(zip_data)

zip_data = zip_data.dropna(subset=["latitude", "longitude"])

if zip_data.empty:
    st.error("Postcodes konden niet geocode worden.")
    st.stop()


# KLEUR & RADIUS


max_omzet = zip_data["Subtotal"].max()

zip_data["intensity"] = zip_data["Subtotal"] / max_omzet

zip_data["color"] = zip_data["intensity"].apply(
    lambda x: [255, int(255 * (1 - x)), 0, 180]
)

zip_data["radius"] = np.sqrt(zip_data["Subtotal"]) * 200


# KAART


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
    zoom=4,
)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={
        "html": "<b>Land:</b> {Country}<br/>"
                "<b>Postcode:</b> {Shipping Zip}<br/>"
                "<b>Omzet:</b> ${Subtotal}",
        "style": {"backgroundColor": "black", "color": "white"}
    }
)

st.subheader("Omzet per Postcode (US + UK)")
st.pydeck_chart(deck)