"""
import_data.py - Import Clean_Ecommerce Dataset into MySQL Database

This script:
1. Connects to the local/remote MySQL server using credentials from .env.
2. Creates the database (default: 'ecommerce_db') if it does not already exist.
3. Cleans and normalizes the dataset from Clean_Ecommerce.xlsx / Clean_Ecommerce.csv:
   - Trims whitespace from string fields (e.g., city names, product names).
   - Standardizes date formats (YYYY-MM-DD).
   - Replaces missing / NaN values with NULL.
4. Creates the 'orders' table with optimized data types.
5. Performs a batch insert of all records.
6. Prints a verification summary.
"""

import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pandas as pd
import pymysql
from dotenv import load_dotenv

# Define absolute path to .env file in the project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")

def reload_config():
    """Reloads environment variables from the project .env file."""
    load_dotenv(dotenv_path=ENV_FILE, override=True)
    return {
        "host": os.getenv("DB_HOST", "localhost").strip(),
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER", "root").strip(),
        "password": os.getenv("DB_PASSWORD", "").strip(),
        "database": os.getenv("DB_NAME", "ecommerce_db").strip(),
    }

# Initial configuration load
config = reload_config()
DB_HOST = config["host"]
DB_PORT = config["port"]
DB_USER = config["user"]
DB_PASSWORD = config["password"]
DB_NAME = config["database"]

EXCEL_FILE = os.path.join(BASE_DIR, "Clean_Ecommerce.xlsx")
CSV_FILE = os.path.join(BASE_DIR, "Clean_Ecommerce.csv")


def load_raw_data():
    """Reads dataset from Excel or CSV file."""
    if os.path.exists(EXCEL_FILE):
        print(f"📖 Reading dataset from Excel: {EXCEL_FILE}")
        try:
            return pd.read_excel(EXCEL_FILE)
        except Exception as e:
            print(f"⚠️ Excel read failed: {e}. Falling back to CSV...")

    if os.path.exists(CSV_FILE):
        print(f"📖 Reading dataset from CSV: {CSV_FILE}")
        return pd.read_csv(CSV_FILE)

    raise FileNotFoundError("Could not find Clean_Ecommerce.xlsx or Clean_Ecommerce.csv in project directory.")


