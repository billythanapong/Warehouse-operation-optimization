import streamlit as st
import plotly.graph_objects as go
import time
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="Sales Page", layout="wide")

# Load data
DATA_DIR = os.path.join(os.path.dirname(__file__), '..','..', 'data')
files = [f for f in os.listdir(DATA_DIR) if f.endswith('modified_user.csv')]
selected_file = files[0] if files else None
if selected_file:
    df = pd.read_csv(os.path.join(DATA_DIR, selected_file))
else:
    st.warning("No data file found.")
    st.stop()

# Add Items to Sales Table

# --- PO Number and Customer Name ---
today_str = datetime.now().strftime("%Y-%m-%d")
po_prefix = f"PO-{datetime.now().strftime('%Y-%m-%d')}"
if 'po_counter' not in st.session_state or st.session_state.get('po_date') != today_str:
    st.session_state['po_counter'] = 1
    st.session_state['po_date'] = today_str
po_number = f"{po_prefix}-{st.session_state['po_counter']:04d}"

if 'customer_name' not in st.session_state:
    st.session_state['customer_name'] = ''

st.subheader("Create Sales Order")
if 'sales_table' not in st.session_state:
    st.session_state['sales_table'] = []
if 'selected_idx' not in st.session_state:
    st.session_state['selected_idx'] = 0

item_options = df['item_id'].unique() if 'item_id' in df.columns else df.index.astype(str)

with st.form("sales_order_form"):
    customer_name = st.text_input("Customer Name", value=st.session_state['customer_name'])
    st.text_input("PO Number", value=po_number, disabled=True)
    item = st.selectbox("Select Item", item_options)
    amount = st.number_input("Amount", min_value=1, value=1)
    submitted = st.form_submit_button("Add/Update Item")
    if submitted:
        st.session_state['customer_name'] = customer_name
        found = False
        for row in st.session_state['sales_table']:
            if row['item'] == item:
                row['amount'] = amount
                found = True
                st.success("Item has been updated.")
                break
        if not found:
            st.session_state['sales_table'].append({'item': item, 'amount': amount})



# Prepare DataFrame for Data Editor
sales_df = pd.DataFrame(st.session_state['sales_table'])
if not sales_df.empty:
    # Merge with item info
    merged = sales_df.merge(df[['item_id','category','stock_level']], left_on='item', right_on='item_id', how='left')
    merged = merged.rename(columns={'amount': 'qty ordered', 'stock_level': 'stocklevel'})
    # Status logic
    def status_func(row):
        if pd.isna(row['stocklevel']) or pd.isna(row['qty ordered']):
            return ''
        diff = row['stocklevel'] - row['qty ordered']
        if diff >= 0:
            return 'ok'
        elif abs(diff) < 20:
            return f"short ({abs(int(diff))})"
        else:
            return f"short ({abs(int(diff))})"
    merged['status'] = merged.apply(status_func, axis=1)
    
    # Only show required columns
    show_cols = ['item_id','category','qty ordered','stocklevel','status']
    merged = merged[show_cols]
    # Title and subtitle
    st.markdown(f"### Sales Order - {po_number} for {st.session_state['customer_name']}")
    st.markdown(f"<span style='font-size:16px;'>Created on {today_str} by <b>Employee01</b> - <b>{len(merged)}</b> items</span>", unsafe_allow_html=True)
    # Show styled DataFrame using .apply (row-wise) for status column
    def highlight_status_row(row):
        style = [''] * len(row)
        if 'status' in row.index:
            idx = row.index.get_loc('status')
            val = row['status']
            if val == 'ok':
                style[idx] = 'background-color:  rgba(0, 107, 61,0.6)'
            elif isinstance(val, str) and val.startswith('short'):
                num = int(val.split('(')[-1].replace(')','')) if '(' in val else 0
                if num < 20:
                    style[idx] = 'background-color: rgba(255, 152, 14,0.6)'
                else:
                    style[idx] = 'background-color: rgba(211, 33, 44,0.6)'
        return style
    st.dataframe(merged.style.apply(highlight_status_row, axis=1), use_container_width=True)

    submit = st.button("Submit Order")
    if submit:
        st.balloons()
        # 1. Log activity to session state
        if 'activity_log' not in st.session_state:
            st.session_state['activity_log'] = []
        st.session_state['activity_log'].append({
            "job function": "Sales Page",
            "date time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "activity": f"Submitted sales order {po_number} for {st.session_state['customer_name']}",
            "number": len(st.session_state['activity_log']) + 1
        })

        # 1.5. Save sales order to sales history table in session state
        if 'sales_history' not in st.session_state:
            st.session_state['sales_history'] = []
        # Save a copy of the current order with metadata
        sales_order_record = {
            "po_number": po_number,
            "customer_name": st.session_state['customer_name'],
            "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": list(st.session_state['sales_table'])
        }
        st.session_state['sales_history'].append(sales_order_record)

        # 2. Deduct stock level from _user.csv for each item in sales order
        user_file_path = os.path.join(DATA_DIR, selected_file)
        df_user = pd.read_csv(user_file_path)
        for row in st.session_state['sales_table']:
            item_id = row['item']
            amount = row['amount']
            if 'item_id' in df_user.columns and 'stock_level' in df_user.columns:
                idx = df_user[df_user['item_id'] == item_id].index
                if not idx.empty:
                    df_user.loc[idx, 'stock_level'] = df_user.loc[idx, 'stock_level'] - amount
        df_user.to_csv(user_file_path, index=False)

        # 3. Clear only relevant session state for sales page
        time.sleep(2)  # Just to allow balloons to show before clearing
        st.session_state['sales_table'] = []
        st.session_state['customer_name'] = ''
        st.session_state['selected_idx'] = 0
        # Optionally increment PO counter for next order
        st.session_state['po_counter'] += 1

        # 4. Refresh warehouse page tables by clearing Streamlit cache
        try:
            st.cache_data.clear()
            st.cache_resource.clear()
        except Exception:
            pass
        st.rerun()

else:
    st.info("No items added yet.")