import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="Shopify Repeat Purchase Dashboard",
    layout="wide"
)

st.title("Shopify Repeat Purchase Dashboard")

BOT_IP_THRESHOLD_PER_HOUR = 20

uploaded_files = st.file_uploader(
    "Upload Shopify CSV files",
    type="csv",
    accept_multiple_files=True
)

if uploaded_files:

    dfs = []

    for file in uploaded_files:

        df = pd.read_csv(file)

        df["Created at"] = pd.to_datetime(
            df["Created at"],
            errors="coerce",
            utc=True
        )

        dfs.append(df)

    df = pd.concat(dfs, ignore_index=True)

    st.write("Rows loaded:", len(df))

    # -------------------------
    # BASIC CLEANING
    # -------------------------

    df = df[df["Created at"].notna()]
    df = df[df["Email"].notna()]

    # remove internal emails
    emails_to_remove = [
        "customer@patta.nl",
        "customerstore@patta.nl"
    ]

    df = df[~df["Email"].str.lower().isin(emails_to_remove)]

    # remove test/bot emails
    df = df[
        ~df["Email"].astype(str).str.contains(
            r"\btest\b|\bbot\b|\bfake\b",
            case=False,
            na=False
        )
    ]

    # remove internal store orders
    if "Location" in df.columns:
        df = df[
            ~df["Location"].str.contains(
                r"^Patta\s[A-Z]{2}\s-",
                na=False
            )
        ]

    # -------------------------
    # BOT IP DETECTION
    # -------------------------

    if "IP Address" in df.columns:
        ip_col = "IP Address"
    elif "ip" in df.columns:
        ip_col = "ip"
    else:
        ip_col = None

    if ip_col:

        tmp = df.copy()
        tmp["hour"] = tmp["Created at"].dt.floor("h")

        per_hour = tmp.groupby([ip_col, "hour"]).size()

        bot_ips = per_hour[
            per_hour > BOT_IP_THRESHOLD_PER_HOUR
        ].reset_index()[ip_col].unique()

        df = df[~df[ip_col].isin(bot_ips)]

        st.write("Bot IPs removed:", len(bot_ips))

    # -------------------------
    # EMAIL NORMALISATION
    # -------------------------

    df["email_clean"] = df["Email"].astype(str).str.lower().str.strip()

    is_gmail = df["email_clean"].str.contains(
        r"@gmail\.com$|@googlemail\.com$",
        regex=True
    )

    df.loc[is_gmail, "email_clean"] = df.loc[
        is_gmail, "email_clean"
    ].str.replace(r"\+.*(?=@)", "", regex=True)

    local = df.loc[is_gmail, "email_clean"].str.replace(
        r"@gmail\.com$|@googlemail\.com$",
        "",
        regex=True
    )

    local = local.str.replace(".", "", regex=False)

    domain = df.loc[is_gmail, "email_clean"].str.extract(
        r"(@gmail\.com$|@googlemail\.com$)",
        expand=False
    )

    df.loc[is_gmail, "email_clean"] = local + domain

    # -------------------------
    # ORDER LEVEL DATA
    # -------------------------

    orders = df[
        ["Name", "email_clean", "Created at", "Shipping Country"]
    ].drop_duplicates()

    orders = orders.sort_values("Created at")

    orders = orders.drop_duplicates(
        subset=["Name"],
        keep="first"
    )

    orders = orders.sort_values(
        ["email_clean", "Created at"]
    )

    # -------------------------
    # ORDER STATS
    # -------------------------

    st.subheader("Order stats")

    st.write("Orders:", len(orders))
    st.write("Customers:", orders["email_clean"].nunique())

    # -------------------------
    # FIRST / SECOND ORDER
    # -------------------------

    orders["order_number"] = (
        orders.groupby("email_clean").cumcount() + 1
    )

    first = orders[
        orders["order_number"] == 1
    ][["email_clean", "Created at", "Shipping Country"]].rename(
        columns={
            "Created at": "first_order",
            "Shipping Country": "country"
        }
    )

    second = orders[
        orders["order_number"] == 2
    ][["email_clean", "Created at"]].rename(
        columns={"Created at": "second_order"}
    )

    merged = first.merge(second, on="email_clean", how="left")

    merged["days_to_second_order"] = (
        merged["second_order"] - merged["first_order"]
    ).dt.days

    # -------------------------
    # METRICS
    # -------------------------

    total_customers = len(merged)
    returning_customers = merged["second_order"].notna().sum()
    return_rate = returning_customers / total_customers if total_customers else 0
    median_days = merged["days_to_second_order"].median()

    within_30 = (
        merged["days_to_second_order"]
        .dropna()
        .le(30)
        .mean()
    )

    # -------------------------
    # KPI METRICS
    # -------------------------

    st.subheader("Key metrics")

    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric("Customers", total_customers)
    k2.metric("Returning", returning_customers)
    k3.metric("Return rate", f"{return_rate*100:.2f}%")
    k4.metric("Median days", round(median_days,1))
    k5.metric("Returning within 30 days", f"{within_30*100:.2f}%")

    st.divider()

    # -------------------------
    # ROW 1
    # -------------------------

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Cumulative Repeat Purchase")

        data = merged["days_to_second_order"].dropna().sort_values()

        if len(data) > 0:

            n = len(data)
            cum = (np.arange(1, n+1) / n) * 100

            plot_df = pd.DataFrame({
                "days": data,
                "cumulative_percent": cum
            })

            fig = px.area(
                plot_df,
                x="days",
                y="cumulative_percent",
                template="plotly_dark"
            )

            st.plotly_chart(fig, use_container_width=True)

    with col2:

        st.subheader("Repeat Purchase Rate by Country")

        country_stats = (
            merged
            .groupby("country")
            .agg(
                customers=("email_clean", "count"),
                returning=("second_order", lambda x: x.notna().sum())
            )
            .reset_index()
        )

        country_stats["return_rate_%"] = (
            country_stats["returning"] /
            country_stats["customers"] * 100
        )

        fig = px.bar(
            country_stats.sort_values(
                "customers",
                ascending=False
            ).head(10),
            x="country",
            y="return_rate_%",
            template="plotly_dark"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # -------------------------
    # ROW 2
    # -------------------------

    col3, col4 = st.columns(2)

    with col3:

        st.subheader("Return Distribution")

        bins = [0, 30, 60, 90, 180, 365, 9999]

        labels = [
            "0–30 days",
            "30–60 days",
            "60–90 days",
            "90–180 days",
            "180–365 days",
            "365+ days"
        ]

        merged["bucket"] = pd.cut(
            merged["days_to_second_order"],
            bins=bins,
            labels=labels
        )

        distribution = (
            merged["bucket"]
            .value_counts()
            .sort_index()
            .reset_index()
        )

        distribution.columns = [
            "Time to second order",
            "Customers"
        ]

        fig = px.bar(
            distribution,
            x="Time to second order",
            y="Customers",
            template="plotly_dark"
        )

        st.plotly_chart(fig, use_container_width=True)

    with col4:

        st.subheader("Metrics per Country")

        country_stats["median_days"] = (
            merged.groupby("country")["days_to_second_order"]
            .median()
            .values
        )

        st.dataframe(country_stats, use_container_width=True)
