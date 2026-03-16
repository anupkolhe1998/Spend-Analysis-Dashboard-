import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import StringIO

# Page Configuration
st.set_page_config(
    page_title="KEPL Spend Analysis FY 25-26",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Executive Light UI & Mobile Optimization
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    * {
        font-family: 'Outfit', sans-serif;
    }

    /* Exempt icons from the global font override to ensure they render correctly */
    .st-emotion-cache-18ni7ap, .st-emotion-cache-1v07af9, [data-testid="stIcon"] {
        font-family: inherit !important;
    }

    /* Light Theme Foundations */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
    }
    
    /* Responsive Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
        box-shadow: 4px 0 10px rgba(0,0,0,0.02);
    }
    
    /* Sidebar Widgets */
    [data-testid="stWidgetLabel"] p {
        color: #64748b !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 10px !important;
    }
    
    /* Premium Selectbox Light Theme */
    div[data-baseweb="select"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    div[data-baseweb="select"] * {
        color: #0f172a !important;
    }

    /* Target the actual input text specifically */
    div[data-testid="stSelectbox"] div[role="button"] {
        color: #0f172a !important;
        background-color: #ffffff !important;
    }

    /* Dropdown Menus */
    div[role="listbox"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    
    div[role="listbox"] ul li {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }
    
    div[role="listbox"] ul li:hover {
        background-color: #f1f5f9 !important;
        color: #6366f1 !important;
    }

    /* KPI Card (Elevated Light Mode) */
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        transition: all 0.3s ease;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }
    
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #cbd5e1;
    }
    
    .kpi-label {
        color: #64748b;
        font-size: 10px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin-bottom: 2px;
    }
    
    .kpi-value {
        color: #0f172a;
        font-size: 34px;
        font-weight: 900;
        letter-spacing: -1px;
        line-height: 1;
    }
    
    /* Professional Headers */
    h1, h2, h3, .stSubheader {
        color: #0f172a !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px !important;
    }

    /* Mobile Adaptivity */
    @media (max-width: 768px) {
        .kpi-value {
            font-size: 28px;
        }
        .main-title {
            font-size: 20px !important;
        }
    }
    
    /* Table Styling */
    .stDataFrame {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }

    /* Ensure sidebar toggle is visible and professional */
    [data-testid="stSidebarCollapsedControl"] {
        color: #6366f1 !important;
        background-color: rgba(255, 255, 255, 0.8) !important;
        border-radius: 0 8px 8px 0 !important;
        border: 1px solid #e2e8f0 !important;
        border-left: none !important;
        top: 10px !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05) !important;
    }

    /* Hide unnecessary Streamlit elements but keep functional ones */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Data Fetching
