#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Spend‑Analysis Dashboard – Power BI‑style Streamlit app.

Features
--------
* Sidebar slicers (Category, Supplier, Date)
* KPI cards with delta vs. previous period
* Cross‑filtering by clicking on Plotly charts
* Drill‑through to an interactive Ag‑Grid table
* Tabs for Overview / Trends / Details
* Data refresh & CSV/Excel export
"""

import streamlit as st
import pandas as pd
import plotly.express as px

# Optional helper for click-to-filter; not required to run the dashboard.
try:
    from streamlit_plotly_events import plotly_events
except ModuleNotFoundError:
    def plotly_events(fig, click_event=False, hover_event=False, key=None):
        """Fallback when streamlit-plotly-events isn't installed."""
        return []

from st_aggrid import AgGrid, GridOptionsBuilder
from io import BytesIO
from datetime import date, timedelta

# ----------------------------------------------------------------------
# 1️⃣ Page configuration & global CSS
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Spend Analysis Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hide Streamlit's default menu/footer + custom card styling
st.markdown(
    """
    <style>
    #MainMenu, footer {visibility: hidden;}
    .main .block-container {padding-top: 0rem;}
    .app-header {
        background: linear-gradient(90deg, #0570e6 0%, #0093ff 100%);
        padding: 1.5rem 2rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 1.2rem;
    }
    .app-header h1 {margin:0;font-size:2rem;letter-spacing:1px;}

    /* Top-row selects (filters) */
    .stSelectbox > div:first-child,
    .stDateInput > div:first-child {
        border: 1px solid #1976d2 !important;
        border-radius: 10px !important;
        padding: 0.4rem 0.6rem !important;
        background: #fff !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    }
    .stSelectbox label, .stDateInput label {
        font-weight: 600;
        color: #333;
        margin-bottom: 0.25rem;
    }

    .kpi-card {
        background: white; border:1px solid #1976d2; border-radius:12px;
        padding:1rem 1.2rem; box-shadow:0 2px 10px rgba(0,0,0,.05);
    }
    .kpi-card h3 {margin:0;font-size:.95rem;color:#555;}
    .kpi-card .value {font-size:1.8rem;font-weight:600;margin-top:.3rem;}

    /* Category panel */
    .category-panel {
        background: white;
        border: 1px solid #1976d2;
        border-radius: 12px;
        padding: 16px;
        height: 100%;
    }
    .category-panel h4 {
        margin-top: 0;
        font-size: 16px;
        letter-spacing: 0.4px;
    }
    .category-button {
        display: block;
        width: 100%;
        padding: 10px 12px;
        margin-bottom: 8px;
        border: 1px solid #1976d2;
        border-radius: 10px;
        background: transparent;
        color: #0b3c68;
        text-align: left;
        font-weight: 600;
        cursor: pointer;
    }
    .category-button.selected {
        background: #e7f2ff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# 2️⃣ Helper functions
# ----------------------------------------------------------------------
@st.cache_data(ttl=3600)       # refresh at most once per hour (or click ↻)
def load_data(url: str) -> pd.DataFrame:
    """Load the Excel sheet from Google Drive → clean column names → parse dates."""
    df = pd.read_excel(url, engine="openpyxl")
    df.columns = df.columns.str.strip()
    # Expect column name “PO.Date” – adjust if needed
    df["PO.Date"] = pd.to_datetime(df["PO.Date"], errors="coerce")
    return df


def format_inr(val: float) -> str:
    """Compact INR formatting – Cr / Lakh / K."""
    if pd.isna(val):
        return "₹0"
    if val >= 1_00_00_000:
        return f"₹{val/1_00_00_000:,.2f} Cr"
    if val >= 1_00_000:
        return f"₹{val/1_00_000:,.2f} Lakh"
    if val >= 1_000:
        return f"₹{val/1_000:,.1f} K"
    return f"₹{val:,.0f}"


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Filter based on the 3 sidebar slicers stored in session_state."""
    dff = df.copy()

    # Category filter
    if st.session_state.selected_category != "All":
        dff = dff[dff["Category"] == st.session_state.selected_category]

    # Supplier filter
    if st.session_state.selected_supplier != "All":
        dff = dff[dff["Name"] == st.session_state.selected_supplier]

    # Date range filter (two‑element list)
    if isinstance(st.session_state.date_range, list) and len(st.session_state.date_range) == 2:
        start, end = st.session_state.date_range
        dff = dff[(dff["PO.Date"].dt.date >= start) & (dff["PO.Date"].dt.date <= end)]

    return dff


def get_prev_period(df: pd.DataFrame, date_range: list) -> pd.DataFrame:
    """Return a slice representing the period immediately before the current selection."""
    start, end = date_range
    # length of current window
    delta = end - start
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - delta
    mask = (df["PO.Date"].dt.date >= prev_start) & (df["PO.Date"].dt.date <= prev_end)
    return df.loc[mask]

# ----------------------------------------------------------------------
# 3️⃣ Load data (once per session, refreshable)
# ----------------------------------------------------------------------
SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/1Rw_KMZh09GFx4clY-X6DEDh5z5Ikv0hW/export?"
    "format=xlsx"
)
raw_df = load_data(SHEET_URL)

