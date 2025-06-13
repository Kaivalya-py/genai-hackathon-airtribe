import sqlite3
import pandas as pd

# Connect to your SQLite database
DB_FILE = "payments.db"
conn = sqlite3.connect(DB_FILE)

# --- Set Pandas display options to show all columns and more rows (still good for 10 rows) ---
pd.set_option('display.max_columns', None)  # Show all columns
pd.set_option('display.max_rows', 10)     # Limit rows to 10 for display
pd.set_option('display.width', 1000)        # Increase display width to prevent wrapping

# Read data from the 'consolidated_payments' table with a LIMIT
try:
    # --- MODIFIED LINE: Added LIMIT 10 to the SQL query ---
    df_limited = pd.read_sql_query('SELECT * FROM consolidated_payments LIMIT 10;', conn)
    print("\n--- Consolidated Payments Table (First 10 Rows) ---")
    print(df_limited)
except pd.io.sql.DatabaseError as e:
    print(f"Error reading from database: {e}")
    print("Ensure the 'consolidated_payments' table exists in 'payments.db'.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

finally:
    # Close the database connection
    conn.close()
    print("\nDatabase connection closed.")

# Reset Pandas display options to default after printing (optional, but good practice)
pd.reset_option('display.max_columns')
pd.reset_option('display.max_rows')
pd.reset_option('display.width')