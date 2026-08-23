# 🛒 AI-Powered E-Commerce Data Assistant & Power BI Analytics Platform

A modern, production-grade analytics platform that combines an **AI-powered Natural Language Data Assistant** with a **Power BI Sales Analytics Dashboard**. Users can ask business questions in natural language, auto-generate SQL queries against MySQL, and inspect rich interactive charts, DAX measures, and Power BI visual reports.

---

## 🏗️ Architecture

```
Clean_Ecommerce.xlsx
        ↓
      MySQL (ecommerce_db.orders)
        ↓
 ┌──────┴──────────────────────────┐
 ↓                                 ↓
Power BI Analytics Suite          Flask Web Application (app.py)
 ├── DAX Measures (11 formulas)    ├── GET  /           → AI Assistant (index.html)
 ├── Power BI Desktop (.pbix)      ├── GET  /dashboard  → Power BI Analytics (dashboard.html)
 └── Power BI Service Embed        ├── POST /ask        → Natural Language to SQL & Insights
                                   └── GET  /api/*      → Schema & Live Data Feeds
```

---

## 🌟 Key Features

### 1. 🤖 AI Natural Language Analytics Assistant
- **Conversational SQL Generation**: Converts plain English questions into optimized, safe SQL `SELECT` queries using Google Gemini LLM API.
- **Strict SQL Security Firewall**: Enforces read-only analytics by whitelisting `SELECT` queries and strictly blocking dangerous keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, etc.) and multi-statement injection attempts.
- **Executive Business Summaries**: Delivers explanations formatted with Indian Rupee units (₹ Lakh, ₹ Crore), KPI medals, and actionable takeaways.

### 2. 📊 Power BI Analytics Suite
- **7 Executive KPI Cards**: Total Sales, Total Orders, Unique Customers, Quantity Sold, Average Order Value (AOV), Average Discount Rate, and Gross Profit.
- **11 Production DAX Measures**: Real column-mapped DAX formulas for sales growth, category contribution %, and top product metrics.
- **Interactive Visualizations**:
  - Monthly Revenue & Profit Trend
  - Category Revenue Contribution Breakdown
  - Top 10 Products by Revenue & Units
  - Geographic Growth Markets (City & State breakdown)
  - Payment Modes & Customer Account Leaderboard
- **Multi-Dimension Slicers**: Interactive filtering by Category, City, and Order Status.
- **Dual Dashboard Modes**: Interactive in-app visualizer + Cloud Power BI Service iframe embed container.

---

## 📁 Project Structure

```
Ecommerce_AI_Assistant/
│
├── app.py                  # Flask web server & routes (GET /, GET /dashboard, POST /ask)
├── database.py             # MySQL connector, dynamic schema introspector & query executor
├── sql_generator.py        # LLM prompt builder & strict SQL security validator
├── ai_assistant.py         # End-to-end analytics orchestrator & explanation generator
├── powerbi.py              # Power BI integration & live analytics data engine
├── import_data.py          # Data ingestion script from Clean_Ecommerce.xlsx into MySQL
├── requirements.txt        # Python package dependencies
├── .env                    # Local secrets & credentials (DB, AI keys, Power BI Embed)
├── .env.example            # Environment configuration template
│
├── powerbi/
│   └── DAX_MEASURES.md     # 11 Production DAX Formulas reference
│
├── templates/
│   ├── index.html          # AI Assistant chat interface
│   └── dashboard.html      # Power BI Analytics Dashboard
│
├── static/
│   ├── style.css           # Glassmorphism design system & responsive styling
│   ├── dashboard.css       # Power BI Dashboard stylesheet
│   └── script.js           # Async chat controller, table renderer & schema explorer
│
├── tests/
│   └── test_assistant.py   # Automated unit & integration test suite
│
├── Clean_Ecommerce.xlsx    # Source e-commerce dataset (Excel - 524 rows)
├── Clean_Ecommerce.csv     # Source e-commerce dataset (CSV - 524 rows)
└── README.md               # Complete setup and user guide
```

---

