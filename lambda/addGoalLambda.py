import json
import boto3
import psycopg2
from psycopg2 import sql
from datetime import datetime,date
current_date=date.today()
def lambda_handler(event, context):
    # Step 1: Extract user message
    message = event.get('message', '')
    if not message:
        return {"statusCode": 400, "body": "No message found"}

    # Step 2: Create Bedrock prompt
    prompt = f"""
You are an intelligent goal analyzer.
Your task is to extract structured financial goal details from the user's message.
Current date={current_date}
Return a valid JSON object with the following keys:
- goal_name: short title of the goal
- target_amount: numeric value (no currency symbols)
- target_date: in YYYY-MM-DD format if a time period or date is mentioned, else null
- category: classify the goal as one of ["savings", "investment", "loan_repayment", "education", "travel", "health", "emergency", "other"]
if target_date is provided as 1 year from now calculate it using current date.

If no date or timespan is provided by default set it to 1 year or calculate from statement if it says i want to save 30000 for my trip and monthly i will save 5000 so it will take 6 months. Be smart be productive.
Example Input: "I want to save 50,000 rupees for a vacation by March 2026"
Example Output:
{{
  "goal_name": "Vacation Savings",
  "target_amount": 50000,
  "target_date": "2026-03-01",
  "category": "travel"
}}

Example Input: I want to plan a trip to Tokyo, Japan for that I need to save 300000, my monthly saving for that trip should be 20000.
Example Output:
{{
    "goal_name": "Tokyo, Japan trip"
    "target_amount": 300000,
    "target_date": "2027-01-19"
    "category": "Travel"
}}
In above example I calculated the time as the date for e.g. I considered 19th October 2025 and then 300000/20000 = 15 months so 15 months would be 19th January 2027.

Now, analyze this message:
{message}
"""

    # Step 3: Initialize Bedrock client
    client = boto3.client('bedrock-runtime', region_name='eu-north-1')

    # Step 4: Prepare Bedrock messages
    messages = [
        {
            "role": "user",
            "content": [{"text": prompt}]
        }
    ]

    # Step 5: Call Bedrock model
    response = client.converse(
        modelId="amazon.nova-lite-v1:0",
        messages=messages,
        inferenceConfig={
            "maxTokens": 300,
            "temperature": 0.7,
            "topP": 0.9
        }
    )

    # Step 6: Extract raw text output
    raw_output = response["output"]["message"]["content"][0]["text"]

    # Step 7: Clean and parse model response
    try:
        cleaned_output = raw_output.strip().strip("```json").strip("```").strip()
        extracted_data = json.loads(cleaned_output)
    except Exception:
        extracted_data = {"error": "Invalid JSON", "raw": raw_output}

    # Step 8: Insert parsed goal into PostgreSQL
    try:
        conn = psycopg2.connect(
            host="finprod.cvcamc60mtim.eu-north-1.rds.amazonaws.com",
            port="5432",
            database="finprod",
            user="postgres",
            password="Siddhesh"
        )
        cursor = conn.cursor()

        # Insert new goal record
        cursor.execute(
            sql.SQL("""
                INSERT INTO goal (goal_name, target_amount, target_date, category, raw_message)
                VALUES (%s, %s, %s, %s, %s)
            """),
            (
                extracted_data.get("goal_name"),
                extracted_data.get("target_amount"),
                extracted_data.get("target_date"),
                extracted_data.get("category"),
                message
            )
        )

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Failed to insert goal into PostgreSQL",
                "details": str(e),
                "parsed_data": extracted_data
            })
        }

    # Step 9: Return final result
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Goal parsed and stored successfully",
            "data": extracted_data
        })
    }
