"""
app.py - Flask Application & REST API Server for AI E-Commerce Assistant

This is the main entry point for the web application.
Routes:
- GET /              : Serves the modern analytics dashboard.
- POST /ask          : Primary conversational endpoint (receives question, returns SQL + answer + data).
- GET /api/status    : Returns database connection status and engine health.
- GET /api/schema    : Returns dynamic schema breakdown for the UI drawer.
- GET /api/summary   : Returns dataset overview metrics for dashboard KPI cards.
- POST /api/import   : Initiates MySQL dataset import.
"""

import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Define absolute path to .env file in the project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_FILE, override=True)

# Import core modules
import database
import ai_assistant
import sql_generator
import import_data
import powerbi

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "ecommerce-ai-assistant-2025")
app.config["JSON_SORT_KEYS"] = False


@app.route("/favicon.ico")
def favicon():
    """Handles browser favicon requests cleanly to prevent 404 in logs."""
    return "", 204


@app.route("/")
def index():
    """Renders the primary AI Data Assistant analytics chat interface."""
    db_status = database.get_connection_status()
    summary = database.get_summary_stats()
    pbi_config = powerbi.get_powerbi_config()
    return render_template("index.html", db_status=db_status, summary=summary, pbi_config=pbi_config, current_page="ai")


@app.route("/dashboard")
def powerbi_dashboard():
    """Renders the dedicated Power BI Analytics Dashboard page."""
    db_status = database.get_connection_status()
    pbi_config = powerbi.get_powerbi_config()
    dax_measures = powerbi.get_dax_measures()
    initial_data = powerbi.get_powerbi_dashboard_data()
    return render_template(
        "dashboard.html",
        db_status=db_status,
        pbi_config=pbi_config,
        dax_measures=dax_measures,
        data=initial_data,
        current_page="dashboard"
    )


@app.route("/api/powerbi/config", methods=["GET"])
def api_powerbi_config():
    """Returns Power BI embedding configuration and DAX measure reference."""
    config = powerbi.get_powerbi_config()
    dax = powerbi.get_dax_measures()
    return jsonify({
        "config": config,
        "dax_measures": dax
    })


@app.route("/api/powerbi/data", methods=["GET"])
def api_powerbi_data():
    """Returns live aggregated analytics data for interactive visualizer and slicers."""
    category = request.args.getlist("category") or request.args.get("category", "All")
    city = request.args.getlist("city") or request.args.get("city", "All")
    status = request.args.getlist("status") or request.args.get("status", "All")
    payment = request.args.getlist("payment") or request.args.get("payment", "All")
    data = powerbi.get_powerbi_dashboard_data(
        category_filter=category,
        city_filter=city,
        status_filter=status,
        payment_filter=payment
    )
    return jsonify(data)


@app.route("/ask", methods=["POST"])
def ask_question():
    """
    Main endpoint for asking natural language questions about the e-commerce dataset.
    Expected JSON payload:
    {
        "question": "Which product has the highest sales?"
    }
    """
    try:
        data = request.get_json(silent=True)
        if not data or "question" not in data:
            return jsonify({
                "status": "error",
                "answer": "Invalid request: Please provide a 'question' string in the JSON payload.",
                "sql": "",
                "data": [],
                "columns": [],
                "rowCount": 0,
                "executionTimeMs": 0,
            }), 400

        question = data.get("question", "").strip()
        if not question:
            return jsonify({
                "status": "error",
                "answer": "Please enter a question to analyze.",
                "sql": "",
                "data": [],
                "columns": [],
                "rowCount": 0,
                "executionTimeMs": 0,
            }), 400

        # Process question through the AI assistant pipeline
        response_payload = ai_assistant.process_question(question)
        return jsonify(response_payload), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "answer": f"An unexpected server error occurred: {str(e)}",
            "sql": "",
            "data": [],
            "columns": [],
            "rowCount": 0,
            "executionTimeMs": 0,
        }), 500


@app.route("/api/status", methods=["GET"])
def api_status():
    """Returns database connection health and active configuration."""
    status = database.get_connection_status()
    gemini_configured = bool(os.getenv("GEMINI_API_KEY", "").strip())
    openai_configured = bool(os.getenv("OPENAI_API_KEY", "").strip())
    
    return jsonify({
        "database": status,
        "ai": {
            "gemini_configured": gemini_configured,
            "openai_configured": openai_configured,
            "active_provider": os.getenv("LLM_PROVIDER", "auto"),
            "model": os.getenv("LLM_MODEL", "gemini-1.5-flash"),
        }
    })


@app.route("/api/schema", methods=["GET"])
def api_schema():
    """Returns dynamic database schema details for in-app schema explorer."""
    schema = database.get_schema_info()
    return jsonify(schema)


@app.route("/api/summary", methods=["GET"])
def api_summary():
    """Returns high-level business KPI metrics."""
    stats = database.get_summary_stats()
    return jsonify(stats)


@app.route("/api/import", methods=["POST"])
def api_import():
    """Triggers MySQL data import on demand."""
    try:
        success = import_data.import_to_mysql()
        if success:
            return jsonify({
                "status": "success",
                "message": "Dataset successfully imported into MySQL database 'ecommerce_db'."
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Import failed. Please check MySQL credentials in your .env file."
            }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Import error: {str(e)}"
        }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() in ["true", "1", "t"]
    print("\n" + "=" * 60)
    print(f"🌟 E-Commerce AI Assistant running at: http://127.0.0.1:{port}")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
