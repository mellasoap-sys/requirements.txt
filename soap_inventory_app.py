import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px
import os

# =========================================================================
# DATABASE / GOOGLE SHEETS CONFIGURATION
# =========================================================================
SHEET_ID = "1O-BghXvxzvPhVeffW5gZYi7NaSZ-rXl6OvmU-GCdsEs"

# ⚠️ PASTE YOUR COPIED GOOGLE APPS SCRIPT WEB APP URL INSIDE THE QUOTES BELOW:
API_URL = "https://script.google.com/macros/s/AKfycbzuLD2N2vDIQIBNLjSnPpHiLi2iXNgVGRyPtdG94VveC_NyjXkztfhn53rbXXMxRW1zRw/exec"

def load_data(sheet_name, default_cols):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(url)
        if df.empty or df.columns[0].startswith('Unnamed'):
            return pd.DataFrame(columns=default_cols)
        df.columns = [c.strip() for c in df.columns]
        if 'quantity' in df.columns:
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0.0)
        if 'unit_price' in df.columns:
            df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce').fillna(0.0)
        if 'total_price' in df.columns:
            df['total_price'] = pd.to_numeric(df['total_price'], errors='coerce').fillna(0.0)
        return df
    except Exception:
        return pd.DataFrame(columns=default_cols)

def append_row(sheet_name, row_list):
    if API_URL == "PASTE_YOUR_APPS_SCRIPT_URL_HERE":
        return False
    payload = {"sheet": sheet_name, "action": "append", "row": row_list}
    try:
        requests.post(API_URL, json=payload)
        return True
    except:
        return False

def overwrite_sheet(sheet_name, df):
    if API_URL == "PASTE_YOUR_APPS_SCRIPT_URL_HERE":
        return False
    rows = [df.columns.tolist()] + df.values.tolist()
    payload = {"sheet": sheet_name, "action": "overwrite", "rows": rows}
    try:
        requests.post(API_URL, json=payload)
        return True
    except:
        return False

# =========================================================================
# STREAMLIT INTERFACE SETUP
# =========================================================================
st.set_page_config(page_title="Mella Inventory Management System", layout="wide")

st.sidebar.title("🏢 Mella Manufacturing")
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

menu = ["📊 Dashboard", "📦 Current Stock / Items", "💰 Record Purchases", "🚀 Daily Production", "🏭 Production & Drum Tracking", "📋 Reports"]
choice = st.sidebar.selectbox("Navigation Menu", menu)

