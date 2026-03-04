import streamlit as st
import pandas as pd
import numpy as np
import pgeocode
import pydeck as pdk

st.set_page_config(layout="wide")

# ------------------ DATA INLADEN ------------------

file = "wholesale_cleaned.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(file, encoding="utf-8")
    df.columns = df.columns.str.strip()
    return df

df = load_data()

# ------------------ DATUM VERWERKEN ------------------

df["Created at"] = pd.to_datetime(
    df["Created at"], errors="coerce", utc=True
).dt.tz_localize(None)

df["Jaar"] = df["Created at"].dt.year
df["Maand"] = df["Created at"].dt.month
df["Subtotal"] = pd.to_numeric(df["Subtotal"], errors="coerce").fillna(0)

# ------------------ SIDEBAR FILTERS ------------------

st.sidebar.header("Filters")

st.sidebar.markdown("""
**Seizoen codes**

- **2703** = Patta X Havaianas Green  
- **90** = Patta X Havaianas Black  
- **FS25 / FSS25** = Fem line  
- **NOOS** = Underwear (incl Fem line)
""")

gekozen_jaren = st.sidebar.multiselect(
    "Selecteer jaar(en)",
    sorted(df["Jaar"].dropna().unique()),
    sorted(df["Jaar"].dropna().unique())
)

df_jaar = df[df["Jaar"].isin(gekozen_jaren)]

seizoenen = sorted(df_jaar["Seizoen"].dropna().unique())

gekozen_seizoen = st.sidebar.multiselect(
    "Selecteer seizoen(en)",
    seizoenen,
    seizoenen
)

df_filtered = df[
    (df["Jaar"].isin(gekozen_jaren)) &
    (df["Seizoen"].isin(gekozen_seizoen))
]

if df_filtered.empty:
    st.warning("Geen data voor gekozen filters.")
    st.stop()

# ------------------ KPI ------------------

totale_verkoop = df_filtered["Subtotal"].sum()

st.markdown("## Totale verkoop")

st.metric("Totale omzet", f"€ {totale_verkoop:,.2f}")

# ------------------ OMZET PER LAND ------------------

land_omzet = (
    df_filtered
    .groupby("Shipping Country")["Subtotal"]
    .sum()
    .reset_index()
    .sort_values("Subtotal", ascending=False)
)

land_omzet = land_omzet.rename(columns={
    "Shipping Country": "Land",
    "Subtotal": "Totale omzet (€)"
})

st.subheader("Omzet per land")
st.dataframe(land_omzet, use_container_width=True)

# ------------------ ZIP DATA ------------------

zip_data = (
    df_filtered
    .groupby(
        ["Shipping Country", "Shipping Zip", "Shipping Company"],
        as_index=False
    )["Subtotal"]
    .sum()
)

# ------------------ POSTCODE CLEANING ------------------

zip_data["Shipping Zip"] = (
    zip_data["Shipping Zip"]
    .astype(str)
    .str.upper()
    .str.strip()
    .str.replace(" ", "")
    .str.replace("-", "")
)

# ------------------ GEOCODING ------------------

@st.cache_data(show_spinner="Geocoding postcodes...")
def geocode_global_fast(data):

    results = []

    for country, group in data.groupby("Shipping Country"):

        try:
            nomi = pgeocode.Nominatim(country.lower())

            unique_zips = group["Shipping Zip"].unique()

            geo = nomi.query_postal_code(unique_zips)

            geo = geo[["postal_code", "latitude", "longitude"]]

            geo = geo.rename(columns={"postal_code": "Shipping Zip"})

            merged = group.merge(geo, on="Shipping Zip", how="left")

            results.append(merged)

        except:
            continue

    if not results:
        data["latitude"] = np.nan
        data["longitude"] = np.nan
        return data

    final = pd.concat(results)

    if "latitude" not in final.columns:
        final["latitude"] = np.nan
    if "longitude" not in final.columns:
        final["longitude"] = np.nan

    return final

