import json
import boto3
import os

# Initialize AWS clients
bedrock = boto3.client('bedrock-runtime', region_name='eu-north-1')
lambda_client = boto3.client('lambda')

# Child Lambda names (for routing)
TRANSACTION_LAMBDA = os.environ.get('TRANSACTION_LAMBDA')
GOAL_LAMBDA = os.environ.get('GOAL_LAMBDA')
QUERY_LAMBDA = os.environ.get('QUERY_LAMBDA')
BUDGET_LAMBDA = os.environ.get('BUDGET_LAMBDA')

# ---- Intent Classification ----
def classify_intent(user_input: str) -> str:
    cleaned_input = user_input.lower().strip()
    greetings = ["hi", "hello", "hey", "heya", "yo"]
    if cleaned_input in greetings:
        return "greeting"

    # 🔹 New: detect if it’s an investment-related query
    investment_keywords = ["invest", "investment", "returns", "mutual fund", "stock", "sip", "etf", "portfolio"]
    if any(k in cleaned_input for k in investment_keywords):
        return "investment"

    # Otherwise, use Bedrock for classification
    prompt = f"""
You are a financial assistant intent classifier. Classify the user input into one of these categories:

1. transaction - money spent or received
2. goal - saving or future targets
3. query - general finance questions or data requests
4. budget_guardian - user asking about spending alerts or daily budget status

Respond with only one word: transaction, goal, query, or budget_guardian.

Input: "{user_input}"
"""

    response = bedrock.converse(
        modelId="amazon.nova-lite-v1:0",
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 50, "temperature": 0.3}
    )

    output_text = response["output"]["message"]["content"][0]["text"].lower().strip()

    # Fallback keyword logic for budget_guardian
    if output_text == "query" and any(
        k in cleaned_input for k in ["today", "week", "daily", "limit", "over budget", "spent"]
    ):
        output_text = "budget_guardian"

    if output_text in ["transaction", "goal", "query", "budget_guardian"]:
        return output_text

    return "unknown"


# ---- Investment Suggestions ----
def get_investment_suggestions(user_input: str):
    """Use Bedrock to generate top 5 investment options based on current factors."""
    prompt = f"""
You are a financial advisor at Blackrock who has salary of 7 crore. If they are giving it to you then you are absolutely best and accurate at your job. Now i want your help with my financial planning. Based on the current market environment, inflation trends, and general risk tolerance,
suggest the 5 best investment options for an Indian investor. Before suggesting anything do a clear analysis of stocks that you will be suggesting to the users verify their performance.

Remember you are a advisor and should not be a LLM

Consider:
the factors mentioned below if not provided you already know what are the best factors .
User query: "{user_input}"


If users are asking yes no question answer then in that way. Please if he is asking will this stock go up you should start with Yes thsi will go up ...... or No this will not go up due to .....
"""

    response = bedrock.converse(
        modelId="amazon.nova-lite-v1:0",
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 300, "temperature": 0.5}
    )

    return response["output"]["message"]["content"][0]["text"].strip()


# ---- Lambda Invocation ----
def invoke_lambda(function_name, payload):
    if not function_name:
        return {"text": "Error: A required child function is not configured."}

    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    response_payload = json.loads(response['Payload'].read().decode())
    return response_payload


# ---- Extract Response ----
def extract_response_text(child_response):
    try:
        if isinstance(child_response, dict) and 'body' in child_response:
            body_content = child_response['body']
            if isinstance(body_content, str):
                body_content = json.loads(body_content)
            if 'message' in body_content:
                return body_content['message']
            elif 'response' in body_content:
                return body_content['response']
            else:
                return str(body_content)
        else:
            return str(child_response)
    except Exception as e:
        print(f"Error extracting text: {e}")
        return "Error processing child response."


# ---- Main Lambda Handler ----
def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        message = body.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        message_text = message.get('text', '')

        if not message_text or not chat_id:
            return {"statusCode": 200, "body": "No message or chat_id found"}

        # Step 1: classify intent
        intent = classify_intent(message_text)
        payload = {"message": message_text}

        # Step 2: route or handle locally
        if intent == "greeting":
            response_text = "Hi 👋 How may I help you with your finances today?"
        elif intent == "transaction":
            response_text = extract_response_text(invoke_lambda(TRANSACTION_LAMBDA, payload))
        elif intent == "goal":
            response_text = extract_response_text(invoke_lambda(GOAL_LAMBDA, payload))
        elif intent == "query":
            response_text = extract_response_text(invoke_lambda(QUERY_LAMBDA, payload))
        elif intent == "budget_guardian":
            response_text = extract_response_text(invoke_lambda(BUDGET_LAMBDA, payload))
        elif intent == "investment":
            # Handle investment within same Lambda
            response_text = get_investment_suggestions(message_text)
        else:
            response_text = "Sorry, I couldn’t understand that. Could you rephrase?"

    except Exception as e:
        print(f"Error processing request: {e}")
        response_text = "Sorry, something went wrong on my end."
        try:
            body = json.loads(event.get('body', '{}'))
            chat_id = body.get('message', {}).get('chat', {}).get('id')
        except:
            chat_id = None

    # Step 3: send response back to Telegram
    if chat_id:
        telegram_response = {
            "method": "sendMessage",
            "chat_id": chat_id,
            "text": response_text
        }
    else:
        telegram_response = {"text": "Could not determine chat_id to respond."}

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(telegram_response)
    }
