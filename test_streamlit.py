# import streamlit as st
# import pandas as pd
# import numpy as np

# st.set_page_config(page_title="Streamlit Test", page_icon="🚀")

# st.title("🚀 Streamlit Test App")
# st.write("Als je dit ziet, werkt Streamlit correct!")

# # Tekstinvoer
# name = st.text_input("Wat is je naam?")

# if name:
#     st.success(f"Hallo {name}! 🎉")

# #pick a file
# file = st.file_uploader("Pick a file")

# # Slider
# age = st.slider("Hoe oud ben je?", 0, 100, 25)
# st.write(f"Je bent {age} jaar oud.")

# # Random data grafiek
# st.subheader("📊 Random Data Grafiek")
# data = pd.DataFrame(
#     np.random.randn(20, 3),
#     columns=["A", "B", "C"]
# )

# st.line_chart(data)

# # Checkbox
# if st.checkbox("Laat de ruwe data zien"):
#     st.write(data)


# import streamlit as st
# import pandas as pd
# import seaborn as sns
# import matplotlib.pyplot as plt

# st.title("📊 Totale omzet per maand")

# # CSV uploaden
# uploaded_file = st.file_uploader("Orders", type=["csv"])

# if uploaded_file is not None:
#     df = pd.read_csv(uploaded_file)

#     # Kolom opschonen
#     df["Price: Total"] = (
#         df["Price: Total"]
#         .astype(str)
#         .str.replace(",", "")
#         .astype(float)
#     )

#     # Groeperen per maand (belangrijk!)
#     df_grouped = df.groupby("Maand", as_index=False)["Price: Total"].sum()

#     # Plot maken
#     fig, ax = plt.subplots()
#     sns.barplot(data=df_grouped, x="Maand", y="Price: Total", ax=ax)

#     ax.set_title("Totale omzet per maand")
#     ax.set_xlabel("Maand")
#     ax.set_ylabel("Totale omzet")

#     st.pyplot(fig)

#     if st.checkbox("Toon data"):
#         st.write(df_grouped)




# US


import streamlit as st
import pandas as pd
df=pd.read_csv("US_mainline.csv")
df["Created at"] = pd.to_datetime(df["Created at"], errors="coerce", utc=True)

# Alleen timezone verwijderen als het echt timezone-aware is
# if df["Created at"].dt.tz is not None:
#     df["Created at"] = df["Created at"].dt.tz_localize(None)

# df["Jaar"] = df["Created at"].dt.year
# df["Maand"] = df["Created at"].dt.month
# df["Dag"] = df["Created at"].dt.day
# Voorbeeld data
data = df

st.title("Subtotaal per maand")

# 🔹 Maand filter (multiselect)
gekozen_maanden = st.multiselect(
    "Selecteer maand(en)",
    options=sorted(df["Maand"].unique()),
    default=sorted(df["Maand"].unique())
)

# 🔹 Jaar filter (multiselect)
gekozen_jaren = st.multiselect(
    "Selecteer Jaar(en)",
    options=sorted(df["Jaar"].unique()),
    default=sorted(df["Jaar"].unique())
)
# Filter toepassen
df_filtered = df[df["Maand"].isin(gekozen_maanden)]
df_filtered = df[df["Jaar"].isin(gekozen_jaren)]

# 🔹 Subtotaal per maand
subtotaal = (
    df_filtered
    .groupby("Lineitem name")["Subtotal"]
    .sum()
    .reset_index()
)

st.subheader("Subtotaal per maand")
st.dataframe(subtotaal)