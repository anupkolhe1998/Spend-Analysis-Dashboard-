import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Spend Analysis Dashboard", page_icon="💰", layout="wide")

# --- custom styling to match the screenshot layout ---
st.markdown(
    """
    <style>
    /* Hide default Streamlit menu / footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Global font / background */
    .reportview-container .main {
        background-color: #f7f9ff;
    }

    /* Header */
    .app-header {
        background: linear-gradient(90deg, #0570e6 0%, #0093ff 100%);
        padding: 18px 24px;
        border-radius: 12px;
        color: white;
        margin-bottom: 18px;
    }
    .app-header h1 {
        margin: 0;
        font-size: 28px;
        letter-spacing: 0.4px;
    }

    /* Cards */
    .metric-card {
        background: white;
        border: 1px solid #dfe3ea;
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
        min-height: 100px;
    }
    .metric-card h3 {
        margin: 0 0 6px 0;
        color: #5a5a5a;
        font-size: 14px;
        letter-spacing: 0.4px;
    }
    .metric-card .value {
        font-size: 28px;
        font-weight: 700;
        margin: 0;
    }

    /* Category panel */
    .category-panel {
        background: white;
        border: 1px solid #dfe3ea;
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

@st.cache_data
def load_data(url):
    df = pd.read_excel(url)
    df.columns = df.columns.str.strip()
    df["PO.Date"] = pd.to_datetime(df["PO.Date"])
    return df

# --- Data load and refresh ---
if "refresh" not in st.session_state:
    st.session_state["refresh"] = 0

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.session_state["refresh"] += 1

sheet_url = "https://docs.google.com/spreadsheets/d/1Rw_KMZh09GFx4clY-X6DEDh5z5Ikv0hW/export?format=xlsx"
df = load_data(sheet_url)

# --- Filters ---
categories = ["All"] + sorted(df["Category"].dropna().unique())

if "selected_category" not in st.session_state:
    st.session_state["selected_category"] = "All"

if "selected_supplier" not in st.session_state:
    st.session_state["selected_supplier"] = "All"

if "date_range" not in st.session_state:
    min_date = df["PO.Date"].min().date()
    max_date = df["PO.Date"].max().date()
    st.session_state["date_range"] = [min_date, max_date]

# Synchronize suppliers based on selected category
if st.session_state["selected_category"] != "All":
    suppliers = ["All"] + sorted(
        df[df["Category"] == st.session_state["selected_category"]]["Name"].dropna().unique()
    )
else:
    suppliers = ["All"] + sorted(df["Name"].dropna().unique())

# Helper to format INR values in K/Cr
def format_inr(value):
    if value >= 1_00_00_000:
        return f"₹{value/1_00_00_000:.2f} Cr"
    if value >= 1_00_000:
        return f"₹{value/1_00_000:.2f} Lakh"
    if value >= 1_000:
        return f"₹{value/1_000:.1f}K"
    return f"₹{value:,.0f}"

# --- Layout ---
st.markdown(
    """
    <div class="app-header">
        <h1>KEPL Procurement Analysis FY 25-26</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# Filters row
filter_col1, filter_col2, filter_col3 = st.columns([1.2, 1.2, 2.6])
with filter_col1:
    st.markdown("**Supplier Name**")
    st.session_state["selected_supplier"] = st.selectbox(
        "",
        suppliers,
        index=suppliers.index(st.session_state["selected_supplier"]) if st.session_state["selected_supplier"] in suppliers else 0,
        key="supplier_filter",
        label_visibility="collapsed",
    )

with filter_col2:
    st.markdown("**Category**")
    st.session_state["selected_category"] = st.selectbox(
        "",
        categories,
        index=categories.index(st.session_state["selected_category"]) if st.session_state["selected_category"] in categories else 0,
        key="category_filter",
        label_visibility="collapsed",
    )

with filter_col3:
    st.markdown("**Date Range**")
    st.session_state["date_range"] = st.date_input(
        "",
        value=st.session_state["date_range"],
        key="date_filter",
        label_visibility="collapsed",
    )

# Apply filters
filtered_df = df.copy()
if st.session_state["selected_category"] != "All":
    filtered_df = filtered_df[filtered_df["Category"] == st.session_state["selected_category"]]

if st.session_state["selected_supplier"] != "All":
    filtered_df = filtered_df[filtered_df["Name"] == st.session_state["selected_supplier"]]

if len(st.session_state["date_range"]) == 2:
    filtered_df = filtered_df[
        (filtered_df["PO.Date"].dt.date >= st.session_state["date_range"][0])
        & (filtered_df["PO.Date"].dt.date <= st.session_state["date_range"][1])
    ]

# Top metrics
total_spend = filtered_df["Amt"].sum()
total_orders = filtered_df["P.O.No."].nunique()
total_suppliers = filtered_df["Name"].nunique()
avg_order_value = filtered_df.groupby("P.O.No.")["Amt"].sum().mean()

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    st.markdown(
        """
        <div class='metric-card'>
            <h3>Total No. of PO</h3>
            <p class='value'>{}</p>
        </div>
        """.format(f"{total_orders:,}"),
        unsafe_allow_html=True,
    )

with metric_col2:
    st.markdown(
        """
        <div class='metric-card'>
            <h3>Amt INR</h3>
            <p class='value'>{}</p>
        </div>
        """.format(format_inr(total_spend)),
        unsafe_allow_html=True,
    )

with metric_col3:
    st.markdown(
        """
        <div class='metric-card'>
            <h3>Total Vendors</h3>
            <p class='value'>{}</p>
        </div>
        """.format(f"{total_suppliers:,}"),
        unsafe_allow_html=True,
    )

with metric_col4:
    st.markdown(
        """
        <div class='metric-card'>
            <h3>Avg Order Value</h3>
            <p class='value'>{}</p>
        </div>
        """.format(format_inr(avg_order_value or 0)),
        unsafe_allow_html=True,
    )

st.markdown("---")

# Main content: categories + charts
left_col, right_col = st.columns([1, 2])

with left_col:
    st.markdown("""
        <div class='category-panel'>
            <h4>Category</h4>
    """, unsafe_allow_html=True)

    for cat in categories[1:]:
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
