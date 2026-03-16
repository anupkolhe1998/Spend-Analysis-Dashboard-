import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Spend Analysis Dashboard", page_icon="💰", layout="wide")

@st.cache_data
def load_data(url):
    df = pd.read_excel(url)
    df.columns = df.columns.str.strip()
    df["PO.Date"] = pd.to_datetime(df["PO.Date"])
    return df

st.sidebar.header("Refresh")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

sheet_url = "https://docs.google.com/spreadsheets/d/1Rw_KMZh09GFx4clY-X6DEDh5z5Ikv0hW/export?format=xlsx"
df = load_data(sheet_url)

st.sidebar.header("Filters")

categories = ["All"] + sorted(df["Category"].dropna().unique())
selected_category = st.sidebar.selectbox("Category", categories)

if selected_category != "All":
    suppliers = ["All"] + sorted(df[df["Category"] == selected_category]["Name"].dropna().unique())
else:
    suppliers = ["All"] + sorted(df["Name"].dropna().unique())

selected_supplier = st.sidebar.selectbox("Supplier", suppliers)

min_date = df["PO.Date"].min().date()
max_date = df["PO.Date"].max().date()
date_range = st.sidebar.date_input("Date Range", [min_date, max_date])

filtered_df = df.copy()

if selected_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == selected_category]

if selected_supplier != "All":
    filtered_df = filtered_df[filtered_df["Name"] == selected_supplier]

if len(date_range) == 2:
    filtered_df = filtered_df[
        (filtered_df["PO.Date"].dt.date >= date_range[0]) &
        (filtered_df["PO.Date"].dt.date <= date_range[1])
    ]

total_spend = filtered_df["Amt"].sum()
total_orders = filtered_df["P.O.No."].nunique()
total_suppliers = filtered_df["Name"].nunique()
avg_order_value = filtered_df.groupby("P.O.No.")["Amt"].sum().mean()

st.title("Spend Analysis Dashboard FY 25-26")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Spend", f"₹{total_spend:,.0f}")
col2.metric("Total Orders", total_orders)
col3.metric("Suppliers", total_suppliers)
col4.metric("Avg Order Value", f"₹{avg_order_value:,.0f}")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Spend by Category")
    category_spend = filtered_df.groupby("Category")["Amt"].sum().reset_index().sort_values("Amt", ascending=False)
    fig = px.pie(category_spend, values="Amt", names="Category")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Top 10 Suppliers")
    supplier_spend = filtered_df.groupby("Name")["Amt"].sum().reset_index().sort_values("Amt", ascending=False).head(10)
    fig = px.bar(supplier_spend, x="Amt", y="Name", orientation="h")
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Monthly Spend")
    filtered_df = filtered_df.copy()
    filtered_df["Month"] = filtered_df["PO.Date"].dt.to_period("M").astype(str)
    monthly = filtered_df.groupby("Month")["Amt"].sum().reset_index()
    fig = px.line(monthly, x="Month", y="Amt", markers=True)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Spend by PO Series")
    series_spend = filtered_df.groupby("PO Series")["Amt"].sum().reset_index().sort_values("Amt", ascending=False)
    fig = px.bar(series_spend, x="PO Series", y="Amt")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Transactions")
st.dataframe(filtered_df[["PO.Date", "P.O.No.", "Category", "Name", "Description", "PoQty-PU", "Rate", "Amt"]], use_container_width=True)

csv = filtered_df.to_csv(index=False)
st.download_button("Download Filtered Data", csv, "spend_analysis.csv", "text/csv")
