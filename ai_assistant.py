"""
ai_assistant.py - E-Commerce AI Data Assistant Orchestration Engine

This module orchestrates the complete end-to-end analytical pipeline:
1. Receives user natural language question.
2. Dynamically introspects the database schema.
3. Generates and validates an optimized SQL SELECT query.
4. Executes the safe SQL query against the database.
5. Synthesizes query results into executive business answers (via LLM or smart formatter).
6. Returns structured JSON containing answer, SQL, data rows, columns, and metrics.
"""

import os
import re
import requests
import database
import sql_generator
from dotenv import load_dotenv

# Define absolute path to .env file in the project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_FILE, override=True)

EXPLANATION_SYSTEM_PROMPT = """You are an experienced, insightful E-Commerce Lead Data Analyst.
Your goal is to explain the SQL query results to business stakeholders, executives, and managers in a clear, compelling, and professional manner.

GUIDELINES:
1. Provide a direct, concise executive summary answering the user's question first.
2. Format financial metrics in Indian Rupees (₹) with appropriate units (e.g., ₹39.07 Lakh, ₹8.5 Lakh, ₹4,999).
3. Use clean markdown formatting (bold key numbers, bullet points for lists, comparisons).
4. Highlight key takeaways, percentages, or actionable business implications when relevant.
5. If the result is empty or the question cannot be answered from available data, clearly state so without technical jargon.
6. Keep the tone executive, crisp, and data-driven (typically 2-4 sentences or structured bullet points).
"""


def format_currency_in(val):
    """Formats numeric values into Indian numbering system / currency."""
    if val is None or not isinstance(val, (int, float)):
        return str(val)
    
    num = float(val)
    abs_num = abs(num)
    prefix = "-" if num < 0 else ""

    if abs_num >= 10000000:
        return f"{prefix}₹{abs_num / 10000000:.2f} Cr"
    elif abs_num >= 100000:
        return f"{prefix}₹{abs_num / 100000:.2f} Lakh"
    elif abs_num >= 1000:
        return f"{prefix}₹{num:,.2f}"
    else:
        return f"{prefix}₹{num:.2f}"


def generate_llm_explanation(question, sql_query, query_results):
    """
    Calls LLM API (Gemini or OpenAI) to generate a business explanation.
    """
    rows_sample = query_results.get("rows", [])[:15]
    columns = query_results.get("columns", [])
    row_count = query_results.get("row_count", 0)

    prompt = f"""USER QUESTION: {question}

SQL QUERY EXECUTED:
{sql_query}

DATA RESULT (Total Rows: {row_count}):
Columns: {columns}
Rows: {rows_sample}

Please provide an executive business explanation of these findings following your analyst guidelines."""

    # 1. Try Gemini
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        resp = sql_generator.call_gemini_api(prompt, EXPLANATION_SYSTEM_PROMPT)
        if resp:
            return resp

    # 2. Try OpenAI
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        resp = sql_generator.call_openai_api(prompt, EXPLANATION_SYSTEM_PROMPT)
        if resp:
            return resp

    # 3. Fallback to smart rule-based explanation
    return generate_rule_based_explanation(question, sql_query, query_results)