# =========================================================================
# 1. DASHBOARD
# =========================================================================
if choice == "📊 Dashboard":
    st.title("🧼 Mella Soap & Detergent - Inventory Dashboard")
    st.markdown("---")
    
    inv_df = load_data("Inventory", ["item_name", "category", "quantity", "unit"])
    purchases_df = load_data("Purchases", ['supplier', 'item_name', 'category', 'quantity', 'unit_price', 'total_price', 'purchase_date', 'payment_method', 'ref_num'])
    barrels_df = load_data("Barrels", ["barrel_type", "quantity"])
    
    if barrels_df.empty:
        barrels_df = pd.DataFrame([["250 KG Drum", 0], ["50 KG Drum", 0], ["Other Drum", 0]], columns=["barrel_type", "quantity"])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Unique Items in Warehouse", f"{len(inv_df)} Items")
    col2.metric("Total Expenses (ETB)", f"{purchases_df['total_price'].sum() if not purchases_df.empty else 0:,.2f} ETB")
    col3.metric("Empty Barrels Available", f"{barrels_df['quantity'].sum() if not barrels_df.empty else 0} Pcs")
    
    st.markdown("### 📊 Stock Levels Chart")
    if not inv_df.empty:
        fig = px.bar(inv_df, x='item_name', y='quantity', color='category', title="Current Inventory Quantities", labels={'item_name': 'Item Name', 'quantity': 'Quantity'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data entries detected inside your Google Sheet tabs yet.")

# =========================================================================
# 2. CURRENT STOCK
# =========================================================================
elif choice == "📦 Current Stock / Items":
    st.title("📦 Current Warehouse Stock Status")
    df = load_data("Inventory", ["item_name", "category", "quantity", "unit"])
    if not df.empty:
        st.dataframe(df.rename(columns={"item_name":"Item Name", "category":"Category", "quantity":"Available Stock", "unit":"Unit"}), use_container_width=True)
    else:
        st.warning("Google Sheet warehouse registry is currently empty.")

# =========================================================================
# 3. RECORD PURCHASES
# =========================================================================
elif choice == "💰 Record Purchases":
    st.title("💰 Record New Purchases")
    with st.form("p_form", clear_on_submit=True):
        sup = st.text_input("Supplier Name")
        cat = st.selectbox("Category", ["Chemicals", "Finished Goods", "Packaging Materials", "Office Equipment", "Others"])
        item = st.text_input("Item / Asset Description")
        qty = st.number_input("Quantity", min_value=0.0, step=1.0)
        uom = st.selectbox("Unit of Measure (UOM)", ["KG", "Piece", "Ton", "Gram", "Other"])
        price = st.number_input("Unit Price (ETB)", min_value=0.0, step=0.5)
        pay = st.selectbox("Payment Method", ["Bank Transfer", "Cash"])
        ref = st.text_input("Reference / Invoice Number")
        p_date = st.date_input("Purchase Date", datetime.now().date())
        
        if st.form_submit_button("🎯 Save Purchase"):
            if item and qty > 0 and price > 0:
                tot = qty * price
                
                # Log to Purchases Sheet
                append_row("Purchases", [sup, item, cat, qty, price, tot, str(p_date), pay, ref])
                
                # Update Inventory Master Sheet
                inv_df = load_data("Inventory", ["item_name", "category", "quantity", "unit"])
                if not inv_df.empty and item in inv_df['item_name'].values:
                    inv_df.loc[inv_df['item_name'] == item, 'quantity'] += qty
                else:
                    new_row = pd.DataFrame([[item, cat, qty, uom]], columns=["item_name", "category", "quantity", "unit"])
                    inv_df = pd.concat([inv_df, new_row], ignore_index=True)
                overwrite_sheet("Inventory", inv_df)
                
                st.success(f"Successfully recorded to Google Sheets! Total: {tot:,.2f} ETB.")
            else:
                st.error("Please fill in item details, quantity, and price fields.")

# =========================================================================
# 4. DAILY PRODUCTION
# =========================================================================
elif choice == "🚀 Daily Production":
    st.title("🚀 Record Daily Finished Goods Production")
    with st.form("production_form", clear_on_submit=True):
        product = st.selectbox("Select Manufactured Product", [
            "Ajax 200g", "Ajax 100g", "Bar soap 1", "Bar soap 2", 
            "Raina shampoo", "Raina hand wash", "Raina shower gel", 
            "Raina dish wash", "Raina laundry detergent", "MELLA Bleach"
        ])
        prod_qty = st.number_input("Produced Quantity", min_value=0.0, step=1.0)
        prod_uom = st.selectbox("Unit of Measure (UOM for Production)", ["Pcs", "Liters", "KG"])
        prod_date = st.date_input("Production Date", datetime.now().date())
        
        if st.form_submit_button("🏭 Log Finished Production"):
            if prod_qty > 0:
                # Log to Productions sheet
                append_row("Productions", [product, prod_qty, prod_uom, str(prod_date)])
                
                # Increment Stock in Inventory Sheet
                inv_df = load_data("Inventory", ["item_name", "category", "quantity", "unit"])
                if not inv_df.empty and product in inv_df['item_name'].values:
                    inv_df.loc[inv_df['item_name'] == product, 'quantity'] += prod_qty
                else:
                    new_row = pd.DataFrame([[product, "Finished Goods", prod_qty, prod_uom]], columns=["item_name", "category", "quantity", "unit"])
                    inv_df = pd.concat([inv_df, new_row], ignore_index=True)
                overwrite_sheet("Inventory", inv_df)
                
                st.success(f"Successfully tracked! Added {prod_qty} {prod_uom} of {product} to Google Sheets.")
            else:
                st.error("Produced Quantity must be greater than 0.")

# =========================================================================
# 5. PRODUCTION & DRUM TRACKING
# =========================================================================
elif choice == "🏭 Production & Drum Tracking":
    st.title("🏭 Raw Chemical Consumption & Automatic Drum Tracking")
    
    barrels_df = load_data("Barrels", ["barrel_type", "quantity"])
    if barrels_df.empty:
        barrels_df = pd.DataFrame([["250 KG Drum", 0], ["50 KG Drum", 0], ["Other Drum", 0]], columns=["barrel_type", "quantity"])
        overwrite_sheet("Barrels", barrels_df)
        
    st.subheader("🛢️ Empty Barrels Currently in Stock")
    st.table(barrels_df.rename(columns={"barrel_type": "Barrel Type", "quantity": "Available Quantity"}))
    
    st.markdown("---")
    st.subheader("🧪 Record Chemical Consumption")
    inv_df = load_data("Inventory", ["item_name", "category", "quantity", "unit"])
    chems = []
    if not inv_df.empty:
        chems = inv_df[(inv_df['category'] == 'Chemicals') & (inv_df['quantity'] > 0)]['item_name'].tolist()
    
    if chems:
        with st.form("prod_form"):
            c_name = st.selectbox("Select Used Chemical", chems)
            b_type = st.selectbox("Barrel Type Used", ["250 KG Drum", "50 KG Drum", "Other Drum"])
            b_used = st.number_input("Number of Barrels Emptied", min_value=1, step=1)
            kg_per = st.number_input("KG per Barrel", min_value=1.0, value=250.0 if b_type == "250 KG Drum" else 50.0)
            
            if st.form_submit_button("♻️ Log Consumption & Auto-Add Empty Barrels"):
                total_kg = b_used * kg_per
                current_qty = inv_df.loc[inv_df['item_name'] == c_name, 'quantity'].values[0]
                
                if current_qty >= total_kg:
                    # Deduct chemical
                    inv_df.loc[inv_df['item_name'] == c_name, 'quantity'] -= total_kg
                    overwrite_sheet("Inventory", inv_df)
                    
                    # Add to empty barrel count
                    barrels_df.loc[barrels_df['barrel_type'] == b_type, 'quantity'] += b_used
                    overwrite_sheet("Barrels", barrels_df)
                    
                    st.success(f"Deducted {total_kg} KG from raw chemical stock. Added empty drums to Google Sheets.")
                    st.rerun()
                else:
                    st.error(f"Insufficient stock! Only {current_qty} KG available.")
    else:
        st.info("No chemical stocks registered under 'Chemicals' category to consume yet.")

# =========================================================================
# 6. REPORTS
# =========================================================================
elif choice == "📋 Reports":
    st.title("📋 Generate Management Reports")
    rep = st.selectbox("Select Report Type", ["Current Warehouse Stock", "Purchase History", "Daily Production History"])
    
    if rep == "Current Warehouse Stock":
        df = load_data("Inventory", ["item_name", "category", "quantity", "unit"])
    elif rep == "Purchase History":
        df = load_data("Purchases", ['supplier', 'item_name', 'category', 'quantity', 'unit_price', 'total_price', 'purchase_date', 'payment_method', 'ref_num'])
    else:
        df = load_data("Productions", ['product_name', 'quantity', 'unit', 'production_date'])
        
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download Report as CSV", df.to_csv(index=False).encode('utf-8'), f"{rep.replace(' ', '_')}.csv", "text/csv")
    else:
        st.info("No data entries registered for this report yet.")
