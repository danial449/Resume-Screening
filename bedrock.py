import boto3
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS Session with Explicit Credentials
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION")
)

client = session.client("bedrock-runtime")

messages = [
    {"role": "user", "content": [{"text": "what is gpt"}]},
]

inference_config = {"temperature": 0}

model_response = client.converse(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",  # ✅ Corrected model ID
    messages=messages,
    inferenceConfig=inference_config
)

print("\n[Response Content Text]")
print(model_response["output"]["message"]["content"][0]["text"])