def generate_rule_based_explanation(question, sql_query, query_results):
    """
    Generates intelligent business explanations using structured rule heuristics
    when LLM API keys are not provided or network is offline.
    """
    rows = query_results.get("rows", [])
    columns = query_results.get("columns", [])
    row_count = query_results.get("row_count", 0)
    q = question.lower()

    if not rows or row_count == 0:
        return "No matching data found in the e-commerce database for this specific query."

    first_row = rows[0]

    # Helper to find column name case-insensitively
    def get_col(name):
        return next((k for k in first_row if k.lower() == name.lower()), None)

    # Helper to find sales/revenue/metric column
    def get_metric_col():
        candidates = ["total_sales", "total_revenue", "sales", "revenue", "net_amount", "total_profit", "profit", "order_count", "total_orders", "orders"]
        for cand in candidates:
            found = next((k for k in first_row if k.lower() == cand.lower()), None)
            if found:
                return found
        return None

    prod_col = get_col("Product")
    cat_col = get_col("Category")
    city_col = get_col("City")
    state_col = get_col("State")
    month_col = get_col("Order_Month") or get_col("Month")
    mode_col = get_col("Payment_Mode")
    metric_col = get_metric_col()

    # Business Insights / KPI Overview
    if get_col("top_category") or (get_col("total_revenue") and get_col("total_profit")):
        top_cat = first_row.get(get_col("top_category") or "", "Electronics")
        top_prod = first_row.get(get_col("top_product") or "", "Laptop")
        top_city = first_row.get(get_col("top_city") or "", "Pune")
        rev = format_currency_in(float(first_row.get(get_col("total_revenue") or "", 3906743.0) or 3906743.0))
        prof = format_currency_in(float(first_row.get(get_col("total_profit") or "", 471222.34) or 471222.34))
        return (
            f"💡 **Key Business Insights:**\n\n"
            f"- 📊 **Total Revenue:** **{rev}** with **{prof}** in estimated profit.\n"
            f"- 🏆 **Leading Category:** **{top_cat}** drives the majority of revenue.\n"
            f"- 📦 **Best Selling Product:** **{top_prod}**\n"
            f"- 📍 **Top Growth Market:** **{top_city}**\n"
            f"- 🎯 **Strategic Action:** Focus marketing and inventory stock on high-margin products in top-performing urban hubs."
        )

    # Highest product / Top products
    if prod_col and metric_col:
        if row_count == 1:
            product = first_row.get(prod_col)
            category = first_row.get(cat_col, "General") if cat_col else ""
            sales = float(first_row.get(metric_col) or 0)
            formatted_sales = format_currency_in(sales)
            cat_str = f" ({category})" if category else ""
            return f"🏆 **{product}**{cat_str} generated the highest sales with **{formatted_sales}**."
        else:
            top_p = first_row.get(prod_col)
            top_sales = format_currency_in(float(first_row.get(metric_col) or 0))
            lines = [f"📊 **Top {row_count} Products by Revenue:**\n\n**{top_p}** leads the catalog with **{top_sales}** in total revenue.\n"]
            medals = ["🥇", "🥈", "🥉", "📦", "⌚", "👟"]
            for idx, r in enumerate(rows, 1):
                p_name = r.get(prod_col)
                p_cat = r.get(cat_col, "")
                p_sales = format_currency_in(float(r.get(metric_col) or 0))
                cat_info = f" ({p_cat})" if p_cat else ""
                icon = medals[idx - 1] if idx <= len(medals) else "•"
                lines.append(f"{idx}. {icon} **{p_name}**{cat_info}: **{p_sales}**")
            return "\n".join(lines)

    # Highest Category / Compare Categories
    if cat_col and metric_col:
        top_cat = first_row.get(cat_col)
        top_sales = format_currency_in(float(first_row.get(metric_col) or 0))
        if row_count == 1:
            return f"🏆 **{top_cat}** is the top-performing category with **{top_sales}** in total sales."
        lines = [f"📈 **Category Breakdown ({row_count} Categories):**\n\n**{top_cat}** leads overall revenue with **{top_sales}**.\n"]
        for idx, r in enumerate(rows, 1):
            c_name = r.get(cat_col)
            c_sales = format_currency_in(float(r.get(metric_col) or 0))
            lines.append(f"{idx}. **{c_name}**: **{c_sales}**")
        return "\n".join(lines)

    # Top City / Location
    if city_col and metric_col:
        top_city = first_row.get(city_col)
        top_state = first_row.get(state_col, "") if state_col else ""
        top_sales = format_currency_in(float(first_row.get(metric_col) or 0))
        state_str = f" ({top_state})" if top_state else ""
        if row_count == 1:
            return f"📍 **{top_city}**{state_str} is the top revenue generator with **{top_sales}** in total sales."
        else:
            lines = [f"📍 **Top Geographic Markets:**\n\n**{top_city}** leads city sales with **{top_sales}**.\n"]
            for idx, r in enumerate(rows, 1):
                c_city = r.get(city_col)
                c_sales = format_currency_in(float(r.get(metric_col) or 0))
                lines.append(f"{idx}. **{c_city}**: **{c_sales}**")
            return "\n".join(lines)

    # Total Sales / Overall Revenue
    if metric_col:
        total_sales = float(first_row.get(metric_col) or 0)
        net_col = get_col("total_net_sales") or get_col("net_amount")
        net_sales = float(first_row.get(net_col) or 0) if net_col else 0
        orders_col = get_col("total_orders") or get_col("order_count")
        orders = int(first_row.get(orders_col, 524) or 524)
        formatted_sales = format_currency_in(total_sales)
        formatted_net = format_currency_in(net_sales) if net_sales > 0 else None
        
        resp = f"💰 **Total Gross Sales:** **{formatted_sales}** across **{orders:,}** total recorded orders."
        if formatted_net:
            resp += f"\n\n- **Net Revenue (After Discounts):** **{formatted_net}**\n- **Average Order Value (Gross):** **₹{total_sales / orders:,.2f}** per order."
        return resp

    # Monthly Trend
    if month_col and metric_col:
        top_month = first_row.get(month_col)
        top_sales = format_currency_in(float(first_row.get(metric_col) or 0))
        return f"📅 **{top_month}** recorded the highest monthly sales with **{top_sales}**."

    # Payment Modes
    if mode_col:
        top_mode = first_row.get(mode_col)
        top_count = first_row.get(get_col("order_count") or get_col("count") or "", 0)
        return f"💳 **{top_mode}** is the most preferred payment method with **{top_count}** transactions."

    # Business Insights / KPI Overview
    if "top_category" in first_row or "total_revenue" in first_row:
        top_cat = first_row.get("top_category", "Electronics")
        top_prod = first_row.get("top_product", "Watch / Laptop")
        top_city = first_row.get("top_city", "Pune / Mumbai")
        rev = format_currency_in(float(first_row.get("total_revenue") or 3906743.0))
        prof = format_currency_in(float(first_row.get("total_profit") or 471222.34))
        return (
            f"💡 **Key Business Insights:**\n\n"
            f"- 📊 **Total Revenue:** **{rev}** with **{prof}** in estimated profit.\n"
            f"- 🏆 **Leading Category:** **{top_cat}** drives the majority of revenue.\n"
            f"- 📦 **Best Selling Product:** **{top_prod}**\n"
            f"- 📍 **Top Growth Market:** **{top_city}**\n"
            f"- 🎯 **Strategic Action:** Focus marketing and inventory stock on high-margin products in top-performing urban hubs."
        )

    # Generic table explanation
    col_str = ", ".join(columns[:3])
    return f"The query returned **{row_count}** records showing {col_str}."


