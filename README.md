# Intelligent Warehouse Optimization

This project mainly to applied the in-class knowledge from Algorithm and Optimization class where simulates a workflow in a manufacturing and warehouse as environment.

By acting as a centralized mock-up application built on Streamlit, this tool tests and simulates end-to-end operational improvements. Specifically, it tackles two major optimization challenges:
1. **Delivery Routing Efficiency:** Streamlining the picking process for operators who face large order lists and lack a clear starting point.
2. **Inventory Management:** Shifting from static inventory thresholds to a dynamically calculated Reorder Point (ROP) to prevent stockouts and optimize purchasing.

---

## ⚙️ Project Overview and Core Optimizations

Below is the diagram illustrating how the workflow moves from Sales input to the parallel actions taken by the Delivery and Warehouse teams.

<img src="./streamlit_app/components/Workflow Diagram.jpeg" alt="Workflow Diagram" style="width:100%;max-width:1200px;display:block;margin:auto;"/>

### 1. Delivery & Routing Optimization
When an order is entered from sales, the delivery operator is often faced with the pain point of determining the most efficient picking sequence. 
* **Shortest Path Calculation:** The system utilizes Dijkstra's algorithm to compute the absolute shortest path for the required routing pickup and items to be picked.
* **Energy Estimation:** Alongside the route, the system calculates the electricity utilized for that specific path. 
* **Outcome:** This provides delivery operators with a clear, fast automated schedule, making route planning and energy management highly efficient.

### 2. Dynamic Inventory Reorder Point (ROP)
To assist the warehouse operators, the system recalculates the inventory Reorder Point using statistical techniques.
* **Dynamic Formula:** ROP is evaluated based on usage, lead time, and a calculated safety stock.
* **Forecasting Integration:** The application cross-references the ROP against a 7-day high-demand forecast provided within the dataset, allowing the warehouse operator to anticipate potential stockouts and make informed purchasing decisions.
* **Outcome:** The Streamlit dashboard visualizes these metrics, empowering the warehouse operator to make decision faster and more informed.


---

## 🖼️ Demo Screenshots

<div align="center">
    <text> Warehouse Page Demo </text>
    <img src="./streamlit_app/components/warehouse_page.png" alt="Warehouse Page Demo" style="width:100%;max-width:900px;margin-bottom:24px;"/>
    <br>
    <text> Delivery Page Demo </text>
    <img src="./streamlit_app/components/delivery.png" alt="Delivery Page Demo" style="width:100%;max-width:900px;margin-bottom:24px;"/>
    <br>
    <img src="./streamlit_app/components/delivery2.png" alt="Delivery Route Demo" style="width:100%;max-width:900px;"/>
</div>

---

## ⚠️ Assumptions & Constraints

To simplify the scope of the simulation, the following constraints and assumptions have been applied to the model:

* **Capacity Restrictions:** This version stricts limits the number of items instead of weight for forklift can carry per route.
* **Item Spawn Points:** Because exact physical layout data is not provided in the raw dataset, the spawn points (locations) of items are generated sequently in grid layout to mimic a realistic warehouse floor.
* **Static Mockup Variables:** While the ROP is calculated using dynamic statistical methods, the Streamlit mockup currently processes daily demand and lead time as static data points. The ROP will not continuously update on its own in this specific demo environment without new data ingestion.
* **Further Improvements:** This systemcould include more complex constraints such as weight limits, time windows for deliveries and integrat time constraints to model, and real-time data updates for ROP calculations.

---


## 🎓 Courses Applied

| Course | Application |
|--------|-------------|
| **ADS** — Algorithms & Data Structures | Graph construction, Dijkstra pathfinding |
| **Opt** — Operations Research / Optimization | Linear programming model |

---

## Progression
- [x] Build a clear structured workflow
    - [x] Create useable POC version.  
[OnProgress] Refactor code by using OOP

---

## 🚀 Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/billythanapong/Warehouse-operation-optimization.git
cd Warehouse-operation-optimization

# 2. Install dependencies
pip install poetry
poetry install

# 3. Run the Streamlit app
streamlit run streamlit_app/app.py
```

---

## 📁 Project Structure

```
├── data/
│   └── logistic_dataset_modified.csv   # Modified dataset with x,y coordinates and RFM segments         
|   └── logistic_dataset.csv            # Raw warehouse dataset
├── notebooks/
│   └── data_manipulation.ipynb            # Data cleaning, RFM segmentation, dynamic ROP calculations
├── streamlit_app/
│   ├── app.py            # Safety stock & ROP calculations
│   ├── pages/                   # Warehouse graph & Dijkstra
│        ├── delivery.py           # page for delivery operators
│        ├── warehouse.py           # page for warehouse operators
│        └── sales.py              # page for sales operators                         
├── pyproject.toml # python and dependency management
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Tools |
|-------|-------|
| Data & Statistics | Python, Pandas, NumPy, SciPy |
| Visualization | Matplotlib, Seaborn, Plotly, Tableau |
| Graph / Routing | NetworkX (Dijkstra) |
| UI | Streamlit |
| Version Control | Git / GitHub |

---





