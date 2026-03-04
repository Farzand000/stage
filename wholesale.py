# import streamlit as st
# import pandas as pd
# import numpy as np
# import pgeocode
# import pydeck as pdk
# import calendar

# st.set_page_config(layout="wide")

# # ------------------ DATA INLADEN ------------------
# files=["wholesale_cleaned.csv"]
# @st.cache_data
# def load_data():
#     df = pd.read_csv(files[0], encoding="utf-8")
#     df.columns = df.columns.str.strip()
#     return df

# df = load_data()

# # ------------------ DATUM VERWERKEN ------------------

# df["Created at"] = pd.to_datetime(
#     df["Created at"], errors="coerce", utc=True
# ).dt.tz_localize(None)

# df["Jaar"] = df["Created at"].dt.year
# df["Maand"] = df["Created at"].dt.month
# df["Subtotal"] = pd.to_numeric(df["Subtotal"], errors="coerce").fillna(0)

# # ------------------ FILTERS ------------------

# st.sidebar.header("Filters")

# # gekozen_land = st.sidebar.multiselect(
# #     "Selecteer land",
# #     options=sorted(df["Shipping Country"].dropna().unique()),
# #     default=sorted(df["Shipping Country"].dropna().unique())
# # )

# gekozen_seizoen = st.sidebar.multiselect(
#     "Selecteer seizoen(en)" \
#     "\n- 2703 = Patta X Havaianas Green" \
#     "\n- 90 = Patta X Havaianas Black" \
#     "\n- FS25/FSS25 = Fem line" \
#     "\n- NOOS = Underwear (Incl Fem line)",
#     sorted(df["Seizoen"].dropna().unique()),
#     sorted(df["Seizoen"].dropna().unique())
# )

# gekozen_jaren = st.sidebar.multiselect(
#     "Selecteer Jaar(en)",
#     sorted(df["Jaar"].dropna().unique()),
#     sorted(df["Jaar"].dropna().unique())
# )

# df_filtered = df[
#     #(df["Shipping Country"].isin(gekozen_land)) 
#     (df["Seizoen"].isin(gekozen_seizoen)) &
#     (df["Jaar"].isin(gekozen_jaren))
# ]

# df_filtered = df[
#     #(df["Shipping Country"].isin(gekozen_land)) &
#     (df["Seizoen"].isin(gekozen_seizoen)) &
#     (df["Jaar"].isin(gekozen_jaren))
# ]

# if df_filtered.empty:
#     st.warning("Geen data voor gekozen filters.")
#     st.stop()



# # ------------------ TOTALE VERKOOP ------------------

# totale_verkoop = df_filtered["Subtotal"].sum()

# st.markdown("## Totale verkoop gekozen maand(en) en jaar(en)")

# st.metric(
#     label="Totale omzet",
#     value=f"€ {totale_verkoop:,.0f}"
# )

# if df_filtered.empty:
#     st.warning("Geen data voor gekozen filters.")
#     st.stop()

#     # ------------------ OMZET PER LAND ------------------

# land_omzet = (
#     df_filtered
#     .groupby("Shipping Country")["Subtotal"]
#     .sum()
#     .reset_index()
#     .sort_values("Subtotal", ascending=False)
# )

# land_omzet = land_omzet.rename(columns={
#     "Shipping Country": "Land",
#     "Subtotal": "Totale omzet (€)"
# })

# st.subheader("Omzet per land")

# st.dataframe(
#     land_omzet,
#     use_container_width=True
# )

# # ------------------ ZIP DATA + BEDRIJF ------------------

# zip_data = (
#     df_filtered
#     .groupby(
#         ["Shipping Country", "Shipping Zip", "Shipping Company"],
#         as_index=False
#     )["Subtotal"]
#     .sum()
# )

# zip_data["Shipping Zip"] = (
#     zip_data["Shipping Zip"]
#     .astype(str)
#     .str.strip()
# )

# # ------------------ GEOCODING ------------------

# @st.cache_data(show_spinner="Geocoding postcodes...")
# def geocode_global_fast(data):

#     results = []

#     for country, group in data.groupby("Shipping Country"):

#         country_code = str(country).lower()

#         try:
#             nomi = pgeocode.Nominatim(country_code)
#             unique_zips = group["Shipping Zip"].unique()
#             geo = nomi.query_postal_code(unique_zips)

#             geo = geo[["postal_code", "latitude", "longitude"]]
#             geo = geo.rename(columns={"postal_code": "Shipping Zip"})

#             merged = group.merge(geo, on="Shipping Zip", how="left")
#             results.append(merged)

#         except:
#             continue

#     if not results:
#         return pd.DataFrame()

#     final = pd.concat(results)
#     return final.dropna(subset=["latitude", "longitude"])

# zip_data = geocode_global_fast(zip_data)

# if zip_data.empty:
#     st.error("Geen postcodes konden wereldwijd geocode worden.")
#     st.stop()

# # ------------------ KLEUR & RADIUS ------------------

# max_omzet = zip_data["Subtotal"].max()
# zip_data["intensity"] = zip_data["Subtotal"] / max_omzet

# zip_data["color"] = zip_data["intensity"].apply(
#     lambda x:
#         [0, 255, 0, 180] if x < 0.25 else
#         [255, 255, 0, 180] if x < 0.5 else
#         [255, 0, 0, 180] if x < 0.75 else
#         [128, 0, 128, 180]
# )

# zip_data["radius"] = np.sqrt(zip_data["Subtotal"]) * 500

