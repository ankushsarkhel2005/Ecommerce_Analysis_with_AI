"""
sql_generator.py - AI-Powered SQL Query Generator & Strict Security Validator

This module:
1. Formats prompt instructions with dynamic schema information.
2. Calls the configured LLM API (Google Gemini, OpenAI, or smart rule engine).
3. Strictly validates generated SQL for security against SQL injection and dangerous operations:
   - Whitelist: SELECT / WITH statements only.
   - Blacklist: DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, CREATE, EXEC, etc.
   - Anti-chaining: Disallows multiple statements separated by semicolons.
4. Cleans and normalizes SQL markdown output.
"""

import os
import re
import json
import requests
from dotenv import load_dotenv

# Define absolute path to .env file in the project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")

def reload_ai_config():
    """Reloads AI environment variables from .env."""
    load_dotenv(dotenv_path=ENV_FILE, override=True)
    return {
        "gemini_key": os.getenv("GEMINI_API_KEY", "").strip(),
        "openai_key": os.getenv("OPENAI_API_KEY", "").strip(),
        "provider": os.getenv("LLM_PROVIDER", "auto").lower().strip(),
        "model": os.getenv("LLM_MODEL", "gemini-1.5-flash").strip(),
    }

_ai_cfg = reload_ai_config()
GEMINI_API_KEY = _ai_cfg["gemini_key"]
OPENAI_API_KEY = _ai_cfg["openai_key"]
LLM_PROVIDER = _ai_cfg["provider"]
LLM_MODEL = _ai_cfg["model"]

# Forbidden SQL keywords / tokens
FORBIDDEN_KEYWORDS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bCREATE\b",
    r"\bRENAME\b",
    r"\bREPLACE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bCALL\b",
    r"\bSHUTDOWN\b",
    r"\bOUTFILE\b",
    r"\bDUMPFILE\b",
    r"\bLOAD_FILE\b",
]

# System prompt for SQL generation
SQL_SYSTEM_PROMPT = """You are an expert E-Commerce SQL Data Analyst.
Your role is to translate a user's natural language question into a single, clean, highly optimized SQL SELECT query.

DATABASE SCHEMA:
{schema_text}

CRITICAL RULES:
1. Generate ONLY ONE valid SELECT query (or WITH ... SELECT).
2. ONLY use the table and column names specified in the schema above. DO NOT invent columns or tables.
3. NEVER generate any data modification statements (NO DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, CREATE).
4. Use aggregation functions (SUM, AVG, COUNT, MIN, MAX) with appropriate aliases when calculating totals or metrics.
5. Always use `GROUP BY` when aggregating non-aggregated columns.
6. Use `ORDER BY` and `LIMIT` appropriately (e.g. for "highest", "top 5", "best", "most").
7. For questions about sales or revenue, use `SUM(Sales)` or `SUM(Net_Amount)`.
8. Handle potential NULLs using `COALESCE()` or filtering `WHERE Sales IS NOT NULL`.
9. For case-insensitive text matching or city names, use standard comparisons.
10. Return ONLY the raw SQL query with NO markdown fences, NO backticks, and NO explanations.
"""


def clean_sql_output(raw_output):
    """
    Strips markdown code blocks, backticks, extra whitespaces, and trailing semicolons.
    """
    if not raw_output:
        return ""
    text = raw_output.strip()
    # Remove markdown code blocks like ```sql ... ```
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    # Remove trailing semicolons for consistent execution
    text = re.sub(r";+\s*$", "", text)
    return text.strip()