SHEET_ID = "1Rw_KMZh09GFx4clY-X6DEDh5z5Ikv0hW"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=600, show_spinner=False)
def load_data():
    try:
        # Adding User-Agent and simplifying URL to avoid 400 errors
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(CSV_URL, headers=headers)
        if response.status_code == 200:
            df = pd.read_csv(StringIO(response.text))
            
            # Find relevant columns using deterministic matching.
            # We first try exact header matches (case-insensitive, trimmed) then fallback to substring matching.
            def find_col(patterns):
                cols = list(df.columns)
                normalized = {c.strip().lower(): c for c in cols}

                # Exact match first (cleaned, case-insensitive)
                for p in patterns:
                    key = p.strip().lower()
                    if key in normalized:
                        return normalized[key]

                # Fallback: substring match
                for p in patterns:
                    pl = p.lower()
                    for col in cols:
                        if pl in col.lower():
                            return col
                return None

            po_col = find_col(['P.O.No.', 'PO No', 'PO Number'])
            supp_col = find_col(['Supplier', 'Vendor', 'Name'])
            cat_col = find_col(['Category'])
            amt_col = find_col(['Amt', 'Amount', 'Value', 'Total'])
            
            # New columns for detailed table
            co_col = find_col(['C.O.No.'])
            item_col = find_col(['Item Cd'])
            desc_col = find_col(['Description'])
            qty_col = find_col(['PoQty-PU', 'Qty'])
            rate_col = find_col(['Rate'])
            disc_col = find_col(['Discount'])
            disc_rate_col = find_col(['Discounted Rate'])
            date_col = find_col(['Date', 'P.O.Date', 'PO Date'])
            type_col = find_col(['Type', 'Procurement Type', 'PO Type'])

            # Rename for consistency
            rename_dict = {}
            if po_col: rename_dict[po_col] = 'po_no'
            if supp_col: rename_dict[supp_col] = 'supplier'
            if cat_col: rename_dict[cat_col] = 'category'
            if amt_col: rename_dict[amt_col] = 'amount'
            if co_col: rename_dict[co_col] = 'co_no'
            if item_col: rename_dict[item_col] = 'item_cd'
            if desc_col: rename_dict[desc_col] = 'description'
            if qty_col: rename_dict[qty_col] = 'qty'
            if rate_col: rename_dict[rate_col] = 'rate'
            if disc_col: rename_dict[disc_col] = 'discount'
            if disc_rate_col: rename_dict[disc_rate_col] = 'disc_rate'
            if date_col: rename_dict[date_col] = 'po_date'
            if type_col: rename_dict[type_col] = 'proc_type'
            
            df = df.rename(columns=rename_dict)
            
            # Clean amount column - handle NaN and convert strings
            if 'amount' in df.columns:
                df['amount'] = df['amount'].astype(str).str.replace(r'[^0-9.]', '', regex=True)
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

            if 'rate' in df.columns:
                df['rate'] = df['rate'].astype(str).str.replace(r'[^0-9.]', '', regex=True)
                df['rate'] = pd.to_numeric(df['rate'], errors='coerce').fillna(0)

            if 'disc_rate' in df.columns:
                df['disc_rate'] = df['disc_rate'].astype(str).str.replace(r'[^0-9.]', '', regex=True)
                df['disc_rate'] = pd.to_numeric(df['disc_rate'], errors='coerce').fillna(0)
            
            # Clean PO column to ensure it exists and is clean
            if 'po_no' in df.columns:
                df['po_no'] = df['po_no'].astype(str).str.strip()
                
            # Parse Dates - Support Indian format DD/MM/YYYY and ensure robustness
            if 'po_date' in df.columns:
                # Try parsing with dayfirst=True for Indian formats
                df['po_date'] = pd.to_datetime(df['po_date'], dayfirst=True, errors='coerce')
                # Remove rows with invalid dates for the trend analysis
                df = df.dropna(subset=['po_date'])
                
                # Format for display (e.g., "Apr-2025")
                df['month_year'] = df['po_date'].dt.strftime('%b-%Y')
                # For chronological sorting across years
                df['month_sort'] = df['po_date'].dt.to_period('M')
                
                # Financial Year Sorting Logic (April to March)
                # We create an index where Apr=1, May=2 ... Mar=12
                df['fy_month_idx'] = df['po_date'].dt.month.map(lambda x: x - 3 if x >= 4 else x + 9)
                # Combine with year to ensure 2026 comes after 2025
                df['fy_sort_key'] = df['po_date'].dt.year * 100 + df['fy_month_idx']
            
            return df
        else:
            st.error(f"Failed to fetch data: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def format_money(val):
    if val >= 10000000: return f"₹{val/10000000:.2f}Cr"
    if val >= 100000: return f"₹{val/100000:.2f}L"
    return f"₹{val:,.2f}"

def format_count(val):
    if val >= 1000000: return f"{val/1000000:.1f}M"
    if val >= 1000: return f"{val/1000:.1f}K"
    return str(int(val))


# Dashboard Logic

# Sidebar Header + refresh control
st.sidebar.markdown(f"<h1 style='font-size: 24px; margin-bottom: 30px;'>KEPL Spend Analysis<br>FY 25-26</h1>", unsafe_allow_html=True)
if st.sidebar.button("Refresh data", key="refresh_data"):
    load_data.clear()
    st.rerun()

# Load (cached) data
df = load_data()

if df is not None:
    # Sidebar Filters
    # 1. Category Filter first
    categories = ["All"] + sorted(df['category'].dropna().unique().tolist())
    sel_category = st.sidebar.selectbox("Sector Classification", categories)
    
    # 2. Cascading Supplier Filter
    if sel_category == "All":
        filtered_for_supp = df
    else:
        filtered_for_supp = df[df['category'] == sel_category]
        
    suppliers = ["All"] + sorted(filtered_for_supp['supplier'].dropna().unique().tolist())
    sel_supplier = st.sidebar.selectbox("Vendor", suppliers)
    
    # 3. Cascading Type Filter (dependent on Category & Vendor)
    if sel_supplier == "All":
        filtered_for_type = filtered_for_supp
    else:
        filtered_for_type = filtered_for_supp[filtered_for_supp['supplier'] == sel_supplier]
        
    types = ["All"] + sorted(filtered_for_type['proc_type'].dropna().unique().tolist()) if 'proc_type' in filtered_for_type.columns else ["All"]
    sel_type = st.sidebar.selectbox("Spending Type", types)
    
    # Final Filter Data
    filtered_df = filtered_for_type.copy()
    if sel_type != "All":
        filtered_df = filtered_df[filtered_df['proc_type'] == sel_type]
        
    # Metrics Calculation
    total_spend = filtered_df['amount'].sum()
    po_count = filtered_df['po_no'].dropna().astype(str).str.strip().replace(['nan', '', 'None'], pd.NA).dropna().nunique() if 'po_no' in filtered_df.columns else 0
    vendor_count = filtered_df['supplier'].nunique() if 'supplier' in filtered_df.columns else 0
    
    # KPI Row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid #6366f1;">
                <div class="kpi-label">Total PO Issued</div>
                <div class="kpi-value">{format_count(po_count)}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid #8b5cf6;">
                <div class="kpi-label">Total PO Value</div>
                <div class="kpi-value">{format_money(total_spend)}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid #ec4899;">
                <div class="kpi-label">Total Vendors</div>
                <div class="kpi-value">{format_count(vendor_count)}</div>
            </div>
        """, unsafe_allow_html=True)

    # Charts
    chart_col1, chart_col2 = st.columns([1.5, 1])
    
    with chart_col1:
        st.subheader("Top 10 Strategic Suppliers by Spend")
        supp_data = filtered_df.groupby('supplier')['amount'].sum().sort_values(ascending=False).head(10).reset_index()
        
        # Create formatted text for the top of the bars
        supp_data['text_label'] = supp_data['amount'].apply(format_money)
        fig_supp = px.bar(
            supp_data, 
            x='supplier', y='amount',
            text='text_label',
            color='amount',
            color_continuous_scale=['#6366f1', '#8b5cf6', '#ec4899'],
            template="plotly_white"
        )
        
        # Calculate tick values for Y-axis in Indian Format
        max_val = supp_data['amount'].max()
        if max_val > 0:
            step = max_val / 5
            tick_vals = [i * step for i in range(7)]
            tick_text = [format_money(v) for v in tick_vals]
        else:
            tick_vals, tick_text = [], []

        fig_supp.update_traces(
            textposition='outside',
            textfont=dict(color='#0f172a', size=10, family="Outfit"),
            cliponaxis=False
        )
        
        fig_supp.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            coloraxis_showscale=False,
            xaxis_title=None,
            yaxis_title=None,
            margin=dict(l=20, r=20, t=30, b=80),
            font=dict(color="#0f172a", size=11),
            xaxis=dict(tickfont=dict(color="#475569")),
            yaxis=dict(
                tickvals=tick_vals,
                ticktext=tick_text,
                tickfont=dict(color="#475569"), 
                gridcolor="#f1f5f9"
            )
        )
        st.plotly_chart(fig_supp, use_container_width=True)
        
    with chart_col2:
        st.subheader("Category Spend Distribution")
        cat_data = filtered_df.groupby('category')['amount'].sum().sort_values(ascending=False).reset_index()
        fig_cat = px.pie(
            cat_data,
            values='amount', names='category',
            hole=0.6,
            color_discrete_sequence=['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f59e0b', '#10b981'],
            template="plotly_white"
        )
        fig_cat.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=80, t=10, b=10),
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05, font=dict(color="#0f172a", size=12)),
            font=dict(color="#0f172a")
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    # Trend Analysis
    st.markdown("### Strategic Spend Trajectory (FY 2025-26)")
    if 'po_date' in filtered_df.columns and not filtered_df['po_date'].isna().all():
        # Group by the sort keys to maintain chronological FY order
        trend_data = filtered_df.groupby(['fy_sort_key', 'month_year']).agg({
            'amount': 'sum'
        }).reset_index().sort_values('fy_sort_key')
        
        fig_trend = px.line(
            trend_data,
            x='month_year', y='amount',
            markers=True,
            text=trend_data['amount'].apply(format_money),
            template="plotly_white",
            color_discrete_sequence=['#6366f1']
        )
        
        fig_trend.update_traces(
            textposition='top center',
            textfont=dict(color='#0f172a', size=10),
            line=dict(width=3, shape='spline') # Smooth curve
        )
        
        # Format Y-axis for trend chart
        trend_max = trend_data['amount'].max() if not trend_data.empty else 0
        if trend_max > 0:
            t_step = trend_max / 4
            t_tick_vals = [i * t_step for i in range(5)]
            t_tick_text = [format_money(v) for v in t_tick_vals]
        else:
            t_tick_vals, t_tick_text = [], []

        fig_trend.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title=None,
            yaxis_title=None,
            margin=dict(l=20, r=20, t=30, b=40),
            yaxis=dict(
                tickvals=t_tick_vals,
                ticktext=t_tick_text,
                tickfont=dict(color="#475569"),
                gridcolor="#f1f5f9"
            ),
            xaxis=dict(
                tickfont=dict(color="#475569"),
                categoryorder='array',
                categoryarray=trend_data['month_year'].tolist() # Lock order
            )
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Insufficient data for Financial Year trend visualization.")

    # Detailed Spend Table
    st.markdown("### Transactional Spend Intelligence")
    
    # Select columns for display
    display_cols = ['supplier', 'proc_type', 'co_no', 'item_cd', 'description', 'qty', 'rate', 'discount', 'disc_rate', 'amount']
    # Filter to only existing columns
    existing_display_cols = [c for c in display_cols if c in filtered_df.columns]
    
    table_df = filtered_df[existing_display_cols].copy()
    
    # Rename for professional presentation
    rename_presentation = {
        'supplier': 'Strategic Partner',
        'proc_type': 'Spending Type',
        'co_no': 'C.O. Reference',
        'item_cd': 'SKU/Item ID',
        'description': 'Description',
        'qty': 'Order Qty',
        'rate': 'Unit Rate',
        'discount': 'Disc%',
        'disc_rate': 'Net Rate',
        'amount': 'Gross Volume'
    }
    table_df = table_df.rename(columns=rename_presentation)
    
    # Format Currency Columns for display
    if 'Unit Rate' in table_df.columns:
        table_df['Unit Rate'] = table_df['Unit Rate'].apply(lambda x: f"₹{x:,.2f}")
    if 'Net Rate' in table_df.columns:
        table_df['Net Rate'] = table_df['Net Rate'].apply(lambda x: f"₹{x:,.2f}")
    if 'Gross Volume' in table_df.columns:
        table_df['Gross Volume'] = table_df['Gross Volume'].apply(lambda x: f"₹{x:,.2f}")
        
    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        height=400 # Approximately 10-12 rows
    )

    st.markdown("---")
    st.markdown(f"<div style='text-align: center; color: rgba(255,255,255,0.4); font-size: 14px; font-weight: 500;'>Strategic Enterprise Insights • Confidential Management Report • High Performance Analytics Engine</div>", unsafe_allow_html=True)
else:
    st.error("Engine Fault. Data pipeline obstruction detected.")
