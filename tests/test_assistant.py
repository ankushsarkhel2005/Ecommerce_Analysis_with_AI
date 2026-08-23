"""
test_assistant.py - Automated Unit & Integration Tests

Covers:
1. Database schema inspection and summary statistics.
2. Safe SQL generation and anti-injection security validation.
3. Query execution against dataset.
4. AI assistant end-to-end question processing.
5. Flask API endpoints (GET /, POST /ask, GET /api/status, GET /api/schema).
"""

import os
import sys
import unittest
import json

# Ensure workspace root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
import sql_generator
import ai_assistant
from app import app


class TestEcommerceAssistant(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_01_database_schema(self):
        """Verify dynamic schema extraction from dataset."""
        schema = database.get_schema_info()
        self.assertIsNotNone(schema)
        self.assertEqual(schema["table_name"], "orders")
        self.assertGreater(schema["row_count"], 0)
        self.assertTrue(len(schema["columns"]) >= 15)
        
        column_names = [col["name"] for col in schema["columns"]]
        self.assertIn("Sales", column_names)
        self.assertIn("Category", column_names)
        self.assertIn("Product", column_names)
        self.assertIn("City", column_names)

    def test_02_database_summary_stats(self):
        """Verify business KPI calculations."""
        stats = database.get_summary_stats()
        self.assertIn("total_sales", stats)
        self.assertIn("total_orders", stats)
        self.assertGreater(stats["total_sales"], 1000000)
        self.assertGreaterEqual(stats["total_orders"], 500)

    def test_03_sql_security_validator(self):
        """Ensure dangerous queries and SQL injections are blocked."""
        # Dangerous commands
        dangerous = [
            "DROP TABLE orders",
            "DELETE FROM orders WHERE 1=1",
            "UPDATE orders SET Sales = 0",
            "INSERT INTO orders (Order_ID) VALUES ('HACK')",
            "ALTER TABLE orders DROP COLUMN Sales",
            "TRUNCATE TABLE orders",
            "SELECT * FROM orders; DROP TABLE orders",
            "SELECT * FROM orders -- comment bypass",
        ]

        for query in dangerous:
            is_valid, err = sql_generator.validate_sql(query)
            self.assertFalse(is_valid, f"Failed to block dangerous query: {query}")
            self.assertIsNotNone(err)

        # Valid SELECT queries
        safe = [
            "SELECT Product, SUM(Sales) FROM orders GROUP BY Product",
            "SELECT Category, AVG(Sales) FROM orders GROUP BY Category ORDER BY AVG(Sales) DESC LIMIT 5",
            "SELECT COUNT(*) AS total FROM orders WHERE City = 'Pune'",
        ]

        for query in safe:
            is_valid, err = sql_generator.validate_sql(query)
            self.assertTrue(is_valid, f"Wrongly blocked safe query: {query}")
            self.assertIsNone(err)

    def test_04_ai_assistant_e2e(self):
        """Test end-to-end question processing pipeline."""
        questions = [
            "What is the total sales?",
            "Which product has the highest sales?",
            "Which category has the highest sales?",
            "Which city has the highest sales?",
            "Show me important business insights."
        ]

        for q in questions:
            res = ai_assistant.process_question(q)
            self.assertEqual(res["status"], "success", f"Processing failed for question: {q}")
            self.assertTrue(len(res["sql"]) > 0)
            self.assertTrue(len(res["answer"]) > 0)
            self.assertGreater(res["rowCount"], 0)

    def test_05_flask_api_ask(self):
        """Test Flask POST /ask endpoint."""
        payload = {"question": "What is the total sales?"}
        response = self.app.post(
            "/ask",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("answer", data)
        self.assertIn("sql", data)
        self.assertIn("total_sales", data["sql"].lower())

    def test_06_flask_api_status_and_schema(self):
        """Test Flask status and schema metadata endpoints."""
        status_res = self.app.get("/api/status")
        self.assertEqual(status_res.status_code, 200)
        status_data = json.loads(status_res.data)
        self.assertIn("database", status_data)
        self.assertIn("ai", status_data)

        schema_res = self.app.get("/api/schema")
        self.assertEqual(schema_res.status_code, 200)
        schema_data = json.loads(schema_res.data)
        self.assertEqual(schema_data["table_name"], "orders")

    def test_07_powerbi_dashboard_and_api(self):
        """Test Power BI dashboard page and analytics endpoints."""
        # 1. Test GET /dashboard renders successfully
        dash_res = self.app.get("/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"Power BI Analytics", dash_res.data)

        # 2. Test GET /api/powerbi/config returns DAX measures
        config_res = self.app.get("/api/powerbi/config")
        self.assertEqual(config_res.status_code, 200)
        config_data = json.loads(config_res.data)
        self.assertIn("config", config_data)
        self.assertIn("dax_measures", config_data)
        self.assertGreaterEqual(len(config_data["dax_measures"]), 10)

        # 3. Test GET /api/powerbi/data returns aggregated metrics
        data_res = self.app.get("/api/powerbi/data")
        self.assertEqual(data_res.status_code, 200)
        bi_data = json.loads(data_res.data)
        self.assertIn("kpis", bi_data)
        self.assertIn("categories", bi_data)
        self.assertIn("top_products", bi_data)
        self.assertIn("monthly_trend", bi_data)
        self.assertGreater(float(bi_data["kpis"]["total_sales"]), 0)


if __name__ == "__main__":
    unittest.main()

