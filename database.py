from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pandas as pd
import datetime
import io
import requests

# SQLite database setup
DATABASE_URL = "sqlite:///./spend_analysis.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Model for Spend Transactions
class SpendTransaction(Base):
    __tablename__ = "spend_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    po_date = Column(DateTime, index=True)
    po_no = Column(String, index=True)
    category = Column(String, index=True)
    supplier = Column(String, index=True)
    description = Column(String)
    item_cd = Column(String)
    qty = Column(Float)
    rate = Column(Float)
    discount = Column(Float)
    disc_rate = Column(Float)
    amount = Column(Float, index=True)
    proc_type = Column(String, index=True)
    co_no = Column(String)

    # Indexes for high performance querying
    __table_args__ = (
        Index('ix_supplier_amount', 'supplier', 'amount'),
        Index('ix_category_amount', 'category', 'amount'),
    )

def init_db():
    Base.metadata.create_all(bind=engine)

def sync_from_sheets(csv_url: str):
    print(f"Syncing from: {csv_url}")
    # Force fresh data from Google Sheets
    import time
    cache_busting_url = f"{csv_url}&t={int(time.time())}"
    
    response = requests.get(cache_busting_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch Google Sheet: {response.status_code}")
    
    # Ensure UTF-8 encoding
    response.encoding = 'utf-8'
    df = pd.read_csv(io.StringIO(response.text), on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    
    # Column mapping logic (robust version from app.py)
    def find_col(patterns):
        cols = list(df.columns)
        normalized = {c.strip().lower(): c for c in cols}
        for p in patterns:
            key = p.strip().lower()
            if key in normalized: return normalized[key]
        for p in patterns:
            pl = p.lower()
            for col in cols:
                if pl in col.lower(): return col
        return None

    mapping = {
        'po_date': find_col(['Date', 'P.O.Date', 'PO Date']),
        'po_no': find_col(['P.O.No.', 'PO No', 'PO Number']),
        'category': find_col(['Category']),
        'supplier': find_col(['Supplier', 'Vendor', 'Name']),
        'description': find_col(['Description']),
        'item_cd': find_col(['Item Cd']),
        'qty': find_col(['PoQty-PU', 'Qty']),
        'rate': find_col(['Rate']),
        'discount': find_col(['Discount']),
        'disc_rate': find_col(['Discounted Rate']),
        'amount': find_col(['Amt', 'Amount', 'Value', 'Total']),
        'proc_type': find_col(['Type', 'Procurement Type', 'PO Type']),
        'co_no': find_col(['C.O.No.'])
    }
    
    # Rename and Clean
    active_mapping = {v: k for k, v in mapping.items() if v}
    df = df.rename(columns=active_mapping)
    
    # Ensure all columns exist for the DB model
    for col in mapping.keys():
        if col not in df.columns:
            df[col] = None

    # Cast types
    df['po_date'] = pd.to_datetime(df['po_date'], dayfirst=True, errors='coerce')
    # df = df.dropna(subset=['po_date']) # REMOVED: Allow rows with blank dates (Salary, Rent, etc.)
    
    numeric_cols = ['qty', 'rate', 'discount', 'disc_rate', 'amount']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[^0-9.]', '', regex=True), errors='coerce').fillna(0)
    
    # Clean Supplier/Name characters (e.g. mangled dashes)
    if 'supplier' in df.columns:
        df['supplier'] = df['supplier'].astype(str).str.replace('â€“', '–').str.replace('â€”', '—').str.strip()
    
    # Bulk insert into SQLite
    db = SessionLocal()
    try:
        # Clear existing data for fresh sync (rebuild for 83k rows)
        db.execute(Base.metadata.tables['spend_transactions'].delete())
        
        # Insert in chunks for memory efficiency
        data_to_insert = df.to_dict(orient='records')
        db.bulk_insert_mappings(SpendTransaction, data_to_insert)
        db.commit()
        print(f"Successfully synced {len(df)} rows.")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    SHEET_ID = "1VnsMIcFNYUtFmLsYYfLagUusm0FMnys6iSmSrhHhlfQ"
    CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    sync_from_sheets(CSV_URL)
