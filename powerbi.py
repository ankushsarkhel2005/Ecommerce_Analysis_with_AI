"""
powerbi.py - Power BI Integration & Analytics Data Engine

This module provides:
1. Power BI configuration management (Embed URL, Report ID, Workspace ID).
2. Ground-truth DAX measures definitions mapped to actual columns in ecommerce_db.orders.
3. Live aggregated analytics data endpoints for visual charts, KPIs, and interactive slicers.
"""

import os
import json
from dotenv import load_dotenv
import database

# Load environment configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_FILE, override=True)


def get_powerbi_config():
    """
    Returns Power BI embedding configuration from environment variables.
    Supports:
    - Direct Public Web Embed URL (Publish to Web iframe)
    - Power BI Embedded Service Principal credentials (Workspace ID, Report ID)
    """
    embed_url = os.getenv("POWERBI_EMBED_URL", "").strip()
    report_id = os.getenv("POWERBI_REPORT_ID", "").strip()
    workspace_id = os.getenv("POWERBI_WORKSPACE_ID", "").strip()
    tenant_id = os.getenv("POWERBI_TENANT_ID", "").strip()
    client_id = os.getenv("POWERBI_CLIENT_ID", "").strip()

    # Determine active embed mode
    if embed_url:
        embed_mode = "direct_url"
    elif report_id and workspace_id:
        embed_mode = "service_principal"
    else:
        embed_mode = "visualizer"  # Default built-in interactive dashboard

    return {
        "embed_mode": embed_mode,
        "embed_url": embed_url,
        "report_id": report_id,
        "workspace_id": workspace_id,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "is_configured": bool(embed_url or (report_id and workspace_id)),
    }


def get_dax_measures():
    """
    Returns the complete list of DAX measures tailored for Clean_Ecommerce (orders table).
    These can be directly copy-pasted into Power BI Desktop.
    """
    return [
        {
            "name": "Total Sales",
            "formula": "Total Sales = SUM(orders[Sales])",
            "category": "Sales & Revenue",
            "format": "₹#,##0.00",
            "description": "Calculates total gross revenue across all transactions."
        },
        {
            "name": "Total Orders",
            "formula": "Total Orders = DISTINCTCOUNT(orders[Order_ID])",
            "category": "Orders",
            "format": "#,##0",
            "description": "Counts total unique order transactions."
        },
        {
            "name": "Total Quantity",
            "formula": "Total Quantity = SUM(orders[Qty])",
            "category": "Sales & Revenue",
            "format": "#,##0",
            "description": "Calculates total volume of product units sold."
        },
        {
            "name": "Total Customers",
            "formula": "Total Customers = DISTINCTCOUNT(orders[Customer_Name])",
            "category": "Customer Analytics",
            "format": "#,##0",
            "description": "Counts total unique customer profiles."
        },
        {
            "name": "Average Order Value (AOV)",
            "formula": "Average Order Value = DIVIDE([Total Sales], [Total Orders], 0)",
            "category": "Sales & Revenue",
            "format": "₹#,##0.00",
            "description": "Measures the average revenue generated per transaction."
        },
        {
            "name": "Average Discount",
            "formula": "Average Discount = AVERAGE(orders[Discount])",
            "category": "Pricing & Promotions",
            "format": "0.0%",
            "description": "Calculates average discount percentage offered across orders."
        },
        {
            "name": "Total Net Revenue",
            "formula": "Total Net Revenue = SUM(orders[Net_Amount])",
            "category": "Sales & Revenue",
            "format": "₹#,##0.00",
            "description": "Revenue generated after subtracting promotional discounts."
        },
        {
            "name": "Total Profit",
            "formula": "Total Profit = SUM(orders[Profit])",
            "category": "Profitability",
            "format": "₹#,##0.00",
            "description": "Cumulative gross profit across all product sales."
        },
        {
            "name": "Profit Margin %",
            "formula": "Profit Margin % = DIVIDE([Total Profit], [Total Sales], 0)",
            "category": "Profitability",
            "format": "0.0%",
            "description": "Overall profit margin percentage."
        },
        {
            "name": "Category Sales %",
            "formula": "Category Sales % = DIVIDE([Total Sales], CALCULATE([Total Sales], ALL(orders[Category])), 0)",
            "category": "Category Analysis",
            "format": "0.0%",
            "description": "Calculates category contribution percentage to overall sales."
        },
        {
            "name": "Top Product Sales",
            "formula": "Top Product Sales = CALCULATE([Total Sales], TOPN(1, ALL(orders[Product]), [Total Sales], DESC))",
            "category": "Product Analytics",
            "format": "₹#,##0.00",
            "description": "Revenue generated by the #1 best-selling product."
        }
    ]


