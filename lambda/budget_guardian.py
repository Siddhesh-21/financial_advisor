import os
import json
import boto3
from datetime import datetime, timedelta
import psycopg2

# Initialize Bedrock
bedrock = boto3.client("bedrock-runtime", region_name="eu-north-1")

# PostgreSQL connection settings
DB_HOST = os.environ["DB_HOST"]
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]

MEMORY_FILE = "/tmp/memory.json"  # ephemeral Lambda memory

def load_memory():
    """Load chat memory (context) from /tmp"""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_memory(memory):
    """Save chat memory to /tmp"""
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory[-20:], f)  # limit to last 20 exchanges for efficiency

def get_recent_transactions(days=1):
    """Fetch recent transactions from PostgreSQL"""
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    conn = psycopg2.connect(
        host=DB_HOST,
        port="5432",
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    query = f"""
        SELECT amount, transaction_type, category, transaction_date
        FROM transactions
        WHERE transaction_date >= '{start_date}' AND transaction_date <= '{end_date}';
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    txns = [
        {
            "amount": float(r[0]),
            "type": r[1],
            "category": r[2],
            "date": str(r[3])
        }
        for r in rows
    ]
    return txns

def summarize_spending(txns):
    """Aggregate basic stats"""
    total_spent = sum(t["amount"] for t in txns if t["type"] == "debit")
    total_earned = sum(t["amount"] for t in txns if t["type"] == "credit")
    return {
        "spent": round(total_spent, 2),
        "earned": round(total_earned, 2),
        "net_balance": round(total_earned - total_spent, 2)
    }

def generate_context(memory, user_input, spending_summary):
    """Prepare prompt for Bedrock model with context"""
    context_snippets = "\n".join(
        [f"User: {m['user']}\nAgent: {m['agent']}" for m in memory[-5:]]
    )

    prompt = f"""
You are Budget Guardian, an agent that helps users stay within their spending limits.

Here is the recent memory of the conversation and events:
{context_snippets}

User's spending summary:
- Total spent today: ₹{spending_summary['spent']}
- Total earned today: ₹{spending_summary['earned']}
- Net balance: ₹{spending_summary['net_balance']}

Now the user says: "{user_input}"

Based on past context and current data, respond naturally with a short alert or insight.
Mention patterns if noticed (e.g., overspending, improvement, consistency).
    """
    return prompt.strip()

def query_bedrock(prompt):
    """Send the contextual prompt to Bedrock"""
    response = bedrock.converse(
        modelId="amazon.nova-lite-v1:0",
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 300, "temperature": 0.4},
    )
    return response["output"]["message"]["content"][0]["text"]

def lambda_handler(event, context):
    user_input = event.get("message", "")
    if not user_input:
        return {"statusCode": 400, "body": "No input message"}

    # Step 1. Load conversation memory
    memory = load_memory()

    # Step 2. Fetch spending summary
    transactions = get_recent_transactions(days=1)
    spending_summary = summarize_spending(transactions)

    # Step 3. Generate contextual prompt
    prompt = generate_context(memory, user_input, spending_summary)

    # Step 4. Query Bedrock
    bedrock_reply = query_bedrock(prompt)

    # Step 5. Update memory
    memory.append({"user": user_input, "agent": bedrock_reply, "timestamp": datetime.utcnow().isoformat()})
    save_memory(memory)

    # Step 6. Return result
    return {
        "statusCode": 200,
        "body": json.dumps({
            "agent": "budget_guardian",
            "response": bedrock_reply
        })
    }
