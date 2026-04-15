import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import networkx as nx
import os
import random

st.set_page_config(page_title="Delivery Route Optimizer", layout="wide")
st.title("Warehouse Delivery & Routing System")

# ==========================================
# 1. WAREHOUSE GRID & OBSTACLE SETUP
# ==========================================
MAX_X = 105
MAX_Y = 60

# Define blocks (x_min, x_max, y_min, y_max)
# Aisles are implicitly created by the gaps between these blocks
OBSTACLES = {
    "Office (Red)": (5, 15, 35, 55),
    "Zone A Top":   (20, 30, 35, 55),
    "Zone B Top":   (40, 50, 35, 55),
    "Zone C Top":   (60, 70, 35, 55),
    "Zone D Top":   (80, 90, 35, 55),
    "Depot (Black)":(5, 15, 5, 25),
    "Zone A Bot":   (20, 30, 5, 25),
    "Zone B Bot":   (40, 50, 5, 25),
    "Zone C Bot":   (60, 70, 5, 25),
    "Zone D Bot":   (80, 90, 5, 25),
}

def is_blocked(x, y):
    """Checks if a coordinate is inside any of the warehouse racks/buildings, except Depot."""
    for name, (xmin, xmax, ymin, ymax) in OBSTACLES.items():
        if name == "Depot (Black)":
            continue  # Do not block depot area
        if xmin < x < xmax and ymin < y < ymax:
            return True
    return False

# Build the Walkable Grid Graph
@st.cache_resource # Cache to speed up re-runs
def build_warehouse_graph():
    G = nx.grid_2d_graph(MAX_X, MAX_Y)
    # Remove all nodes that fall inside the obstacles (walls/racks)
    nodes_to_remove = [node for node in G.nodes if is_blocked(node[0], node[1])]
    G.remove_nodes_from(nodes_to_remove)
    return G

G = build_warehouse_graph()
valid_aisle_nodes = set(G.nodes)

def get_nearest_aisle(x, y):
    """Snaps an item's (x,y) location to the nearest valid driving aisle."""
    if (x, y) in valid_aisle_nodes:
        return (x, y)
    # Find closest node using Manhattan distance
    closest_node = min(valid_aisle_nodes, key=lambda node: abs(node[0]-x) + abs(node[1]-y))
    return closest_node

# Forklift starting position (in the aisle just outside the Depot)
# Forklift starting position (center of Depot area)
# Depot (Black): (5, 15, 5, 25) → center is ((5+15)//2, (5+25)//2) = (10, 15)
DEPOT_AISLE_COORD = (10, 15)


# ==========================================
# 2. ORDER PROCESSING UI
# ==========================================
sales_history = st.session_state.get('sales_history', [])

# Build DataFrame for display
orders_df = pd.DataFrame([
    {"PO Number": order["po_number"], "Customer": order["customer_name"], "Date": order["date_time"]}
    for order in sales_history
])
st.markdown("### Pending Orders")
selected_idx = st.selectbox("Select Order to Fulfill", options=orders_df.index, format_func=lambda i: f"{orders_df.loc[i, 'PO Number']} ({orders_df.loc[i, 'Customer']})")

selected_order = sales_history[selected_idx]
order_items = pd.DataFrame(selected_order['items'])

# Load User Data for Coordinates (Mocked if file not found)
DATA_DIR = os.path.join(os.path.dirname(__file__), '..','..', 'data')
try:
    user_files = [f for f in os.listdir(DATA_DIR) if f.endswith('modified_user.csv')]
    df_items = pd.read_csv(os.path.join(DATA_DIR, user_files[0])) if user_files else pd.DataFrame()
except FileNotFoundError:
    df_items = pd.DataFrame()