def get_powerbi_dashboard_data(category_filter=None, city_filter=None, status_filter=None):
    """
    Queries the database and returns structured analytics data for the dashboard visuals,
    supporting interactive multi-dimension filtering.
    """
    table = "orders"
    where_clauses = []
    
    if category_filter and category_filter.lower() != "all":
        safe_cat = category_filter.replace("'", "''")
        where_clauses.append(f"Category = '{safe_cat}'")
        
    if city_filter and city_filter.lower() != "all":
        safe_city = city_filter.replace("'", "''")
        where_clauses.append(f"City = '{safe_city}'")
        
    if status_filter and status_filter.lower() != "all":
        safe_status = status_filter.replace("'", "''")
        where_clauses.append(f"Order_Status = '{safe_status}'")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    # 1. Overall KPIs
    kpi_sql = f"""
        SELECT 
            COALESCE(SUM(Sales), 0) AS total_sales,
            COALESCE(SUM(Net_Amount), 0) AS total_net_sales,
            COALESCE(SUM(Profit), 0) AS total_profit,
            COALESCE(SUM(Qty), 0) AS total_quantity,
            COUNT(DISTINCT Order_ID) AS total_orders,
            COUNT(DISTINCT Customer_Name) AS total_customers,
            COALESCE(AVG(Discount), 0) AS avg_discount,
            COALESCE(AVG(Sales), 0) AS avg_order_value
        FROM {table}
        {where_sql};
    """
    kpi_res = database.execute_query(kpi_sql)
    kpis = kpi_res["rows"][0] if kpi_res["rows"] else {}

    # 2. Monthly Revenue Trend
    month_sql = f"""
        SELECT 
            Order_Month,
            SUM(Sales) AS sales,
            SUM(Profit) AS profit,
            COUNT(*) AS orders
        FROM {table}
        {where_sql}
        GROUP BY Order_Month
        ORDER BY sales DESC;
    """
    month_res = database.execute_query(month_sql)
    monthly_trend = month_res["rows"]

    # Month ordering helper
    month_order = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6, 
                   "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12}
    monthly_trend.sort(key=lambda m: month_order.get(m.get("Order_Month", ""), 99))

    # 3. Category Breakdown
    cat_sql = f"""
        SELECT 
            Category,
            SUM(Sales) AS total_sales,
            SUM(Profit) AS total_profit,
            COUNT(*) AS total_orders,
            SUM(Qty) AS total_qty,
            ROUND(AVG(Sales), 2) AS avg_order_value
        FROM {table}
        {where_sql}
        GROUP BY Category
        ORDER BY total_sales DESC;
    """
    cat_res = database.execute_query(cat_sql)
    categories = cat_res["rows"]

    # Compute category contribution %
    tot_sales = float(kpis.get("total_sales") or 1)
    for c in categories:
        c_sales = float(c.get("total_sales") or 0)
        c["share_pct"] = round((c_sales / tot_sales) * 100, 1) if tot_sales > 0 else 0

    # 4. Top Products by Revenue
    prod_sql = f"""
        SELECT 
            Product,
            Category,
            SUM(Sales) AS total_sales,
            SUM(Qty) AS total_qty,
            SUM(Profit) AS total_profit,
            COUNT(*) AS total_orders
        FROM {table}
        {where_sql}
        GROUP BY Product, Category
        ORDER BY total_sales DESC
        LIMIT 10;
    """
    prod_res = database.execute_query(prod_sql)
    top_products = prod_res["rows"]

    # 5. Geographic Breakdown (Top Cities)
    city_sql = f"""
        SELECT 
            City,
            State,
            SUM(Sales) AS total_sales,
            COUNT(*) AS total_orders,
            SUM(Qty) AS total_qty
        FROM {table}
        {where_sql}
        GROUP BY City, State
        ORDER BY total_sales DESC
        LIMIT 8;
    """
    city_res = database.execute_query(city_sql)
    top_cities = city_res["rows"]

    # 6. Payment Modes Breakdown
    payment_sql = f"""
        SELECT 
            Payment_Mode,
            COUNT(*) AS order_count,
            SUM(Sales) AS total_sales
        FROM {table}
        {where_sql}
        GROUP BY Payment_Mode
        ORDER BY total_sales DESC;
    """
    pay_res = database.execute_query(payment_sql)
    payment_modes = pay_res["rows"]

    # 7. Customer Analysis (Top 5 Customers by Revenue)
    cust_sql = f"""
        SELECT 
            Customer_Name,
            City,
            COUNT(*) AS order_count,
            SUM(Sales) AS total_spent
        FROM {table}
        {where_sql}
        GROUP BY Customer_Name, City
        ORDER BY total_spent DESC
        LIMIT 5;
    """
    cust_res = database.execute_query(cust_sql)
    top_customers = cust_res["rows"]

    # 8. Slicer Options
    slicer_cat_res = database.execute_query(f"SELECT DISTINCT Category FROM {table} ORDER BY Category;")
    slicer_city_res = database.execute_query(f"SELECT DISTINCT City FROM {table} ORDER BY City;")
    slicer_status_res = database.execute_query(f"SELECT DISTINCT Order_Status FROM {table} ORDER BY Order_Status;")

    slicer_options = {
        "categories": [r["Category"] for r in slicer_cat_res.get("rows", []) if r.get("Category")],
        "cities": [r["City"] for r in slicer_city_res.get("rows", []) if r.get("City")],
        "statuses": [r["Order_Status"] for r in slicer_status_res.get("rows", []) if r.get("Order_Status")],
    }

    return {
        "kpis": kpis,
        "monthly_trend": monthly_trend,
        "categories": categories,
        "top_products": top_products,
        "top_cities": top_cities,
        "payment_modes": payment_modes,
        "top_customers": top_customers,
        "slicer_options": slicer_options,
        "filters_applied": {
            "category": category_filter or "All",
            "city": city_filter or "All",
            "status": status_filter or "All",
        }
    }