## 🧰 Tech Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Chart.js, Lucide Icons
- **Backend**: Python 3.10+, Flask
- **Database**: MySQL (`localhost:3306/ecommerce_db`), PyMySQL
- **BI & Reporting**: Microsoft Power BI Desktop, Power BI Service, DAX
- **Data Science**: Pandas, OpenPyXL
- **AI / LLMs**: Google Gemini API (`gemini-flash-lite-latest`, `gemini-3.5-flash`), OpenAI API (`gpt-4o-mini`), or smart semantic fallback engine

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)
Create or edit `.env` in the root directory:
```ini
# MySQL Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_actual_mysql_password
DB_NAME=ecommerce_db

# Gemini API Key (https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here
LLM_PROVIDER=auto
LLM_MODEL=gemini-flash-lite-latest

# Flask Server Configuration
FLASK_ENV=development
FLASK_DEBUG=True
PORT=5000
SECRET_KEY=ecommerce-ai-assistant-secret-key-2025

# Power BI Service Embed URL (Optional)
POWERBI_EMBED_URL=
```

### 3. Import Dataset into MySQL
Ingest `Clean_Ecommerce.xlsx` into MySQL table `orders`:
```bash
python import_data.py
```

### 4. Run the Web Application
```bash
python app.py
```
Open **`http://127.0.0.1:5000`** in your browser:
- **`http://127.0.0.1:5000/`** → AI Assistant Chat Interface
- **`http://127.0.0.1:5000/dashboard`** → Power BI Analytics Dashboard

---

## 📊 Connecting Power BI to MySQL & Creating the Dashboard

### Step 1: Connect Power BI Desktop to MySQL
1. Open **Power BI Desktop**.
2. Click **Get Data** → Select **MySQL Database**.
3. Enter Server: `localhost:3306` and Database: `ecommerce_db`.
4. Enter MySQL credentials (`root` / your password) and select the **`orders`** table.
5. Click **Load**.

### Step 2: Add DAX Measures
In Power BI Desktop, right-click the `orders` table → Click **New Measure** to create the DAX formulas:

1. **Total Sales**:
   ```dax
   Total Sales = SUM(orders[Sales])
   ```
2. **Total Orders**:
   ```dax
   Total Orders = DISTINCTCOUNT(orders[Order_ID])
   ```
3. **Total Quantity**:
   ```dax
   Total Quantity = SUM(orders[Qty])
   ```
4. **Total Customers**:
   ```dax
   Total Customers = DISTINCTCOUNT(orders[Customer_Name])
   ```
5. **Average Order Value**:
   ```dax
   Average Order Value = DIVIDE([Total Sales], [Total Orders], 0)
   ```
6. **Average Discount**:
   ```dax
   Average Discount = AVERAGE(orders[Discount])
   ```
7. **Total Profit**:
   ```dax
   Total Profit = SUM(orders[Profit])
   ```
8. **Category Contribution %**:
   ```dax
   Category Sales % = DIVIDE([Total Sales], CALCULATE([Total Sales], ALL(orders[Category])), 0)
   ```

*(See [`powerbi/DAX_MEASURES.md`](powerbi/DAX_MEASURES.md) for the complete list of 11 formulas).*

### Step 3: Publish & Embed in Flask Web App
1. In Power BI Desktop, click **Publish** → Select your Power BI Workspace.
2. Open the report on **[app.powerbi.com](https://app.powerbi.com)**.
3. Go to **File** → **Embed Report** → **Publish to Web (Public)**.
4. Copy the generated iframe URL and paste it into `.env`:
   ```env
   POWERBI_EMBED_URL="https://app.powerbi.com/view?r=eyJrIjoi..."
   ```
5. Refresh the `/dashboard` page in your browser to view the live cloud report embedded inside your app!

---

## 🧪 Testing

Run the automated test suite:
```bash
python -m unittest tests/test_assistant.py
```
All unit and integration tests verify:
- Dynamic schema extraction & KPI calculation
- SQL security filtering & query execution
- End-to-end AI assistant question processing
- Flask endpoints (`GET /`, `GET /dashboard`, `POST /ask`, `GET /api/status`, `GET /api/schema`, `GET /api/powerbi/data`)