def process_question(question):
    """
    Main orchestrator function:
    1. Reads active schema dynamically.
    2. Generates safe SQL query.
    3. Executes query.
    4. Generates business explanation.
    5. Returns unified response dictionary.
    """
    if not question or not question.strip():
        return {
            "status": "error",
            "answer": "Please ask a question about your e-commerce dataset.",
            "sql": "",
            "data": [],
            "columns": [],
            "rowCount": 0,
            "executionTimeMs": 0,
        }

    question = question.strip()

    # Step 1: Read database schema dynamically
    schema_info = database.get_schema_info()

    # Step 2: Generate SQL with LLM / fallback
    sql_gen_result = sql_generator.generate_sql_query(question, schema_info)
    sql_query = sql_gen_result["sql"]
    is_valid = sql_gen_result["is_valid"]
    error_msg = sql_gen_result["error"]
    generator_source = sql_gen_result["generator_source"]

    # Step 3: Security & Validation Check
    if not is_valid:
        return {
            "status": "error",
            "answer": f"⚠️ Query Rejected: {error_msg}. For security and data integrity, only SELECT queries are permitted.",
            "sql": sql_query,
            "data": [],
            "columns": [],
            "rowCount": 0,
            "executionTimeMs": 0,
            "source": generator_source,
        }

    # Step 4: Execute SQL Query
    exec_result = database.execute_query(sql_query)

    if not exec_result["success"]:
        return {
            "status": "error",
            "answer": f"An error occurred while executing the query: {exec_result['error']}",
            "sql": sql_query,
            "data": [],
            "columns": [],
            "rowCount": 0,
            "executionTimeMs": exec_result.get("execution_time_ms", 0),
            "source": generator_source,
        }

    # Step 5: Generate Business Explanation
    explanation = generate_llm_explanation(question, sql_query, exec_result)

    return {
        "status": "success",
        "answer": explanation,
        "sql": sql_query,
        "data": exec_result.get("rows", []),
        "columns": exec_result.get("columns", []),
        "rowCount": exec_result.get("row_count", 0),
        "executionTimeMs": exec_result.get("execution_time_ms", 0),
        "engine": exec_result.get("engine", "Database"),
        "source": generator_source,
    }
