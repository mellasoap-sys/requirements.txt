import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import os

# 1. Database Configuration
DB_FILE = "soap_inventory.db"
def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY AUTOINCREMENT, supplier TEXT, item_name TEXT, category TEXT, quantity REAL, unit_price REAL, total_price REAL, purchase_date TEXT, payment_method TEXT, ref_num TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (item_name TEXT PRIMARY KEY, category TEXT, quantity REAL, unit TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS empty_barrels (barrel_type TEXT PRIMARY KEY, quantity INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS productions (id INTEGER PRIMARY KEY AUTOINCREMENT, product_name TEXT, quantity REAL, unit TEXT, production_date TEXT)''')
    cursor.execute("SELECT COUNT(*) FROM empty_barrels")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO empty_barrels (barrel_type, quantity) VALUES ('250 KG Drum', 0), ('50 KG Drum', 0), ('Other Drum', 0)")
    conn.commit()
    conn.close()

init_db()

# 2. Page Setup
st.set_page_config(page_title="Mella Inventory Management System", layout="wide")

st.sidebar.title("🏢 Mella Manufacturing")
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

menu = ["📊 Dashboard", "📦 Current Stock / Items", "💰 Record Purchases", "🚀 Daily Production", "🏭 Production & Drum Tracking", "📋 Reports"]
choice = st.sidebar.selectbox("Navigation Menu", menu)
conn = get_db_connection()

if choice == "📊 Dashboard":
    st.title("🧼 Mella Soap & Detergent - Inventory Dashboard")
    st.markdown("---")
    
    inv_df = pd.read_sql_query("SELECT * FROM inventory", conn)
    barrels_df = pd.read_sql_query("SELECT * FROM empty_barrels", conn)
    purchases_df = pd.read_sql_query("SELECT * FROM purchases", conn)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Unique Items in Warehouse", f"{len(inv_df)} Items")
    col2.metric("Total Expenses (ETB)", f"{purchases_df['total_price'].sum() if not purchases_df.empty else 0:,.2f} ETB")
    col3.metric("Empty Barrels Available", f"{barrels_df['quantity'].sum() if not barrels_df.empty else 0} Pcs")
    
    st.markdown("### 📊 Stock Levels Chart")
    if not inv_df.empty:
        fig = px.bar(inv_df, x='item_name', y='quantity', color='category', title="Current Inventory Quantities", labels={'item_name': 'Item Name', 'quantity': 'Quantity'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available yet. Use menus to feed information.")

elif choice == "📦 Current Stock / Items":
    st.title("📦 Current Warehouse Stock Status")
    df = pd.read_sql_query("SELECT item_name AS [Item Name], category AS [Category], quantity AS [Available Stock], unit AS [Unit] FROM inventory", conn)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Warehouse is currently empty.")

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
                cursor = conn.cursor()
                cursor.execute("INSERT INTO purchases (supplier, item_name, category, quantity, unit_price, total_price, purchase_date, payment_method, ref_num) VALUES (?,?,?,?,?,?,?,?,?)", (sup, item, cat, qty, price, tot, str(p_date), pay, ref))
                cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (item,))
                row = cursor.fetchone()
                if row: 
                    cursor.execute("UPDATE inventory SET quantity = ? WHERE item_name = ?", (row[0]+qty, item))
                else: 
                    cursor.execute("INSERT INTO inventory VALUES (?,?,?,?)", (item, cat, qty, uom))
                conn.commit()
                st.success(f"Success! Record added. Total Price: {tot:,.2f} ETB. Warehouse Stock updated.")
            else:
                st.error("Please fill in item details, quantity, and price fields.")

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
                cursor = conn.cursor()
                cursor.execute("INSERT INTO productions (product_name, quantity, unit, production_date) VALUES (?,?,?,?)", (product, prod_qty, prod_uom, str(prod_date)))
                cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (product,))
                row = cursor.fetchone()
                if row:
                    cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE item_name = ?", (prod_qty, product))
                else:
                    cursor.execute("INSERT INTO inventory VALUES (?, ?, ?, ?)", (product, "Finished Goods", prod_qty, prod_uom))
                conn.commit()
                st.success(f"Successfully recorded! added {prod_qty} {prod_uom} of {product} to warehouse stock.")
            else:
                st.error("Produced Quantity must be greater than 0.")

elif choice == "🏭 Production & Drum Tracking":
    st.title("🏭 Raw Chemical Consumption & Automatic Drum Tracking")
    b_df = pd.read_sql_query("SELECT barrel_type AS [Barrel Type], quantity AS [Available Quantity] FROM empty_barrels", conn)
    st.table(b_df)
    st.markdown("---")
    st.subheader("🧪 Record Chemical Consumption")
    chems = [r[0] for r in conn.cursor().execute("SELECT item_name FROM inventory WHERE category='Chemicals' AND quantity > 0").fetchall()]
    
    if chems:
        with st.form("prod_form"):
            c_name = st.selectbox("Select Used Chemical", chems)
            b_type = st.selectbox("Barrel Type Used", ["250 KG Drum", "50 KG Drum", "Other Drum"])
            b_used = st.number_input("Number of Barrels Emptied", min_value=1, step=1)
            kg_per = st.number_input("KG per Barrel", min_value=1.0, value=250.0 if b_type == "250 KG Drum" else 50.0)
            
            if st.form_submit_button("♻️ Log Consumption & Auto-Add Empty Barrels"):
                total_kg = b_used * kg_per
                cursor = conn.cursor()
                cursor.execute("SELECT quantity FROM inventory WHERE item_name = ?", (c_name,))
                current_qty = cursor.fetchone()[0]
                
                if current_qty >= total_kg:
                    cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE item_name = ?", (total_kg, c_name))
                    cursor.execute("UPDATE empty_barrels SET quantity = quantity + ? WHERE barrel_type = ?", (b_used, b_type))
                    conn.commit()
                    st.success(f"Deducted {total_kg} KG from raw stock. Empty Barrel(s) automatically tracked.")
                else:
                    st.error(f"Insufficient chemical stock! Only {current_qty} KG available.")
    else:
        st.info("No chemical stocks registered under 'Chemicals' category to consume yet.")

elif choice == "📋 Reports":
    st.title("📋 Generate Management Reports")
    rep = st.selectbox("Select Report Type", ["Current Warehouse Stock", "Purchase History", "Daily Production History"])
    
    if rep == "Current Warehouse Stock":
        df = pd.read_sql_query("SELECT item_name AS [Item Name], category AS [Category], quantity AS [Quantity], unit AS [Unit] FROM inventory", conn)
    elif rep == "Purchase History":
        df = pd.read_sql_query("SELECT supplier AS [Supplier], item_name AS [Item], category AS [Category], quantity AS [Qty], unit_price AS [Unit Price], total_price AS [Total Cost (ETB)], purchase_date AS [Date], payment_method AS [Payment], ref_num AS [Ref No] FROM purchases", conn)
    else:
        df = pd.read_sql_query("SELECT product_name AS [Product Manufactured], quantity AS [Quantity Output], unit AS [UOM], production_date AS [Date of Production] FROM productions", conn)
        
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download Report as Excel/CSV", df.to_csv(index=False).encode('utf-8'), f"{rep.replace(' ', '_')}.csv", "text/csv")
    else:
        st.info("No data entries registered for this report yet.")

conn.close()