# # ------------------ WERELDKAART ------------------

# layer = pdk.Layer(
#     "ScatterplotLayer",
#     data=zip_data,
#     get_position='[longitude, latitude]',
#     get_radius="radius",
#     get_fill_color="color",
#     pickable=True,
# )

# view_state = pdk.ViewState(
#     latitude=20,
#     longitude=0,
#     zoom=1.3,
# )

# deck = pdk.Deck(
#     layers=[layer],
#     initial_view_state=view_state,
#     tooltip={
#         "html": "<b>Land:</b> {Shipping Country}<br/>"
#                 "<b>Postcode:</b> {Shipping Zip}<br/>"
#                 "<b>Bedrijf:</b> {Shipping Company}<br/>"
#                 "<b>Omzet:</b> €{Subtotal}",
#         "style": {"backgroundColor": "black", "color": "white"}
#     }
# )

# st.subheader("Wereldwijde omzet per land")
# st.pydeck_chart(deck)

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

# ------------------ JAAR FILTER ------------------

gekozen_jaren = st.sidebar.multiselect(
    "Selecteer jaar(en)",
    sorted(df["Jaar"].dropna().unique()),
    sorted(df["Jaar"].dropna().unique())
)

df_jaar = df[df["Jaar"].isin(gekozen_jaren)]

# ------------------ SEIZOEN FILTER ------------------

seizoen_labels = {
    "2703": "2703 – Patta X Havaianas Green",
    "90": "90 – Patta X Havaianas Black",
    "FS25": "FS25 – Fem line",
    "FSS25": "FSS25 – Fem line",
    "NOOS": "NOOS – Underwear"
}

seizoenen = sorted(df_jaar["Seizoen"].dropna().unique())

gekozen_seizoen = st.sidebar.multiselect(
    "Selecteer seizoen(en)",
    options=seizoenen,
    format_func=lambda x: seizoen_labels.get(x, x),
    default=seizoenen
)

# ------------------ DATA FILTER ------------------

df_filtered = df[
    (df["Jaar"].isin(gekozen_jaren)) &
    (df["Seizoen"].isin(gekozen_seizoen))
]

if df_filtered.empty:
    st.warning("Geen data voor gekozen filters.")
    st.stop()

# ------------------ TOTALE VERKOOP ------------------

totale_verkoop = df_filtered["Subtotal"].sum()

st.markdown("## Totale verkoop")

st.metric(
    label="Totale omzet",
    value=f"€ {totale_verkoop:,.2f}"
)

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

st.dataframe(
    land_omzet,
    use_container_width=True
)

# ------------------ ZIP DATA + BEDRIJF ------------------

zip_data = (
    df_filtered
    .groupby(
        ["Shipping Country", "Shipping Zip", "Shipping Company"],
        as_index=False
    )["Subtotal"]
    .sum()
)

zip_data["Shipping Zip"] = (
    zip_data["Shipping Zip"]
    .astype(str)
    .str.strip()
)

# ------------------ GEOCODING ------------------

@st.cache_data(show_spinner="Geocoding postcodes...")
def geocode_global_fast(data):

    results = []

    for country, group in data.groupby("Shipping Country"):

        country_code = str(country).lower()

        try:
            nomi = pgeocode.Nominatim(country_code)
            unique_zips = group["Shipping Zip"].unique()
            geo = nomi.query_postal_code(unique_zips)

            geo = geo[["postal_code", "latitude", "longitude"]]
            geo = geo.rename(columns={"postal_code": "Shipping Zip"})

            merged = group.merge(geo, on="Shipping Zip", how="left")
            results.append(merged)

        except:
            continue

    if not results:
        return pd.DataFrame()

    final = pd.concat(results)
    return final.dropna(subset=["latitude", "longitude"])

zip_data = geocode_global_fast(zip_data)

if zip_data.empty:
    st.error("Geen postcodes konden wereldwijd geocode worden.")
    st.stop()

# ------------------ OMZET FORMATTEREN ------------------

zip_data["Omzet_fmt"] = zip_data["Subtotal"].apply(lambda x: f"{x:,.2f}")

# ------------------ KLEUR SCHAAL ------------------

def omzet_kleur(waarde):

    if waarde <= 10000:
        return [0, 200, 0, 180]      # groen
    elif waarde <= 20000:
        return [255, 255, 0, 180]    # geel
    elif waarde <= 30000:
        return [255, 165, 0, 180]    # oranje
    elif waarde <= 40000:
        return [255, 0, 0, 180]      # rood
    else:
        return [128, 0, 128, 180]    # paars

zip_data["color"] = zip_data["Subtotal"].apply(omzet_kleur)

# Radius gebaseerd op omzet
zip_data["radius"] = np.sqrt(zip_data["Subtotal"]) * 250

# ------------------ LEGENDA ------------------

st.subheader("Omzet schaal")

col1, col2, col3, col4, col5 = st.columns(5)

col1.markdown("🟢 **€0 – €10.000**")
col2.markdown("🟡 **€10.000 – €20.000**")
col3.markdown("🟠 **€20.000 – €30.000**")
col4.markdown("🔴 **€30.000 – €40.000**")
col5.markdown("🟣 **€40.000+**")

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
                "<b>Bedrijf:</b> {Shipping Company}<br/>"
                "<b>Omzet:</b> €{Omzet_fmt}",
        "style": {"backgroundColor": "black", "color": "white"}
    }
)

st.subheader("Wereldwijde omzet per land")

st.pydeck_chart(deck)