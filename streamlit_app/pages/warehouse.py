import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

st.set_page_config(page_title="Warehouse Page", layout="wide")

# Load data
DATA_DIR = os.path.join(os.path.dirname(__file__), '..','..', 'data')
files = [f for f in os.listdir(DATA_DIR) if f.endswith('modified_user.csv')]
selected_file = files[0] if files else None
if selected_file:
    df = pd.read_csv(os.path.join(DATA_DIR, selected_file))
else:
    st.warning("No data file found.")
    st.stop()


# Tabs for overview and specific item
tab1, tab2 = st.tabs(["Overview 📖", "Item Insight 🔍"])

with tab1:
    st.subheader("Warehouse Overview")
    # Metric cards
    total_monetary = df['unit_price'].sum() if 'unit_price' in df.columns else 0
    total_holding_cost = df['holding_cost_per_unit_day'].sum() if 'holding_cost_per_unit_day' in df.columns else 0
    # colA, colB = st.columns(2)
    # colA.metric("Total Monetary Value", f"{total_monetary:,.2f}")
    # colB.metric("Total Holding Cost/Unit/Day", f"{total_holding_cost:,.2f}")

    # 1. Number of tracked items
    num_items = len(df)
    # 2. Number of items where reorder_point < ROP
    num_reorder_below_rop = 0
    if 'reorder_point' in df.columns and 'ROP' in df.columns:
        num_reorder_below_rop = (df['reorder_point'] < df['ROP']).sum()
    # 3. Number of items that will be short in 7 days (using forecasted demand)
    num_short_7d = 0
    if 'stock_level' in df.columns and 'forecasted_demand_next_7d' in df.columns:
        def will_shortage(row):
            stock = row['stock_level']
            forecast = row['forecasted_demand_next_7d']
            daily = forecast / 7 if forecast else 0
            for _ in range(7):
                stock -= daily
                if stock <= 0:
                    return True
            return False
        num_short_7d = df.apply(will_shortage, axis=1).sum()

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Tracked Items", str(num_items)+ "", border=True)
    m2.metric("ROP changed (items)", num_reorder_below_rop,border=True)
    m3.metric("Shortage in 7 Days (items)", num_short_7d, border=True)
    m4.metric("Total Valuation ($)", f"{total_monetary:,.2f}",border=True)
    m5.metric("Total Holding Cost/Unit/Day", f"{total_holding_cost:,.2f}",border=True)

    # Filters
    st.write("### Summary Table")

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    categories = sorted(df['category'].unique())
    itemcodes = sorted(df['item_id'].unique())
    inventory_tiers = sorted(df['Inventory_Tier'].unique())
    selected_category = filter_col1.selectbox("Filter by Category", options=["All"] + list(categories))
    selected_itemcode = filter_col2.selectbox("Filter by Item Code", options=["All"] + list(itemcodes))
    selected_inventory_tier = filter_col3.selectbox("Filter by Inventory Tier", options=["All"] + list(inventory_tiers))

    filtered_df = df.copy()
    filtered_df = filtered_df[['item_id','category','Inventory_Tier','stock_level','ROP','reorder_point','reorder_frequency_days','lead_time_days','daily_demand','demand_std_dev','storage_location_id','zone','unit_price','total_orders_last_month','last_restock_date','forecasted_demand_next_7d','order_fulfillment_rate']]
    
    if selected_category != "All" and 'category' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    if selected_itemcode != "All" and 'item_id' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['item_id'] == selected_itemcode]
    if selected_inventory_tier != "All" and 'Inventory_Tier' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Inventory_Tier'] == selected_inventory_tier]


    # Table of items that will shortage in 7 days
    if 'stock_level' in filtered_df.columns and 'forecasted_demand_next_7d' in filtered_df.columns:
        def will_shortage_row(row):
            stock = row['stock_level']
            forecast = row['forecasted_demand_next_7d']
            daily = forecast / 7 if forecast else 0
            for _ in range(7):
                stock -= daily
                if stock <= 0:
                    return True
            return False
        shortage_7d_df = filtered_df[filtered_df.apply(will_shortage_row, axis=1)].reset_index(drop=True)
        st.write(f"Items that will shortage in 7 days: :red[{shortage_7d_df.shape[0]}]/{filtered_df.shape[0]}")
        def highlight_higher_rop(s):
            reorder = s['reorder_point'] if 'reorder_point' in s else None
            rop = s['ROP'] if 'ROP' in s else None
            style = [''] * len(s)
            if reorder is not None and rop is not None:
                if reorder > rop:
                    style[s.index.get_loc('reorder_point')] = 'background-color: rgba(255,255,0,0.2)'
                elif rop > reorder:
                    style[s.index.get_loc('ROP')] = 'background-color: rgba(255,255,0,0.5)'
            return style
        if not shortage_7d_df.empty:
            st.dataframe(shortage_7d_df.style.apply(highlight_higher_rop, axis=1), use_container_width=True)
        else:
            st.info("No items will shortage in 7 days.")

    # Table of items below reorder point
    if 'reorder_point' in filtered_df.columns and 'stock_level' in filtered_df.columns:
        below_reorder = filtered_df[filtered_df['stock_level'] < filtered_df['ROP']].reset_index(drop=True)
        # Add status column
        def calc_status(row):
            stock = row['stock_level']
            rop = row['ROP']
            if rop == 0:
                return "-"
            diff = stock - rop
            pct = diff / rop
            
            if pct >= -0.25:
                return "Warning"
            elif pct >= -0.7:
                return "Critique"
            else :
                return "Danger"
        if not below_reorder.empty:
            below_reorder = below_reorder.copy()
            below_reorder['status'] = below_reorder.apply(calc_status, axis=1)
            # Move 'status' column to be after 'Inventory_Tier'
            cols = list(below_reorder.columns)
            if 'status' in cols and 'Inventory_Tier' in cols:
                cols.remove('status')
                idx = cols.index('Inventory_Tier') + 1
                cols = cols[:idx] + ['status'] + cols[idx:]
                below_reorder = below_reorder[cols]
            def highlight_status(s):
                color_map = {
                    "Danger": "background-color: rgba(255,0,0,0.5)",
                    "Critique": "background-color: rgba(255,165,0,0.5)",
                    "Warning": "background-color: rgba(255,255,0,0.5)"
                }
                return [color_map.get(val, "") if col == 'status' else "" for col, val in zip(s.index, s)]
            def highlight_ROP(s):
                style = [''] * len(s)
                style[s.index.get_loc('ROP')] = 'background-color: rgba(255,255,0,0.5)'
                return style
            st.write(f"Items below reorder point : :red[{below_reorder.shape[0]}]/{df.shape[0]}")
            st.dataframe(
                below_reorder.style.apply(highlight_ROP, axis=1).apply(highlight_status, axis=1),
                use_container_width=True
            )
            
        else:
            st.info("No items below reorder point.")
    else:
        st.info("Reorder point or stock level columns not found in data.")


