import json
import boto3
import psycopg2
import re
from decimal import Decimal
from datetime import date, datetime
import os

# ---------- Helper Functions ----------

def serialize_special(obj):
    """Convert Decimal and datetime objects to JSON-serializable types."""
    if isinstance(obj, list):
        return [serialize_special(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: serialize_special(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    else:
        return obj


# ---------- Memory Layer (stored in /tmp) ----------

MEMORY_FILE = "/tmp/memory.json"

def load_memory():
    """Load memory from /tmp (if exists)."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_memory(memory):
    """Save memory to /tmp."""
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f)

def get_user_context(user_id):
    """Get context for specific user."""
    memory = load_memory()
    return memory.get(user_id, "")

def update_user_context(user_id, user_query, response):
    """Append new conversation to user’s context."""
    memory = load_memory()
    context = memory.get(user_id, "")
    context += f"\nUser: {user_query}\nAssistant: {response}\n"
    memory[user_id] = context
    save_memory(memory)


# ---------- Bedrock SQL Generator ----------

def generate_sql(user_query, memory_context):
    """Use Bedrock to generate SQL for the user query."""
    prompt = f"""You are an expert financial SQL assistant.
You will receive user's conversation context and question.
Generate a valid PostgreSQL query based on the following tables:

Table: transactions
- id (serial primary key)
- amount (numeric)
- transaction_type (text)  # 'credit' or 'debit'
- transaction_date (date)
- category (text)
- raw_message (text)
- created_at (timestamp)

Table: goal
- id (serial primary key)
- goal_name (text)
- target_amount (numeric)
- target_date (date)
- category (text)
- raw_message (text)

Rules:
1. Always use `age(date1, date2)` for date differences.
2. To calculate remaining months: `EXTRACT(MONTH FROM age(target_date, CURRENT_DATE))`.
3. Return only a valid SQL query — no markdown or explanations.

User Context: {memory_context}
User Question: '{user_query}'
"""

    client = boto3.client("bedrock-runtime", region_name="eu-north-1")

    response = client.converse(
        modelId="amazon.nova-lite-v1:0",
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 400, "temperature": 0.3, "topP": 0.9}
    )

    raw_text = response["output"]["message"]["content"][0]["text"].strip()
    sql_query = re.sub(r"```sql|```", "", raw_text).strip()
    return sql_query


# ---------- Bedrock Text Generator ----------

def generate_textual_response(user_query, data, memory_context):
    """Convert SQL result to natural answer using Bedrock."""
    client = boto3.client("bedrock-runtime", region_name="eu-north-1")
    prompt = f"""
You are a friendly financial assistant with short-term memory.
Use the previous conversation and new data to answer naturally.

User Context: {memory_context}
User Question: "{user_query}"
Database Results: {json.dumps(data)}
"""
    response = client.converse(
        modelId="amazon.nova-lite-v1:0",
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 250, "temperature": 0.5}
    )
    return response["output"]["message"]["content"][0]["text"].strip()


# ---------- Lambda Handler ----------

def lambda_handler(event, context):
    user_query = event.get("message", "")
    user_id = event.get("user_id", "default_user")

    if not user_query:
        return {"statusCode": 400, "body": "No query found"}

    try:
        # 1️⃣ Load memory
        memory_context = get_user_context(user_id)

        # 2️⃣ Generate SQL
        sql_query = generate_sql(user_query, memory_context)

        # 3️⃣ Execute SQL
        conn = psycopg2.connect(
            host="finprod.cvcamc60mtim.eu-north-1.rds.amazonaws.com",
            port="5432",
            database="finprod",
            user="postgres",
            password="Siddhesh"
        )
        cursor = conn.cursor()
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        conn.close()

        data = serialize_special([dict(zip(columns, row)) for row in results])

        # 4️⃣ Generate human response
        textual_response = generate_textual_response(user_query, data, memory_context)

        # 5️⃣ Update in-memory context
        update_user_context(user_id, user_query, textual_response)

        # 6️⃣ Return
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": textual_response,
                "generated_sql": sql_query,
                "data": data
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "sql": sql_query if 'sql_query' in locals() else None
            })
        }
