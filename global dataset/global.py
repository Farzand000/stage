import streamlit as st
import pandas as pd
import numpy as np
import pgeocode
import pydeck as pdk
import calendar

st.set_page_config(layout="wide")

# ------------------ LAND SELECTIE ------------------

st.sidebar.header("Instellingen")

land = st.sidebar.selectbox(
    "Selecteer shopify store",
    ["United States", "United Kingdom", "Global"]
)

@st.cache_data
def load_data(file):
    return pd.read_csv(file)

if land == "United States":
    df = load_data("US_mainline.csv")
    zoom_level = 4
    currency_symbol = "$"

elif land == "United Kingdom":
    df = load_data("UK_mainline.csv")
    zoom_level = 5
    currency_symbol = "£"

else:  # GLOBAL
    df = load_data("global_mainline.csv")
    zoom_level = 1.3
    currency_symbol = "€"

# ------------------ DATA PREP ------------------

df["Created at"] = pd.to_datetime(df["Created at"], errors="coerce", utc=True).dt.tz_localize(None)
df["Jaar"] = df["Created at"].dt.year
df["Maand"] = df["Created at"].dt.month
df["Subtotal"] = pd.to_numeric(df["Subtotal"], errors="coerce")

# ------------------ FILTERS ------------------

st.sidebar.header("Filters")

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
    (df["Maand"].isin(gekozen_maanden)) &
    (df["Jaar"].isin(gekozen_jaren))
]

if df_filtered.empty:
    st.warning("Geen data beschikbaar voor deze filters.")
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

st.subheader(f"Subtotaal per maand - {land}")
st.bar_chart(subtotaal.set_index("MaandNaam")["Subtotal"])

# ------------------ KAART LOGICA ------------------

@st.cache_data
def geocode_global(data):

    grouped = (
        data.groupby(["Shipping Country", "Shipping Zip"])["Subtotal"]
        .sum()
        .reset_index()
        .dropna()
    )

    latitudes = []
    longitudes = []

    for _, row in grouped.iterrows():
        Country_code = str(row["Shipping Country"]).lower()
        zip_code = str(row["Shipping Zip"]).strip().split("-")[0]

        try:
            nomi = pgeocode.Nominatim( Country_code)
            info = nomi.query_postal_code(zip_code)
            latitudes.append(info.latitude)
            longitudes.append(info.longitude)
        except:
            latitudes.append(None)
            longitudes.append(None)

    grouped["latitude"] = latitudes
    grouped["longitude"] = longitudes

    return grouped.dropna()

if land == "Global":

    world_data = geocode_global(df_filtered)

    if not world_data.empty:

        max_omzet = world_data["Subtotal"].max()

        world_data["color"] = world_data["Subtotal"].apply(
            lambda x: [200, int(255 * (1 - x / max_omzet)), 0, 160]
        )

        world_data["radius"] = np.sqrt(world_data["Subtotal"]) * 50000

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=world_data,
            get_position='[longitude, latitude]',
            get_radius="radius",
            get_fill_color="color",
            pickable=True,
        )

        view_state = pdk.ViewState(
            latitude=20,
            longitude=0,
            zoom=zoom_level,
        )

        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={
                "html": f"<b>Land:</b> {{Shipping Country}}<br/><b>Omzet:</b> {currency_symbol}{{Subtotal}}",
                "style": {"backgroundColor": "black", "color": "white"}
            }
        )

        st.subheader("Global omzet kaart")
        st.pydeck_chart(deck)

    else:
        st.warning("Geen geocode data beschikbaar.")

else:
    # US of UK postcode kaart

    zip_data = (
        df_filtered.groupby("Shipping Zip")["Subtotal"]
        .sum()
        .reset_index()
        .dropna()
    )

    Country_code = "us" if land == "United States" else "gb"

    zip_data["Shipping Zip"] = (
        zip_data["Shipping Zip"]
        .astype(str)
        .str.strip()
        .str.split("-").str[0]
    )

    if  Country_code == "us":
        zip_data["Shipping Zip"] = zip_data["Shipping Zip"].str[:5]

    nomi = pgeocode.Nominatim( Country_code)
    coords = nomi.query_postal_code(zip_data["Shipping Zip"])

    zip_data["latitude"] = coords["latitude"]
    zip_data["longitude"] = coords["longitude"]
    zip_data = zip_data.dropna()

    if not zip_data.empty:

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
            zoom=4,
        )

        deck = pdk.Deck(layers=[layer], initial_view_state=view_state)

        st.subheader(f"Omzet per Postcode - {land}")
        st.pydeck_chart(deck)

