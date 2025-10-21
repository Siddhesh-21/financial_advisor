🧠 Financial Advisor AI

A Generative AI-powered personal finance management assistant built using AWS Lambda, Bedrock, SageMaker, and Telegram.

🚀 Overview

Financial Advisor AI is an intelligent personal finance assistant that helps users track budgets, plan savings, and manage spending habits — all through an interactive Telegram bot.

The system integrates AWS Bedrock for intent understanding, AWS Lambda for event processing, RDS PostgreSQL for data persistence, and SageMaker for predictive analytics and personalization.

🧩 Features

💬 Telegram Bot Interface — Natural chat interface for managing goals, budgets, and financial advice.

🧠 AI-Powered Intent Classification via AWS Bedrock.

📊 Personalized Recommendations using SageMaker AI models.

💰 Budget Management — Track expenses, manage savings goals, and route requests to the “Budget Guardian.”

☁️ Serverless Architecture using AWS Lambda + API Gateway.

💾 Secure Storage in PostgreSQL (RDS) and /tmp for temporary session data.

🏗️ Architecture
Architecture Components

Telegram Bot → Frontend for user interaction.

AWS API Gateway → Entry point for Telegram webhook requests.

AWS Lambda (classification_function) → Routes user messages to relevant intent handlers.

Intent Lambda Functions:

goal_intent_function

budget_intent_function

guardian_notification_function

AWS Bedrock → Natural Language Understanding (intent detection).

AWS SageMaker → Financial prediction and recommendation models.

AWS RDS (PostgreSQL) → Persistent storage for goals, budgets, and transactions.

/tmp Storage in Lambda → Temporary session memory.

Architecture Diagram

📎 (Paste your generated architecture image here)


⚙️ How We Built It
Component	Technology
Frontend	Telegram Bot
API Layer	AWS API Gateway
Business Logic	AWS Lambda (Python)
AI/ML	AWS Bedrock, SageMaker
Database	Amazon RDS (PostgreSQL)
Temporary Storage	Lambda /tmp
Monitoring	CloudWatch Logs
💡 Inspiration

Managing finances can be overwhelming. We wanted to create an AI-powered financial guardian that not only tracks spending but also learns user behavior, provides personalized recommendations, and helps users stay accountable — all within an intuitive Telegram interface.

🧱 Challenges We Faced

Configuring Telegram webhooks with AWS API Gateway and Lambda.

Handling stateful memory in a stateless Lambda environment.

Integrating Bedrock for intent understanding and SageMaker for insights.

Ensuring real-time, secure message flow from Telegram → AWS → RDS.

🏆 Accomplishments

Fully serverless, AI-powered finance assistant.

Automated budget routing and notifications.

Clean integration between Telegram, AWS Bedrock, and RDS.

Lightweight, scalable architecture ready for production.

📚 What We Learned

Best practices for serverless architecture design.

How to integrate Generative AI (Bedrock) with conversational systems.

Using SageMaker for real-world financial modeling and recommendations.

Efficient use of /tmp memory in AWS Lambda for short-term data storage.

🔮 What’s Next

Add voice-based financial coaching using Amazon Transcribe.

Build investment recommendation engine with real-time market insights.

Deploy multi-user authentication with Amazon Cognito.

Expand analytics and visualization dashboards.

🧰 Installation & Setup
Prerequisites

AWS Account with access to:

Lambda

API Gateway

Bedrock

SageMaker

RDS (PostgreSQL)

Telegram Bot Token (from @BotFather
)

Python 3.9+

Steps

Clone this repository:

git clone https://github.com/Siddhesh-21/financial_advisor.git
cd financial_advisor


Set up environment variables:

export TELEGRAM_BOT_TOKEN=<your_bot_token>
export DB_HOST=<rds_endpoint>
export DB_USER=<username>
export DB_PASS=<password>
export DB_NAME=<database_name>


Deploy Lambda functions:

classification_function

goal_intent_function

budget_intent_function

guardian_notification_function

Configure API Gateway:

Set endpoint: /prod/webhook

Integrate with classification Lambda.

Set Telegram webhook:

curl -F "url=https://<api_gateway_url>/prod/webhook" \
     https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook


Monitor in CloudWatch for real-time logs.

🧑‍💻 Team

Developer: Siddhesh Kushare

Role: Architect, AI Engineer, Full-Stack Developer