def validate_sql(sql_query, allowed_table="orders"):
    """
    Strict security validator for generated SQL queries.
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not sql_query or not sql_query.strip():
        return False, "Generated SQL is empty."

    cleaned = sql_query.strip()

    # 1. Must start with SELECT or WITH
    if not (re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE) or re.match(r"^\s*WITH\b", cleaned, re.IGNORECASE)):
        return False, "Security Violation: Only SELECT and CTE queries are permitted."

    # 2. Check for forbidden keywords
    for pattern in FORBIDDEN_KEYWORDS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            match = re.search(pattern, cleaned, re.IGNORECASE).group(0)
            return False, f"Security Violation: Prohibited SQL command '{match}' detected."

    # 3. Check for multiple query chaining (semicolon followed by another statement)
    if ";" in cleaned:
        statements = [s.strip() for s in cleaned.split(";") if s.strip()]
        if len(statements) > 1:
            return False, "Security Violation: Multiple chained SQL statements are not permitted."

    # 4. Check for dangerous comment syntax that could hide injection
    if "--" in cleaned or "/*" in cleaned:
        return False, "Security Violation: SQL comments are not permitted."

    return True, None


def call_gemini_api(prompt, system_prompt):
    """
    Calls Google Gemini REST API using the provided GEMINI_API_KEY.
    Automatically tries candidate model endpoints if one returns 404.
    """
    cfg = reload_ai_config()
    api_key = cfg["gemini_key"]
    if not api_key:
        return None

    configured_model = cfg["model"]
    if "/" in configured_model:
        configured_model = configured_model.split("/")[-1]

    # Model priority list (prioritizing 200-OK high-quota active models)
    candidate_models = [
        configured_model,
        "gemini-flash-lite-latest",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-flash-latest"
    ]
    # Deduplicate while preserving order
    seen = set()
    models_to_try = [m for m in candidate_models if m and not (m in seen or seen.add(m))]

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\nUSER QUESTION: {prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 600,
        },
    }

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=4)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
            elif response.status_code in (404, 429):
                # Try next model if not found or rate limited
                continue
            else:
                continue
        except Exception:
            continue

    return None


def call_openai_api(prompt, system_prompt):
    """
    Calls OpenAI Chat Completions REST API using OPENAI_API_KEY.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = "gpt-4o-mini"
    if "gpt" in os.getenv("LLM_MODEL", "").lower():
        model = os.getenv("LLM_MODEL")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 500,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            data = response.json()
            choices = data.get("choices", [])
            if choices and "message" in choices[0]:
                return choices[0]["message"].get("content", "").strip()
        else:
            print(f"⚠️ OpenAI API error ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"⚠️ OpenAI API request failed: {e}")

    return None


def fallback_rule_sql_generator(question, schema_info):
    """
    Smart semantic fallback engine that maps standard e-commerce questions
    to verified SQL queries when no LLM API key is configured or when offline.
    """
    q = question.lower().strip()
    table = schema_info.get("table_name", "orders")

    # 1. Total sales / revenue
    if any(k in q for k in ["total sale", "total revenue", "overall sale", "all sale", "how much sale", "how much revenue", "sum of sale"]):
        return f"SELECT COALESCE(SUM(Sales), 0) AS total_sales, COALESCE(SUM(Net_Amount), 0) AS total_net_sales, COUNT(*) AS total_orders FROM {table};"

    # 2. Product with highest sales / top products
    if "product" in q and any(k in q for k in ["highest", "top", "best", "most", "maximum", "leader"]):
        limit = 5 if ("top 5" in q or "5" in q) else (10 if "top 10" in q else 1)
        if "top" in q and "5" in q:
            return f"SELECT Product, Category, SUM(Sales) AS total_sales, COUNT(*) AS order_count FROM {table} GROUP BY Product, Category ORDER BY total_sales DESC LIMIT 5;"
        return f"SELECT Product, Category, SUM(Sales) AS total_sales, COUNT(*) AS order_count FROM {table} GROUP BY Product, Category ORDER BY total_sales DESC LIMIT {limit};"

    # 3. Category with highest sales / compare categories
    if ("category" in q or "categories" in q) and any(k in q for k in ["highest", "top", "best", "most", "compare", "breakdown", "revenue", "share", "sale", "between"]):
        return f"SELECT Category, SUM(Sales) AS total_sales, COUNT(*) AS total_orders, ROUND(AVG(Sales), 2) AS avg_order_value FROM {table} GROUP BY Category ORDER BY total_sales DESC;"

    # 4. City / Location with highest sales
    if any(k in q for k in ["city", "location", "state", "place", "region", "geography"]) and any(k in q for k in ["highest", "top", "best", "most", "sales", "revenue"]):
        limit = 5 if ("top 5" in q or "5" in q) else 1
        return f"SELECT City, State, SUM(Sales) AS total_sales, COUNT(*) AS order_count FROM {table} GROUP BY City, State ORDER BY total_sales DESC LIMIT {limit};"

    # 5. Month with highest sales / monthly trend
    if any(k in q for k in ["month", "monthly", "trend", "time", "season"]):
        return f"SELECT Order_Month, SUM(Sales) AS total_sales, COUNT(*) AS order_count FROM {table} WHERE Order_Month IS NOT NULL GROUP BY Order_Month ORDER BY total_sales DESC;"

    # 6. Payment modes / Payment methods
    if any(k in q for k in ["payment", "upi", "card", "cod", "wallet", "netbanking", "mode"]):
        return f"SELECT Payment_Mode, COUNT(*) AS order_count, SUM(Sales) AS total_sales FROM {table} GROUP BY Payment_Mode ORDER BY total_sales DESC;"

    # 7. Order Status / Cancellations / Returns / Delivered
    if any(k in q for k in ["status", "cancel", "return", "deliver", "pending"]):
        return f"SELECT Order_Status, COUNT(*) AS order_count, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table}), 2) AS percentage FROM {table} GROUP BY Order_Status ORDER BY order_count DESC;"

    # 8. Top customers / Customer analysis
    if any(k in q for k in ["customer", "client", "buyer", "user"]):
        return f"SELECT Customer_Name, City, COUNT(*) AS orders_placed, SUM(Sales) AS total_spent FROM {table} GROUP BY Customer_Name, City ORDER BY total_spent DESC LIMIT 5;"

    # 9. Profit analysis / Most profitable
    if any(k in q for k in ["profit", "margin", "profitable"]):
        return f"SELECT Product, Category, SUM(Profit) AS total_profit, SUM(Sales) AS total_sales, ROUND((SUM(Profit)/SUM(Sales))*100, 2) AS profit_margin_pct FROM {table} WHERE Profit IS NOT NULL GROUP BY Product, Category ORDER BY total_profit DESC;"

    # 10. General Business Insights / Overview
    if any(k in q for k in ["insight", "summary", "overview", "kpi", "performance", "important"]):
        return f"""
        SELECT 
            (SELECT Category FROM {table} GROUP BY Category ORDER BY SUM(Sales) DESC LIMIT 1) AS top_category,
            (SELECT Product FROM {table} GROUP BY Product ORDER BY SUM(Sales) DESC LIMIT 1) AS top_product,
            (SELECT City FROM {table} GROUP BY City ORDER BY SUM(Sales) DESC LIMIT 1) AS top_city,
            (SELECT SUM(Sales) FROM {table}) AS total_revenue,
            (SELECT SUM(Profit) FROM {table}) AS total_profit,
            (SELECT COUNT(*) FROM {table}) AS total_orders;
        """

    # Generic fallback: top products by sales
    return f"SELECT Product, Category, SUM(Sales) AS total_sales, COUNT(*) AS orders FROM {table} GROUP BY Product, Category ORDER BY total_sales DESC LIMIT 5;"


def generate_sql_query(question, schema_info):
    """
    Generates and validates a SQL query for the user question.
    Returns:
        dict: {
            "sql": str,
            "is_valid": bool,
            "error": str or None,
            "generator_source": "Gemini API" | "OpenAI API" | "Semantic Fallback Engine"
        }
    """
    schema_text = schema_info.get("text_representation", "Table: orders")
    formatted_system_prompt = SQL_SYSTEM_PROMPT.format(schema_text=schema_text)

    raw_sql = None
    source = "Semantic Fallback Engine"

    # Determine provider
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    provider = LLM_PROVIDER

    if provider == "gemini" or (provider == "auto" and gemini_key):
        raw_sql = call_gemini_api(question, formatted_system_prompt)
        if raw_sql:
            source = "Google Gemini API"

    if not raw_sql and (provider == "openai" or (provider == "auto" and openai_key)):
        raw_sql = call_openai_api(question, formatted_system_prompt)
        if raw_sql:
            source = "OpenAI API"

    if not raw_sql:
        raw_sql = fallback_rule_sql_generator(question, schema_info)
        source = "Semantic Fallback Engine"

    # Clean the SQL
    clean_sql = clean_sql_output(raw_sql)

    # Validate the SQL
    is_valid, validation_error = validate_sql(clean_sql, allowed_table=schema_info.get("table_name", "orders"))

    return {
        "sql": clean_sql,
        "is_valid": is_valid,
        "error": validation_error,
        "generator_source": source,
    }