if not order_items.empty:

    merged = order_items.merge(df_items, left_on='item', right_on='item_id', how='left')
    if 'quantity' not in merged.columns: merged['quantity'] = 1 
        
    # ==========================================
    # 3. ADVANCED BATCHING ENGINE (Dynamic Splitting)
    # ==========================================
    FORKLIFT_CAPACITY = 100
    trips = []
    current_trip = []
    current_weight = 0

    for _, row in merged.iterrows():
        remaining_qty = row['amount']
        
        while remaining_qty > 0:
            space_left = FORKLIFT_CAPACITY - current_weight
            pick_qty = min(remaining_qty, space_left)
            
            trip_item = row.to_dict()
            trip_item['pick_qty'] = pick_qty 
            
            # Get the exact item location, then snap it to the walkable grid
            raw_x, raw_y = (trip_item.get('x', 0), trip_item.get('y', 0))
            if pd.isna(raw_x): raw_x = 0
            if pd.isna(raw_y): raw_y = 0
            trip_item['aisle_coord'] = get_nearest_aisle(raw_x, raw_y)
            
            current_trip.append(trip_item)
            current_weight += pick_qty
            remaining_qty -= pick_qty
            
            if current_weight >= FORKLIFT_CAPACITY:
                trips.append(current_trip)
                current_trip = []
                current_weight = 0

    if current_trip:
        trips.append(current_trip)

    # ==========================================
    # 4. GRID-BASED ROUTING ENGINE (Dijkstra)
    # ==========================================
    all_trip_paths = []
    total_overall_distance = 0
    
    st.markdown("---")
    st.markdown("### Optimization & Fulfillment Results")

    for trip_idx, trip in enumerate(trips):
        unvisited = list(range(len(trip)))
        current_coord = DEPOT_AISLE_COORD
        path_coords = [DEPOT_AISLE_COORD]
        trip_distance = 0

        while unvisited:
            # Find the closest item in the remaining trip list
            shortest_dist = float('inf')
            best_target_idx = -1
            best_path_to_target = []
            
            for idx in unvisited:
                target_coord = trip[idx]['aisle_coord']
                # Calculate shortest grid path avoiding buildings
                path = nx.dijkstra_path(G, current_coord, target_coord)
                dist = len(path) - 1
                
                if dist < shortest_dist:
                    shortest_dist = dist
                    best_target_idx = idx
                    best_path_to_target = path
                    
            # Move forklift to the best item
            trip_distance += shortest_dist
            # Append the actual step-by-step turns to the path
            path_coords.extend(best_path_to_target[1:]) 
            current_coord = trip[best_target_idx]['aisle_coord']
            unvisited.remove(best_target_idx)

        # Return to Depot
        return_path = nx.dijkstra_path(G, current_coord, DEPOT_AISLE_COORD) 
        trip_distance += (len(return_path) - 1)
        path_coords.extend(return_path[1:])
        
        all_trip_paths.append(path_coords)
        total_overall_distance += trip_distance

    # ==========================================
    # 5. ROUTE SUMMARY & VALIDATION TABLE
    # ==========================================
    # Calculate electric used for each item (unit: kWh)
    KWH_PER_UNIT =  0.02 # ref value
    route_summary = []
    for trip_idx, trip in enumerate(trips):
        trip_path = all_trip_paths[trip_idx] if trip_idx < len(all_trip_paths) else []
        # Distribute path length to items in trip (simple: equal split)
        path_len = len(trip_path) - 1 if trip_path else 0
        electric_per_item = (path_len * KWH_PER_UNIT) / len(trip) if trip else 0
        unit_per_item = (path_len) / len(trip) if trip else 0
        for item in trip:
            route_summary.append({
                "Route": f"Trip {trip_idx + 1}",
                "Item": item['item'],
                "Pick Qty": item['pick_qty'],
                "Zone": item.get('zone', 'N/A'),
                "Unit (meters)": round(unit_per_item, 2),
                "Electric Used (kWh)": round(electric_per_item, 3)
            })
    summary_df = pd.DataFrame(route_summary)
    total_electric = summary_df['Electric Used (kWh)'].sum()
    if total_electric < 5:
        color = 'green'
    elif total_electric < 8:
        color = 'orange'
    else:
        color = 'red'
    st.markdown(f"Battery Consumption Estimate: :{color}[{total_electric:.2f} kWh]  / 10 kWh</span>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    with col2:
        total_ordered = merged['amount'].sum()
        total_planned = summary_df['Pick Qty'].sum()
        if total_ordered == total_planned:
            st.success(f"**100% Solved!**\n\nOrdered: {total_ordered}\nPlanned: {total_planned}\nTotal Distance: {total_overall_distance} steps")
        else:
            st.error("Fulfillment Mismatch!")

    # ==========================================
    # 6. WAREHOUSE MAP VISUALIZATION (Plotly)
    # ==========================================
    fig = go.Figure()
    
    # Draw Obstacles (Buildings/Racks) as shapes (move to back)
    for name, (xmin, xmax, ymin, ymax) in OBSTACLES.items():
        color = "Red" if "Office" in name else "Black" if "Depot" in name else "#2c5282"
        fig.add_shape(type="rect", x0=xmin, y0=ymin, x1=xmax, y1=ymax,
                      fillcolor=color, line=dict(color="white", width=1), opacity=0.8, layer="below")
        # Add labels to boxes (keep on top)
        if name == "Depot (Black)":
            continue
        else :
            fig.add_trace(go.Scatter(x=[(xmin+xmax)/2], y=[(ymin+ymax)/2], mode="text",
                                 text=[name], textfont=dict(color="white"), showlegend=False))

    # Plot Target Items (pickup stops as squares) and pickup stops as circles
    pickup_coords = []
    for _, row in merged.iterrows():
        raw_x = row.get('x', 0) if pd.notna(row.get('x')) else 0
        raw_y = row.get('y', 0) if pd.notna(row.get('y')) else 0
        pickup_coords.append((raw_x, raw_y))
        fig.add_trace(go.Scatter(
            x=[raw_x], y=[raw_y], mode='markers',
            marker=dict(size=12, symbol='square', color='gold', line=dict(width=2, color='black')),
            name=f"{row['item']}", text=[f"{row['item']} (Qty: {row['amount']})"], hoverinfo="text"
        ))

    # Plot Forklift Routes with fewer arrows, lower opacity, and circles at pickup points
    colors = ['#00FF00', '#FF00FF', '#00FFFF', '#FFA500']
    pickup_set = set(pickup_coords) if 'pickup_coords' in locals() else set()
    for i, path in enumerate(all_trip_paths):
        x_coords = [p[0] for p in path]
        y_coords = [p[1] for p in path]
        color = colors[i % len(colors)]
        # Draw the route as a line
        fig.add_trace(go.Scatter(
            x=x_coords, y=y_coords, mode='lines',
            line=dict(width=4, color=color, dash='solid'),
            opacity=0.5,
            name=f"Trip {i+1} Path"
        ))

        # Add only two arrows: one for outgoing, one for incoming, both near depot but outside
        depot_x, depot_y = DEPOT_AISLE_COORD
        valid_indices = [j for j in range(1, len(x_coords))
                        if not (5 <= x_coords[j] <= 15 and 5 <= y_coords[j] <= 25)]
        if valid_indices:
            j = random.choice(valid_indices)
            x0, y0 = x_coords[j-1], y_coords[j-1]
            x1, y1 = x_coords[j], y_coords[j]
            dx, dy = x1 - x0, y1 - y0
            norm = (dx**2 + dy**2) ** 0.5
            if norm != 0:
                arrow_size = 2
                dxn, dyn = dx / norm, dy / norm
                xb, yb = x1 - dxn * arrow_size, y1 - dyn * arrow_size
                fig.add_annotation(
                    x=x1, y=y1, ax=xb, ay=yb,
                    xref='x', yref='y', axref='x', ayref='y',
                    showarrow=True, arrowhead=3, arrowsize=1.5, arrowwidth=2, arrowcolor=color, opacity=0.8
                )

 

    # Add forklift image at DEPOT_AISLE_COORD
    import base64
    forklift_path = os.path.join(os.path.dirname(__file__), '..', 'components', 'forklift.png')
    if os.path.exists(forklift_path):
        with open(forklift_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
        fig.add_layout_image(
            dict(
                source=f"data:image/png;base64,{encoded}",
                x=DEPOT_AISLE_COORD[0], y=DEPOT_AISLE_COORD[1],
                sizex=5, sizey=5,
                xref="x", yref="y",
                xanchor="center", yanchor="middle",
                layer="above"
            )
        )
    fig.update_layout(
        title="Forklift Routing Simulation",
        xaxis=dict(range=[0, MAX_X], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[0, MAX_Y], showgrid=False, zeroline=False, visible=False),
        height=700, template="plotly_dark",
        margin=dict(l=10, r=10, t=40, b=10)
    )
    
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No item data found to route.")