import streamlit as st
import pandas as pd
import numpy as np
import pgeocode
import pydeck as pdk
import calendar

st.set_page_config(layout="wide")


# LAND SELECTIE


st.sidebar.header("Instellingen")

land = st.sidebar.selectbox(
    "Selecteer land",
    ["United States", "United Kingdom"]
)

if land == "United States":
    bestand = "us.csv"
    country_code = "us"
    zoom_level = 4
    currency_symbol = "$"
else:
    bestand = "uk_cleaned.csv"
    country_code = "gb"
    zoom_level = 5
    currency_symbol = "£"


# DATA INLADEN


df = pd.read_csv(bestand)

df["Created at"] = pd.to_datetime(df["Created at"], errors="coerce", utc=True)

if df["Created at"].dt.tz is not None:
    df["Created at"] = df["Created at"].dt.tz_localize(None)

df["Jaar"] = df["Created at"].dt.year
df["Maand"] = df["Created at"].dt.month

df["Subtotal"] = pd.to_numeric(df["Subtotal"], errors="coerce")


# FILTERS


st.sidebar.header("Filters")

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
    (df["Maand"].isin(gekozen_maanden)) &
    (df["Jaar"].isin(gekozen_jaren))
]

if df_filtered.empty:
    st.warning("Geen data beschikbaar voor deze filters.")
    st.stop()


# BAR CHART


subtotaal = (
    df_filtered
    .groupby("Maand")["Subtotal"]
    .sum()
    .reset_index()
)

subtotaal["Maand"] = subtotaal["Maand"].apply(
    lambda x: calendar.month_name[int(x)]
)

st.subheader(f"Subtotaal per maand - {land}")
st.bar_chart(subtotaal.set_index("Maand"))


# ZIP DATA


zip_data = (
    df_filtered
    .groupby("Shipping Zip")["Subtotal"]
    .sum()
    .reset_index()
)

zip_data = zip_data.dropna(subset=["Shipping Zip"])
zip_data["Shipping Zip"] = zip_data["Shipping Zip"].astype(str)

if zip_data.empty:
    st.warning("Geen postcode data beschikbaar.")
    st.stop()


# GEOCODING (met caching)


@st.cache_data
def geocode_zipcodes(zips, country):
    nomi = pgeocode.Nominatim(country)
    result = []
    for z in zips:
        info = nomi.query_postal_code(z)
        result.append((info.latitude, info.longitude))
    return result

coords = geocode_zipcodes(zip_data["Shipping Zip"], country_code)

zip_data["latitude"] = [c[0] for c in coords]
zip_data["longitude"] = [c[1] for c in coords]

zip_data = zip_data.dropna(subset=["latitude", "longitude"])

if zip_data.empty:
    st.error("Postcodes konden niet geocode worden.")
    st.stop()


# KLEUR & RADIUS


max_omzet = zip_data["Subtotal"].max()

zip_data["color_intensity"] = zip_data["Subtotal"] / max_omzet

zip_data["color"] = zip_data["color_intensity"].apply(
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
    zoom=zoom_level,
)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={
        "html": "<b>Postcode:</b> {Shipping Zip}<br/><b>Omzet:</b> ${Subtotal}",
        "style": {"backgroundColor": "black", "color": "white"}
    }
)





# ======================
# BAR CHART PER STAD
# ======================

if "Shipping City" in df_filtered.columns:

    city_data = (
        df_filtered
        .groupby("Shipping City")["Subtotal"]
        .sum()
        .reset_index()
        .sort_values("Subtotal", ascending=False)
    )

    city_data = city_data.dropna(subset=["Shipping City"])

    if not city_data.empty:

        st.subheader("Omzet per Stad")

        weergave_optie = st.radio(
            "Selecteer weergave:",
            ["Top 10 steden", "Alle steden"],
            horizontal=True
        )

        if weergave_optie == "Top 10 steden":
            city_display = city_data.head(10)
        else:
            city_display = city_data

        st.bar_chart(city_display.set_index("Shipping City"))

    else:
        st.warning("Geen stad data beschikbaar.")

else:
    st.warning("Kolom 'Shipping City' niet gevonden in dataset.")


st.subheader(f"Omzet per Postcode - {land}")
st.pydeck_chart(deck)

