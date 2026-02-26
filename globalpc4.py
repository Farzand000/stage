import streamlit as st
import pandas as pd
import numpy as np
import pgeocode
import pydeck as pdk
import calendar

st.set_page_config(layout="wide")

# ------------------ DATA INLADEN ------------------

@st.cache_data
def load_data():
    return pd.read_csv("global_mainline_pc4.csv")

df = load_data()

# ------------------ DATUM VERWERKEN ------------------

df["Created at"] = pd.to_datetime(df["Created at"], errors="coerce", utc=True).dt.tz_localize(None)
df["Jaar"] = df["Created at"].dt.year
df["Maand"] = df["Created at"].dt.month
df["Subtotal"] = pd.to_numeric(df["Subtotal"], errors="coerce")

# ------------------ FILTERS ------------------

st.sidebar.header("Filters")

gekozen_land = st.sidebar.multiselect(
    "Selecteer land",
    options=sorted(df["Shipping Country"].dropna().unique()),
    default=sorted(df["Shipping Country"].dropna().unique())
)

gekozen_maanden = st.sidebar.multiselect(
    "Selecteer maand(en)",
    sorted(df["Maand"].dropna().unique()),
    sorted(df["Maand"].dropna().unique())
)

gekozen_jaren = st.sidebar.multiselect(
    "Selecteer Jaar(en)",
    sorted(df["Jaar"].dropna().unique()),
    sorted(df["Jaar"].dropna().unique())
)

df_filtered = df[
    (df["Shipping Country"].isin(gekozen_land)) &
    (df["Maand"].isin(gekozen_maanden)) &
    (df["Jaar"].isin(gekozen_jaren))
]

if df_filtered.empty:
    st.warning("Geen data voor gekozen filters.")
    st.stop()

# ------------------ SUBTOTAAL PER MAAND ------------------

subtotaal = (
    df_filtered.groupby("Maand")["Subtotal"]
    .sum()
    .reset_index()
    .sort_values("Maand")
)

subtotaal["MaandNaam"] = subtotaal["Maand"].apply(
    lambda x: calendar.month_name[int(x)]
)

maand_volgorde = list(calendar.month_name)[1:]

subtotaal["MaandNaam"] = pd.Categorical(
    subtotaal["MaandNaam"],
    categories=maand_volgorde,
    ordered=True
)

subtotaal = subtotaal.sort_values("MaandNaam")

st.subheader("Subtotaal per maand")
st.bar_chart(subtotaal.set_index("MaandNaam")["Subtotal"])

# ------------------ ZIP DATA ------------------

zip_data = (
    df_filtered
    .groupby(["Shipping Country", "Shipping Zip"])["Subtotal"]
    .sum()
    .reset_index()
    .dropna()
)

zip_data["Shipping Zip"] = (
    zip_data["Shipping Zip"]
    .astype(str)
    .str.strip()
    .str.split("-").str[0]
)

# ------------------ GLOBAL GEOCODING ------------------

# @st.cache_data
# def geocode_global(data):

#     latitudes = []
#     longitudes = []

#     for _, row in data.iterrows():

#         country_code = str(row["Shipping Country"]).lower()

#         try:
#             nomi = pgeocode.Nominatim(country_code)
#             info = nomi.query_postal_code(row["Shipping Zip"])

#             latitudes.append(info.latitude)
#             longitudes.append(info.longitude)

#         except:
#             latitudes.append(None)
#             longitudes.append(None)

#     data["latitude"] = latitudes
#     data["longitude"] = longitudes

#     return data.dropna(subset=["latitude", "longitude"])


# zip_data = geocode_global(zip_data)

# if zip_data.empty:
#     st.error("Geen postcodes konden wereldwijd geocode worden.")
#     st.stop()

@st.cache_data(show_spinner="Geocoding postcodes...")
def geocode_global_fast(data):

    results = []

    # per land groeperen
    for country, group in data.groupby("Shipping Country"):

        country_code = str(country).lower()

        try:
            nomi = pgeocode.Nominatim(country_code)

            # unieke postcodes per land
            unique_zips = group["Shipping Zip"].unique()

            geo = nomi.query_postal_code(unique_zips)

            geo = geo[["postal_code", "latitude", "longitude"]]
            geo = geo.rename(columns={"postal_code": "Shipping Zip"})

            merged = group.merge(geo, on="Shipping Zip", how="left")

            results.append(merged)

        except:
            continue

    final = pd.concat(results)
    return final.dropna(subset=["latitude", "longitude"])

zip_data = geocode_global_fast(zip_data)

if zip_data.empty:
    st.error("Geen postcodes konden wereldwijd geocode worden.")
    st.stop()


# ------------------ KLEUR & RADIUS ------------------

max_omzet = zip_data["Subtotal"].max()

zip_data["intensity"] = zip_data["Subtotal"] / max_omzet

# zip_data["color"] = zip_data["intensity"].apply(
#     lambda x: [255, int(255 * (1 - x)), 0, 180]
# )
zip_data["color"] = zip_data["intensity"].apply(
    lambda x: 
        [0, 255, 0, 180] if x < 0.25 else          # Groen
        [255, 255, 0, 180] if x < 0.5 else         # Geel
        [255, 0, 0, 180] if x < 0.75 else          # Rood
        [128, 0, 128, 180]                         # Paars
)
zip_data["radius"] = np.sqrt(zip_data["Subtotal"]) * 25 # Groter voor wereldkaart. Hoe hoger het getal, hoe groter de radius gaat zijn

# ------------------ WERELDKAART ------------------

layer = pdk.Layer(
    "ScatterplotLayer",
    data=zip_data,
    get_position='[longitude, latitude]',
    get_radius="radius",
    get_fill_color="color",
    pickable=True,
)

view_state = pdk.ViewState(
    latitude=20,
    longitude=0,
    zoom=1.3,
)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={
        "html": "<b>Land:</b> {Shipping Country}<br/>"
                "<b>Postcode:</b> {Shipping Zip}<br/>"
                "<b>Omzet:</b> ${Subtotal}",
        "style": {"backgroundColor": "black", "color": "white"}
    }
)

st.subheader("Wereldwijde omzet per postcode")
st.pydeck_chart(deck)