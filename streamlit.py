import streamlit as st
import pandas as pd
import numpy as np
import pgeocode
import pydeck as pdk
import calendar

st.set_page_config(layout="wide")


# DATA


df = pd.read_csv("US_mainline.csv")

df["Created at"] = pd.to_datetime(df["Created at"], errors="coerce", utc=True)

if df["Created at"].dt.tz is not None:
    df["Created at"] = df["Created at"].dt.tz_localize(None)

df["Jaar"] = df["Created at"].dt.year
df["Maand"] = df["Created at"].dt.month

# Zorg dat Subtotal numeriek is
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

subtotaal["Maand"] = subtotaal["Maand"].apply(lambda x: calendar.month_name[int(x)])

st.subheader("Subtotaal per maand")
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
    st.warning("Geen zipcode data beschikbaar.")
    st.stop()


# GEOCODING (met caching)


@st.cache_data
def geocode_zipcodes(zips):
    nomi = pgeocode.Nominatim("us")
    result = []
    for z in zips:
        info = nomi.query_postal_code(z)
        result.append((info.latitude, info.longitude))
    return result

coords = geocode_zipcodes(zip_data["Shipping Zip"])

zip_data["latitude"] = [c[0] for c in coords]
zip_data["longitude"] = [c[1] for c in coords]

zip_data = zip_data.dropna(subset=["latitude", "longitude"])

if zip_data.empty:
    st.error("Zipcodes konden niet geocode worden.")
    st.stop()


# KLEUR & RADIUS


max_omzet = zip_data["Subtotal"].max()

zip_data["color_intensity"] = zip_data["Subtotal"] / max_omzet

zip_data["color"] = zip_data["color_intensity"].apply(
    lambda x: [255, int(255 * (1 - x)), 0, 180]
)

# Radius schalen zodat hij niet absurd groot wordt
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
        "html": "<b>Zip:</b> {Shipping Zip}<br/><b>Omzet:</b> ${Subtotal}",
        "style": {"backgroundColor": "black", "color": "white"}
    }
)

st.subheader("Omzet per Zipcode")
st.pydeck_chart(deck)

st.bar_chart(subtotaal.set_index("Maand"))
st.subheader("Verkochte items")

# st.dataframe(
#     df_filtered[[
#         "Created at",
#         "Lineitem name",
#         "Shipping Zip",
#         "Subtotal"
#     ]].sort_values("Created at", ascending=False),
#     use_container_width=True
# )

# top_items = (
#     df_filtered
#     .groupby("Lineitem name")["Subtotal"]
#     .sum()
#     .reset_index()
#     .sort_values("Subtotal", ascending=False)
# )

# st.subheader("Omzet per product")
# st.bar_chart(top_items.set_index("Lineitem name"))

top_items = (
    df_filtered
    .groupby(["Maand", "Lineitem name"])["Subtotal"]
    .sum()
    .reset_index()
)

# Maand naam toevoegen
top_items["Maand"] = top_items["Maand"].apply(
    lambda x: calendar.month_name[int(x)]
)

st.subheader("Omzet per product per maand")

st.dataframe(top_items.sort_values(["Maand", "Subtotal"], ascending=[True, False]))