# ----------------------------------------------------------------------
# 4️⃣ Initialise session_state (run only once)
# ----------------------------------------------------------------------
if "selected_category" not in st.session_state:
    st.session_state.selected_category = "All"
if "selected_supplier" not in st.session_state:
    st.session_state.selected_supplier = "All"
if "date_range" not in st.session_state:
    min_date = raw_df["PO.Date"].min().date()
    max_date = raw_df["PO.Date"].max().date()
    st.session_state.date_range = [min_date, max_date]

# ----------------------------------------------------------------------
# 5️⃣ Top filters (no sidebar) + refresh
# ----------------------------------------------------------------------
refresh_col, title_col = st.columns([1, 11])
with refresh_col:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.experimental_rerun()

with title_col:
    st.markdown(
        """
        <div class="app-header">
            <h1>KEPL Procurement Analysis ‑ FY 25‑26</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Filter + KPI row (top of layout)
col_sup, col_cat, col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(
    [1.5, 1.5, 1.2, 1.2, 1.2, 1.2]
)

# Supplier (single‑select)
all_suppliers = ["All"] + sorted(raw_df["Name"].dropna().unique())
st.session_state.selected_supplier = col_sup.selectbox(
    "Supplier Name",
    all_suppliers,
    index=all_suppliers.index(st.session_state.selected_supplier),
    key="top_supplier",
)

# Category (single‑select)
all_categories = ["All"] + sorted(raw_df["Category"].dropna().unique())
st.session_state.selected_category = col_cat.selectbox(
    "Category",
    all_categories,
    index=all_categories.index(st.session_state.selected_category),
    key="top_category",
)

# Apply filters (for KPI + chart computation)
filtered_df = apply_filters(raw_df)

total_pos = filtered_df["P.O.No."].nunique()
total_spend = filtered_df["Amt"].sum()
total_vendors = filtered_df["Name"].nunique()
avg_order = (
    filtered_df.groupby("P.O.No.")["Amt"]
    .sum()
    .mean()
    if not filtered_df.empty else 0
)

# Update KPI cards
col_kpi1.markdown(
    f"""
    <div class="kpi-card">
        <h3>Total No. of PO</h3>
        <p class="value">{total_pos:,}</p>
    </div>
    """,
    unsafe_allow_html=True,
)
col_kpi2.markdown(
    f"""
    <div class="kpi-card">
        <h3>Amt INR</h3>
        <p class="value">{format_inr(total_spend)}</p>
    </div>
    """,
    unsafe_allow_html=True,
)
col_kpi3.markdown(
    f"""
    <div class="kpi-card">
        <h3>Total Vendors</h3>
        <p class="value">{total_vendors:,}</p>
    </div>
    """,
    unsafe_allow_html=True,
)
col_kpi4.markdown(
    f"""
    <div class="kpi-card">
        <h3>Avg Order Value</h3>
        <p class="value">{format_inr(avg_order)}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# ----------------------------------------------------------------------
# 8️⃣ Main area – category list + charts
# ----------------------------------------------------------------------
left_col, right_col = st.columns([1, 2])

with left_col:
    st.markdown("""
        <div class='category-panel'>
            <h4>Category</h4>
    """, unsafe_allow_html=True)

    for cat in all_categories[1:]:
        selected_cls = "selected" if cat == st.session_state["selected_category"] else ""
        if st.button(cat, key=f"cat_{cat}"):
            st.session_state["selected_category"] = cat
            st.session_state["selected_supplier"] = "All"
            st.experimental_rerun()
        st.markdown(
            f"<div class='category-button {selected_cls}'>{cat}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Top 10 Suppliers by Purchase Value")
        supplier_spend = (
            filtered_df.groupby("Name")["Amt"].sum().reset_index().sort_values("Amt", ascending=False).head(10)
        )
        fig = px.bar(supplier_spend, x="Amt", y="Name", orientation="h")
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(t=30, l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        st.subheader("Category wise Distribution")
        category_spend = (
            filtered_df.groupby("Category")["Amt"].sum().reset_index().sort_values("Amt", ascending=False)
        )
        fig = px.pie(category_spend, values="Amt", names="Category", hole=0.3)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("Transactions")
st.dataframe(
    filtered_df[
        [
            "PO.Date",
            "P.O.No.",
            "Category",
            "Name",
            "Description",
            "PoQty-PU",
            "Rate",
            "Discount",
            "Discounted Rate",
            "Amt",
        ]
    ],
    use_container_width=True,
)

csv = filtered_df.to_csv(index=False)
st.download_button("Download Filtered Data", csv, "spend_analysis.csv", "text/csv")
