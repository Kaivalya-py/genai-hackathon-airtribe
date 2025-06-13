import sqlite3
import pandas as pd
import os # To check if the file exists

DB_FILE = "payments.db"
# --- Your CSV FILE PATH ---
CSV_FILE = r"C:\Users\kaiva\Downloads\pl_online_hackathon_2025-main\pl_online_hackathon_2025-main\settlement_data.csv"


# Explicitly list the column names as provided in your data's header.
# We're renaming duplicate headers (like transaction_id) to avoid issues.
COLUMNS = [
    "transaction_id_main", "merchant_display_name", "txn_status_name", "acquirer_name",
    "issuer_name", "payment_mode_id", "payment_mode_name", "card_type_association_name",
    "transaction_amount", "is_aggregator", "is_reversal", "transaction_start_date_time",
    "txn_refund_amt", "batch_id_main", "transaction_id_duplicate", "batch_id_duplicate",
    "nodal_account_bank", "actual_txn_amount", "refund_amount_col", "bank_charge_amount",
    "mdr_charge", "mdr_tax", "platform_fee", "mard_amount", "additonal_taxes",
    "bank_commision", "bank_service_tax", "amount_to_be_deducted_in_addition_to_bank_charges",
    "is_not_on_sell_rate", "convenience_fees_amt_in_paise", "convenience_fees_additional_amt_in_paise",
    "settlement_amount", "sds", "sdscycle", "program_name", "axis_payout_created",
    "payout_status", "payout_nodal_acc"
]

def import_csv_to_sqlite():
    if not os.path.exists(CSV_FILE):
        print(f"Error: The CSV file specified was not found: '{CSV_FILE}'")
        print("Please double-check the path and ensure the file exists.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print(f"Connecting to database: {DB_FILE}")

    # Drop any existing tables to ensure a clean import.
    cursor.execute("DROP TABLE IF EXISTS transactions")
    cursor.execute("DROP TABLE IF EXISTS refunds")
    cursor.execute("DROP TABLE IF EXISTS consolidated_payments")
    print("Dropped existing 'transactions', 'refunds', and 'consolidated_payments' tables (if they existed).")

    try:
        # --- CRITICAL CHANGE: Changed sep='\t' to sep=',' ---
        df_raw = pd.read_csv(CSV_FILE, sep=',', header=None, names=COLUMNS, skiprows=1)
        print(f"Successfully loaded {len(df_raw)} rows from '{CSV_FILE}'.")

        # --- Data Cleaning and Type Conversion ---
        # Convert date columns to datetime objects, then format for SQLite
        date_columns = ['transaction_start_date_time', 'axis_payout_created']
        for col in date_columns:
            # errors='coerce' will turn unparseable dates into NaT (Not a Time)
            # format='%d/%m/%y' to parse dates like 15/01/25
            df_raw[col] = pd.to_datetime(df_raw[col], format='%d/%m/%y', errors='coerce')
            # Format to YYYY-MM-DD HH:MM:SS string, NaT will become None (NULL in SQL)
            df_raw[col] = df_raw[col].dt.strftime('%Y-%m-%d %H:%M:%S')

        # Fill empty strings/NaNs (represented by pandas for empty fields) with actual None/NULL
        # This prevents 'nan' strings in the database for text fields
        df_raw = df_raw.where(pd.notna(df_raw), None)

        # --- Import into SQLite ---
        # Using if_exists='replace' will create a new table with columns matching DataFrame dtypes
        # and then insert all data.
        df_raw.to_sql('consolidated_payments', conn, if_exists='replace', index=False)
        print(f"Successfully imported all data into 'consolidated_payments' table.")

    except pd.errors.EmptyDataError:
        print(f"Error: '{CSV_FILE}' is empty. No data to import.")
    except pd.errors.ParserError as e:
        print(f"Error parsing '{CSV_FILE}'. Please check the delimiter (now set to ',') and data format. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during data import: {e}")

    finally:
        conn.close()
        print("Database import complete and connection closed.")

if __name__ == "__main__":
    import_csv_to_sqlite()
    print("\n--- Verification ---")
    print("You can verify the data in 'payments.db' by running a simple query using a SQLite browser or Python:")
    print("import sqlite3")
    print("import pandas as pd")
    print("conn = sqlite3.connect('payments.db')")
    print("print('\\nConsolidated Payments Table (first 5 rows):')")
    print("print(pd.read_sql_query('SELECT * FROM consolidated_payments LIMIT 5;', conn))")
    print("conn.close()")