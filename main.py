import sqlite3
import pandas as pd
import plotly.express as px
import plotly.io as pio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import re

# --- Pydantic Models for API data structure ---
class QueryRequest(BaseModel):
    query: str
    # In a real app, you would also pass a merchant_id
    # merchant_id: str

class InsightResponse(BaseModel):
    insight_text: str
    chart_json: str
    query_used: str

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Merchant Insights API",
    description="An API that provides conversational insights from payment data."
)

# --- CORS Middleware ---
# Allows the frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "payments.db"

# --- The "Agentic" Logic ---
# This is a simplified agent. It uses regex to find keywords and map them to functions.
# You can replace this logic with calls to an LLM like OpenAI to generate the SQL.

def get_refund_analysis(time_period: str = "yesterday"):
    """Generates SQL and insights for refund analysis."""
    conn = sqlite3.connect(DB_FILE)
    
    # Determine date range based on the time period
    if time_period == "yesterday":
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=1)
        date_filter_str = f"WHERE r.timestamp >= '{start_date}' AND r.timestamp < '{end_date}'"
        period_text = "yesterday"
    elif time_period in ["week", "last 7 days"]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        date_filter_str = f"WHERE r.timestamp >= '{start_date}' AND r.timestamp < '{end_date}'"
        period_text = "in the last 7 days"
    else: # Default to all time if not specified
        date_filter_str = ""
        period_text = "overall"

    sql_query = f"""
        SELECT
            CAST(strftime('%Y-%m-%d', r.timestamp) AS DATE) as refund_date,
            r.reason,
            COUNT(r.refund_id) as number_of_refunds,
            SUM(r.amount) as total_refund_amount
        FROM refunds r
        {date_filter_str}
        GROUP BY refund_date, r.reason
        ORDER BY refund_date, number_of_refunds DESC
    """
    
    df = pd.read_sql_query(sql_query, conn)
    conn.close()
    
    if df.empty:
        return "No refund data found for the specified period.", "{}", sql_query
        
    # Generate Insight Text
    total_refunds = df['number_of_refunds'].sum()
    total_amount = df['total_refund_amount'].sum()
    insight_text = (
        f"Found {total_refunds} refunds totaling ₹{total_amount:,.2f} {period_text}. "
        f"The primary reasons for refunds were: {', '.join(df['reason'].unique()[:3])}."
    )

    # Generate Plotly Chart
    fig = px.bar(
        df, 
        x='refund_date', 
        y='number_of_refunds', 
        color='reason',
        title=f'Refunds by Reason ({period_text.title()})',
        labels={'refund_date': 'Date', 'number_of_refunds': 'Number of Refunds', 'reason': 'Reason'}
    )
    fig.update_layout(template="plotly_white", bargap=0.2)
    
    return insight_text, fig.to_json(), sql_query

def get_sales_performance(payment_method: str = "all"):
    """Generates SQL and insights for sales performance."""
    conn = sqlite3.connect(DB_FILE)
    
    method_filter_str = ""
    method_text = "across all payment methods"
    if payment_method != "all":
        method_filter_str = f"AND payment_method = '{payment_method.upper()}'"
        method_text = f"for {payment_method.upper()}"

    sql_query = f"""
        SELECT
            CAST(strftime('%Y-%m-%d', timestamp) AS DATE) as transaction_date,
            SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as total_sales,
            COUNT(CASE WHEN status = 'completed' THEN 1 ELSE NULL END) as successful_transactions,
            COUNT(CASE WHEN status = 'failed' THEN 1 ELSE NULL END) as failed_transactions
        FROM transactions
        WHERE timestamp >= date('now', '-7 days')
        {method_filter_str}
        GROUP BY transaction_date
        ORDER BY transaction_date
    """
    
    df = pd.read_sql_query(sql_query, conn)
    conn.close()

    if df.empty:
        return f"No sales data found for {payment_method.upper()} in the last 7 days.", "{}", sql_query

    total_sales = df['total_sales'].sum()
    success_rate = (df['successful_transactions'].sum() / (df['successful_transactions'].sum() + df['failed_transactions'].sum())) * 100

    insight_text = (
        f"In the last 7 days, you've had total sales of ₹{total_sales:,.2f} {method_text}. "
        f"Your transaction success rate was {success_rate:.2f}%."
    )
    
    fig = px.line(
        df, 
        x='transaction_date', 
        y='total_sales', 
        title=f'Daily Sales Performance ({method_text.title()})',
        markers=True,
        labels={'transaction_date': 'Date', 'total_sales': 'Total Sales (INR)'}
    )
    fig.update_layout(template="plotly_white")

    return insight_text, fig.to_json(), sql_query


# --- API Endpoint ---
@app.post("/get-insight", response_model=InsightResponse)
async def get_insight(request: QueryRequest):
    """
    Receives a natural language query and returns a data insight.
    This is the main endpoint for the agent.
    """
    query = request.query.lower()
    
    # Simple keyword-based routing
    if "refund" in query:
        # Check for timeframes
        if "week" in query or "7 days" in query:
            insight_text, chart_json, sql_query = get_refund_analysis(time_period="week")
        else:
            insight_text, chart_json, sql_query = get_refund_analysis(time_period="yesterday")
            
    elif "sale" in query or "perform" in query:
        # Check for specific payment methods
        upi_match = re.search(r'\b(upi)\b', query)
        card_match = re.search(r'\b(card)\b', query)
        if upi_match:
            insight_text, chart_json, sql_query = get_sales_performance(payment_method="upi")
        elif card_match:
            insight_text, chart_json, sql_query = get_sales_performance(payment_method="card")
        else:
            insight_text, chart_json, sql_query = get_sales_performance(payment_method="all")
    else:
        insight_text = "Sorry, I can't answer that question yet. Try asking about 'refunds yesterday' or 'sales performance this week'."
        chart_json = "{}"
        sql_query = "N/A"

    return InsightResponse(
        insight_text=insight_text,
        chart_json=chart_json,
        query_used=sql_query
    )

# --- Root Endpoint for health check ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Welcome to the Merchant Insights API!"}