def clean_dataframe(df):
    """Cleans and standardizes the DataFrame columns and values."""
    print("🧹 Cleaning and normalizing data...")
    # Strip whitespace from column names
    df.columns = [c.strip() for c in df.columns]

    # Strip whitespace from string columns
    str_cols = df.select_dtypes(include=["object", "string", "str"]).columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": None, "None": None, "": None, "NaT": None})

    # Format dates to YYYY-MM-DD
    for col in ["Order_Date", "Delivery_Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
            df[col] = df[col].replace({"NaT": None, "": None})

    # Clean phone numbers (convert float phone numbers to clean string digits or None)
    if "Phone" in df.columns:
        def clean_phone(val):
            if pd.isna(val) or val is None or str(val).strip() in ["", "nan", "None"]:
                return None
            try:
                # Convert float 9829008196.0 -> 9829008196
                return str(int(float(val)))
            except Exception:
                return str(val).strip()

        df["Phone"] = df["Phone"].apply(clean_phone)

    # Clean integers
    for int_col in ["Qty", "Order_Year"]:
        if int_col in df.columns:
            def clean_int(val):
                if pd.isna(val) or val is None or str(val).strip() in ["", "nan", "None"]:
                    return None
                try:
                    return int(float(val))
                except Exception:
                    return None
            df[int_col] = df[int_col].apply(clean_int)

    # Clean floats / decimals
    for float_col in ["Unit_Price", "Discount", "Sales", "Net_Amount", "Profit"]:
        if float_col in df.columns:
            def clean_float(val):
                if pd.isna(val) or val is None or str(val).strip() in ["", "nan", "None"]:
                    return None
                try:
                    return round(float(val), 2)
                except Exception:
                    return None
            df[float_col] = df[float_col].apply(clean_float)

    return df


def import_to_mysql():
    """Executes database creation and batch import into MySQL."""
    cfg = reload_config()
    host = cfg["host"]
    port = cfg["port"]
    user = cfg["user"]
    password = cfg["password"]
    database_name = cfg["database"]

    print("=" * 60)
    print("🚀 Starting MySQL Data Import for E-Commerce AI Assistant")
    print(f"📁 Loaded config from: {ENV_FILE}")
    print(f"⚙️ Target: MySQL @ {host}:{port} | User: {user} | Database: {database_name} | Password set: {'Yes' if password else 'No (Blank)'}")
    print("=" * 60)

    # 1. Connect to MySQL Server (without selecting database first)
    try:
        print(f"🔌 Connecting to MySQL server at {host}:{port} as '{user}'...")
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=5,
        )
        print("✅ Successfully connected to MySQL server.")
    except Exception as e:
        print(f"\n❌ ERROR: Could not connect to MySQL server at {host}:{port}.")
        print(f"Details: {e}")
        print(f"\n👉 Please open your '.env' file at:\n   {ENV_FILE}")
        print("   and configure your credentials:")
        print(f"   DB_HOST={host}")
        print(f"   DB_USER={user}")
        print("   DB_PASSWORD=your_actual_mysql_password")
        print(f"   DB_NAME={database_name}")
        return False

    try:
        with conn.cursor() as cursor:
            # 2. Create Database
            print(f"📦 Creating database `{database_name}` if not exists...")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.execute(f"USE `{database_name}`;")

            # 3. Read and Clean Data
            df = load_raw_data()
            df = clean_dataframe(df)

            # 4. Create Table
            table_name = "orders"
            print(f"🛠️ Creating table `{table_name}`...")
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`;")

            create_table_sql = f"""
            CREATE TABLE `{table_name}` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `Order_ID` VARCHAR(50) NULL,
                `Order_Date` DATE NULL,
                `Customer_Name` VARCHAR(100) NULL,
                `Email` VARCHAR(150) NULL,
                `Phone` VARCHAR(30) NULL,
                `City` VARCHAR(100) NULL,
                `State` VARCHAR(100) NULL,
                `Product` VARCHAR(100) NULL,
                `Category` VARCHAR(100) NULL,
                `Qty` INT NULL,
                `Unit_Price` DECIMAL(10, 2) NULL,
                `Discount` DECIMAL(5, 2) NULL,
                `Payment_Mode` VARCHAR(50) NULL,
                `Order_Status` VARCHAR(50) NULL,
                `Delivery_Date` DATE NULL,
                `Order_Month` VARCHAR(50) NULL,
                `Sales` DECIMAL(12, 2) NULL,
                `Net_Amount` DECIMAL(12, 2) NULL,
                `Profit` DECIMAL(12, 2) NULL,
                `Order_Year` INT NULL,
                `Order_Day` VARCHAR(50) NULL,
                INDEX idx_category (`Category`),
                INDEX idx_product (`Product`),
                INDEX idx_city (`City`),
                INDEX idx_order_date (`Order_Date`),
                INDEX idx_order_status (`Order_Status`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            cursor.execute(create_table_sql)
            print(f"✅ Table `{table_name}` created with indexes.")

            # 5. Insert Data
            cols = [
                "Order_ID", "Order_Date", "Customer_Name", "Email", "Phone",
                "City", "State", "Product", "Category", "Qty", "Unit_Price",
                "Discount", "Payment_Mode", "Order_Status", "Delivery_Date",
                "Order_Month", "Sales", "Net_Amount", "Profit", "Order_Year", "Order_Day"
            ]

            # Match only existing columns in df
            active_cols = [c for c in cols if c in df.columns]
            placeholders = ", ".join(["%s"] * len(active_cols))
            columns_str = ", ".join([f"`{c}`" for c in active_cols])

            insert_sql = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"

            records = []
            for _, row in df.iterrows():
                row_vals = []
                for c in active_cols:
                    val = row[c]
                    if pd.isna(val) or val is None:
                        row_vals.append(None)
                    else:
                        row_vals.append(val)
                records.append(tuple(row_vals))

            print(f"📥 Inserting {len(records)} records into `{table_name}`...")
            cursor.executemany(insert_sql, records)
            print(f"✅ Successfully inserted {len(records):,} records.")

            # 6. Verify row count
            cursor.execute(f"SELECT COUNT(*) AS total FROM `{table_name}`")
            count = cursor.fetchone()[0]
            print(f"📊 Verification: `{table_name}` now contains {count:,} rows.")

        conn.close()
        print("\n🎉 Import completed successfully! MySQL is ready for queries.")
        return True

    except Exception as e:
        print(f"\n❌ Error during import: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


if __name__ == "__main__":
    success = import_to_mysql()
    sys.exit(0 if success else 1)
