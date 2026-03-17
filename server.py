from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
import database as db
from typing import List, Optional
import datetime
import os

app = FastAPI(title="KEPL Spend Analytics API")

# Enable CORS for the custom frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()

@app.get("/", response_class=HTMLResponse)
def read_root():
    path = os.path.join("frontend", "index.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Server Online</h1><p>Frontend file not found.</p>"

@app.get("/api/status")
def get_status():
    return {"status": "Powerhouse Engine Online", "rows": db.SessionLocal().query(db.SpendTransaction).count()}

@app.post("/sync")
def sync_data(background_tasks: BackgroundTasks):
    SHEET_ID = "1VnsMIcFNYUtFmLsYYfLagUusm0FMnys6iSmSrhHhlfQ"
    CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    background_tasks.add_task(db.sync_from_sheets, CSV_URL)
    return {"message": "Sync started in background"}

@app.get("/metrics")
def get_metrics(category: Optional[str] = None, supplier: Optional[str] = None, proc_type: Optional[str] = None, session: Session = Depends(get_db)):
    query = session.query(db.SpendTransaction)
    if category and category != "All": query = query.filter(db.SpendTransaction.category == category)
    if supplier and supplier != "All": query = query.filter(db.SpendTransaction.supplier == supplier)
    if proc_type and proc_type != "All": query = query.filter(db.SpendTransaction.proc_type == proc_type)
    
    total_spend = query.with_entities(func.sum(db.SpendTransaction.amount)).scalar() or 0
    po_count = query.with_entities(func.count(func.distinct(db.SpendTransaction.po_no))).scalar() or 0
    vendor_count = query.with_entities(func.count(func.distinct(db.SpendTransaction.supplier))).scalar() or 0
    
    return {
        "total_spend": total_spend,
        "po_count": po_count,
        "vendor_count": vendor_count
    }

@app.get("/charts/top-suppliers")
def get_top_suppliers(limit: int = 10, category: Optional[str] = None, supplier: Optional[str] = None, proc_type: Optional[str] = None, session: Session = Depends(get_db)):
    query = session.query(db.SpendTransaction.supplier, func.sum(db.SpendTransaction.amount).label('amount'))
    if category and category != "All": query = query.filter(db.SpendTransaction.category == category)
    if supplier and supplier != "All": query = query.filter(db.SpendTransaction.supplier == supplier)
    if proc_type and proc_type != "All": query = query.filter(db.SpendTransaction.proc_type == proc_type)
    
    results = query.group_by(db.SpendTransaction.supplier).order_by(func.sum(db.SpendTransaction.amount).desc()).limit(limit).all()
    return [{"supplier": r[0], "amount": r[1]} for r in results]

@app.get("/charts/category-dist")
def get_category_distribution(category: Optional[str] = None, supplier: Optional[str] = None, proc_type: Optional[str] = None, session: Session = Depends(get_db)):
    query = session.query(db.SpendTransaction.category, func.sum(db.SpendTransaction.amount).label('amount'))
    if category and category != "All": query = query.filter(db.SpendTransaction.category == category)
    if supplier and supplier != "All": query = query.filter(db.SpendTransaction.supplier == supplier)
    if proc_type and proc_type != "All": query = query.filter(db.SpendTransaction.proc_type == proc_type)
    
    results = query.group_by(db.SpendTransaction.category).all()
    return [{"category": r[0], "amount": r[1]} for r in results]

@app.get("/charts/trend")
def get_trend(category: Optional[str] = None, supplier: Optional[str] = None, proc_type: Optional[str] = None, session: Session = Depends(get_db)):
    # SQL implementation of the FY Sorting Logic (Apr to Mar)
    # We select po_date, amount and calculate month/year strings
    query = session.query(db.SpendTransaction.po_date, db.SpendTransaction.amount)
    if category and category != "All": query = query.filter(db.SpendTransaction.category == category)
    if supplier and supplier != "All": query = query.filter(db.SpendTransaction.supplier == supplier)
    if proc_type and proc_type != "All": query = query.filter(db.SpendTransaction.proc_type == proc_type)
    
    data = query.all()
    if not data: return []
    
    import pandas as pd
    df = pd.DataFrame(data, columns=['po_date', 'amount'])
    # Drop rows without dates for trend calculation
    df = df.dropna(subset=['po_date'])
    if df.empty: return []
    
    df['month_year'] = df['po_date'].dt.strftime('%b-%Y')
    
    # Financial Year Sorting Logic (April to March)
    df['fy_month_idx'] = df['po_date'].dt.month.map(lambda x: x - 3 if x >= 4 else x + 9)
    df['fy_sort_key'] = df['po_date'].dt.year * 100 + df['fy_month_idx']
    
    trend = df.groupby(['fy_sort_key', 'month_year'])['amount'].sum().reset_index().sort_values('fy_sort_key')
    return trend[['month_year', 'amount']].to_dict(orient='records')

@app.get("/transactions")
def get_transactions(limit: int = 100, category: Optional[str] = None, supplier: Optional[str] = None, proc_type: Optional[str] = None, session: Session = Depends(get_db)):
    query = session.query(db.SpendTransaction)
    if category and category != "All": query = query.filter(db.SpendTransaction.category == category)
    if supplier and supplier != "All": query = query.filter(db.SpendTransaction.supplier == supplier)
    if proc_type and proc_type != "All": query = query.filter(db.SpendTransaction.proc_type == proc_type)
    
    results = query.order_by(db.SpendTransaction.po_date.desc()).limit(limit).all()
    output = []
    for r in results:
        output.append({
            "po_date": r.po_date.strftime('%d-%b-%Y') if r.po_date else "N/A",
            "po_no": r.po_no,
            "category": r.category,
            "supplier": r.supplier,
            "description": r.description,
            "item_cd": r.item_cd,
            "qty": r.qty,
            "rate": r.rate,
            "discount": r.discount,
            "amount": r.amount,
            "proc_type": r.proc_type
        })
    return output

@app.get("/filters")
def get_filters(category: Optional[str] = None, supplier: Optional[str] = None, proc_type: Optional[str] = None, session: Session = Depends(get_db)):
    # Bi-directional Cascading Logic (Full Cross-Filtering)
    
    # 1. Categories available given selected supplier and type
    cat_query = session.query(db.SpendTransaction.category).distinct()
    if supplier and supplier != "All": cat_query = cat_query.filter(db.SpendTransaction.supplier == supplier)
    if proc_type and proc_type != "All": cat_query = cat_query.filter(db.SpendTransaction.proc_type == proc_type)
    
    # 2. Suppliers available given selected category and type
    supp_query = session.query(db.SpendTransaction.supplier).distinct()
    if category and category != "All": supp_query = supp_query.filter(db.SpendTransaction.category == category)
    if proc_type and proc_type != "All": supp_query = supp_query.filter(db.SpendTransaction.proc_type == proc_type)
    
    # 3. Types available given selected category and supplier
    type_query = session.query(db.SpendTransaction.proc_type).distinct()
    if category and category != "All": type_query = type_query.filter(db.SpendTransaction.category == category)
    if supplier and supplier != "All": type_query = type_query.filter(db.SpendTransaction.supplier == supplier)
    
    return {
        "categories": sorted([r[0] for r in cat_query.all() if r[0]]),
        "suppliers": sorted([r[0] for r in supp_query.all() if r[0]]),
        "types": sorted([r[0] for r in type_query.all() if r[0]])
    }

if __name__ == "__main__":
    import uvicorn
    # Initialize DB and perform initial sync if empty
    db.init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