# --- Add line chart of last restock date grouped by inventory tier ---
    st.markdown("---")
    st.subheader("Monthly Total Orders by Inventory Tier")
    if 'last_restock_date' in df.columns and 'Inventory_Tier' in df.columns and 'total_orders_last_month' in df.columns:
        df['last_restock_date_dt'] = pd.to_datetime(df['last_restock_date'], errors='coerce')
        df['restock_month'] = df['last_restock_date_dt'].dt.to_period('M').astype(str)
        # Group by month and inventory tier, sum total_orders_last_month
        grouped = df.groupby(['restock_month', 'Inventory_Tier'])['total_orders_last_month'].sum().reset_index()
        # Pivot for easier plotting
        pivot = grouped.pivot(index='restock_month', columns='Inventory_Tier', values='total_orders_last_month').fillna(0)
        fig3 = go.Figure()
        for tier in pivot.columns:
            fig3.add_trace(go.Scatter(
                x=pivot.index,
                y=pivot[tier],
                mode='lines+markers',
                name=str(tier),
                marker=dict(size=8)
            ))
        fig3.update_layout(
            title='Monthly Total Orders by Inventory Tier',
            xaxis_title='Restock Month',
            yaxis_title='Total Orders',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=True,
            margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("last_restock_date, Inventory_Tier, or total_orders_last_month column not found for monthly orders chart.")



with tab2:
    st.subheader("Item Insight Projection")
    item_options = df['item_id'].unique() if 'item_id' in df.columns else df.index.astype(str)
    with st.form("search_item_form"):
        item = st.selectbox("Select Item", item_options, key="warehouse_item_select")
        submit_col,send_col = st.columns([0.8,9.2])
        with submit_col : 
            submitted = st.form_submit_button("Search")
            if submitted : 
                st.session_state['submitted'] = True
        
        if st.session_state.get('submitted'):
            with send_col:
                send = st.form_submit_button("Send to Purchase")
                if send : 
                    st.balloons()
                    if 'activity_log' not in st.session_state:
                        st.session_state['activity_log'] = []
                    st.session_state['activity_log'].append({
                        "job function": "Warehouse Page",
                        "date time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "activity": f"Sent items to warehouse: {item}",
                        "number": len(st.session_state['activity_log']) + 1,
                    })
                        

            if send :
                st.success("Thank you for demo")

    if submitted and item:
        item_data = df[df['item_id'] == item]
        stock_level = item_data['stock_level'].values[0]
        lead_time = item_data['lead_time_days'].values[0] 
        reorder_point = item_data['reorder_point'].values[0]
        new_ROP = item_data['ROP'].values[0]
        forecast_7d = item_data['forecasted_demand_next_7d'].values[0]
        # Distribute forecast over 7 days
        daily_forecast = forecast_7d / 7 if forecast_7d else 0
        days = list(range(8))
        stock_projection = [stock_level]
        shortage_day = None
        for i in range(1, 8):
            next_stock = stock_projection[-1] - daily_forecast
            stock_projection.append(next_stock)
            if shortage_day is None and next_stock < new_ROP:
                shortage_day = i
        # Show result as text
        st.write(f"**Item:** {item} / **Category:** {item_data['category'].values[0]} / **Inventory Tier:** {item_data['Inventory_Tier'].values[0]}")
        st.write(f"**Current Stock Level:** {stock_level}")
        # Chart and metric card
        chart_col, metric_col = st.columns([3,1])
        with chart_col:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=days,
                y=stock_projection,
                marker_color='rgba(30, 144, 255, 0.7)',
                name='Projected Stock'
            ))
            fig.add_trace(go.Scatter(
                x=days,
                y=[new_ROP]*8,
                mode='lines',
                line=dict(color='red', dash='dash'),
                name='Dynamic Reorder Point'
            ))
            fig.add_trace(go.Scatter(
                x=days,
                y=[reorder_point]*8,
                mode='lines',
                line=dict(color='orange', dash='dash'),
                name='Old Reorder Point'
            ))
            fig.update_layout(
                title='Stock Level Projection (7 Days)',
                xaxis_title='Day',
                yaxis_title='Stock Level',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                showlegend=True,
                margin=dict(l=10, r=10, t=30, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)
        with metric_col:
            rop_value = item_data['ROP'].values[0] if 'ROP' in item_data.columns else None
            delta_rop = None
            if rop_value is not None:
                delta_rop = rop_value - reorder_point
                st.metric(label="Dynamic ROP Value", value=f"{rop_value:.2f}", delta=f"{delta_rop:+.2f}", border=True)
            else:
                st.metric(label="Dynamic ROP Value", value="N/A")
            # Lead time metric card
            st.metric(label="Lead Time (days)", value=lead_time,border=True)
            # Shortage day metric card
            if shortage_day is not None:
                st.metric(label="Shortage Occurs (Day)", value=shortage_day, border=True)
            else:
                st.metric(label="Shortage Occurs (Day)", value="No Shortage", border=True)