zip_data = geocode_global_fast(zip_data)

# ------------------ FALLBACK VOOR LANDEN ZONDER POSTCODE ------------------

country_centers = {
    "AE": [25.2048, 55.2708],
    "SG": [1.3521, 103.8198],
    "HK": [22.3193, 114.1694],
    "BR": [-14.2350, -51.9253],
    "CA": [56.1304, -106.3468]
}

for country, coords in country_centers.items():

    mask = (
        (zip_data["Shipping Country"] == country) &
        (zip_data["latitude"].isna())
    )

    zip_data.loc[mask, "latitude"] = coords[0]
    zip_data.loc[mask, "longitude"] = coords[1]

zip_data = zip_data.dropna(subset=["latitude", "longitude"])

# ------------------ OMZET FORMATTEREN ------------------

zip_data["Omzet_fmt"] = zip_data["Subtotal"].apply(lambda x: f"{x:,.2f}")

# ------------------ KLEUR SCHAAL ------------------

def omzet_kleur(waarde):

    if waarde <= 10000:
        return [0, 200, 0, 180]
    elif waarde <= 20000:
        return [255, 255, 0, 180]
    elif waarde <= 30000:
        return [255, 165, 0, 180]
    elif waarde <= 50000:
        return [255, 0, 0, 180]
    else:
        return [128, 0, 128, 180]

zip_data["color"] = zip_data["Subtotal"].apply(omzet_kleur)

zip_data["radius"] = np.sqrt(zip_data["Subtotal"]) * 250

# ------------------ KAART ZOOM ------------------

lat = 20
lon = 0
zoom = 1.3

# ------------------ LEGENDA ------------------

st.subheader("Omzet schaal")

col1, col2, col3, col4, col5 = st.columns(5)

col1.markdown("🟢 **€0 – €10.000**")
col2.markdown("🟡 **€10.000 – €20.000**")
col3.markdown("🟠 **€20.000 – €30.000**")
col4.markdown("🔴 **€30.000 – €50.000**")
col5.markdown("🟣 **€50.000+**")

# ------------------ KAART ------------------

layer = pdk.Layer(
    "ScatterplotLayer",
    data=zip_data,
    get_position='[longitude, latitude]',
    get_radius="radius",
    get_fill_color="color",
    pickable=True,
)

view_state = pdk.ViewState(
    latitude=lat,
    longitude=lon,
    zoom=zoom,
)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={
        "html": "<b>Land:</b> {Shipping Country}<br/>"
                "<b>Postcode:</b> {Shipping Zip}<br/>"
                "<b>Bedrijf:</b> {Shipping Company}<br/>"
                "<b>Omzet:</b> €{Omzet_fmt}",
        "style": {"backgroundColor": "black", "color": "white"}
    }
)

st.subheader("Wereldwijde omzet per land")

st.pydeck_chart(deck)

# ------------------ WINKELS PER LAND ------------------

st.subheader("Winkels per land")

landen_lijst = sorted(df_filtered["Shipping Country"].dropna().unique())

gekozen_land = st.selectbox(
    "Kies een land",
    landen_lijst
)

df_land = df_filtered[df_filtered["Shipping Country"] == gekozen_land]

winkel_omzet = (
    df_land
    .groupby("Shipping Company")["Subtotal"]
    .sum()
    .reset_index()
    .sort_values("Subtotal", ascending=False)
)

winkel_omzet = winkel_omzet.rename(columns={
    "Shipping Company": "Winkel",
    "Subtotal": "Omzet (€)"
})

winkel_omzet["Omzet (€)"] = winkel_omzet["Omzet (€)"].apply(lambda x: f"€ {x:,.2f}")

st.dataframe(
    winkel_omzet,
    use_container_width=True
)

# ------------------ TOTAAL OMZET LAND ------------------

totaal_land = df_land["Subtotal"].sum()

st.metric(
    f"Totaal omzet {gekozen_land}",
    f"€ {totaal_land:,.2f}"
)
