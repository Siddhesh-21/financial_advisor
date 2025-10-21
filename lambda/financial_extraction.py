import json
import boto3
import psycopg2
from psycopg2 import sql
import datetime

current_date = datetime.date.today()
def lambda_handler(event, context):
    # Step 1: Extract message
    message = event.get('message', '')
    if not message:
        return {"statusCode": 400, "body": "No message found"}

    # Step 2: Prepare Bedrock prompt
    prompt = f"""You are an intelligent financial transaction parser.
Extract structured details from the transaction message and classify it into a category.

Return a JSON object with the following keys:
- amount: the transaction amount as a number (without currency symbols)
- transaction_type: "debit" or "credit"
- transaction_date: the date of the transaction in YYYY-MM-DD format
- category: classify the transaction as one of ["salary", "grocery", "entertainment", "utility", "restaurant", "transport", "other"]


Current date = {current_date}
Note if transaction date is not mentioned get it as current_date. If mentioned today or yesterday or so get the date accordingly as per the logic today means current date yesteray mean current date -1
Here is the transaction message:
{message}"""

    # Step 3: Initialize Bedrock client
    client = boto3.client('bedrock-runtime', region_name='eu-north-1')

    # Step 4: Prepare messages for Bedrock
    messages = [
        {
            "role": "user",
            "content": [{"text": prompt}]
        }
    ]

    # Step 5: Call Bedrock
    try:
        response = client.converse(
            modelId="amazon.nova-lite-v1:0",
            messages=messages,
            inferenceConfig={
                "maxTokens": 300,
                "temperature": 0.7,
                "topP": 0.9
            }
        )
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": "Bedrock call failed", "details": str(e)})}

    # Step 6: Extract model output
    try:
        raw_output = response["output"]["message"]["content"][0]["text"]
        extracted_text = raw_output.strip().strip("```json").strip("```").strip()
        extracted_data = json.loads(extracted_text)
    except Exception:
        extracted_data = {"error": "Model did not return valid JSON", "raw": raw_output}

    # Step 7: Write to PostgreSQL
    try:
        conn = psycopg2.connect(
            host="finprod.cvcamc60mtim.eu-north-1.rds.amazonaws.com",
            port="5432",
            database="finprod",
            user="postgres",
            password="Siddhesh"
        )
        cursor = conn.cursor()

        # Insert parsed record
        cursor.execute(
            sql.SQL("""
                INSERT INTO transactions (amount, transaction_type, transaction_date, category, raw_message)
                VALUES (%s, %s, %s, %s, %s)
            """),
            (
                extracted_data.get("amount"),
                extracted_data.get("transaction_type"),
                extracted_data.get("transaction_date"),
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
                "error": "Failed to write to PostgreSQL",
                "details": str(e),
                "parsed_data": extracted_data
            })
        }

    # Step 8: Return final result
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Transaction parsed and stored successfully",
            "data": extracted_data
        })
    }
