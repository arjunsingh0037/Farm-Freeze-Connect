"""
AI Service for FarmFreeze Connect
Integrates Amazon Bedrock AI for natural language processing
"""
import json
import os
import boto3
from botocore.exceptions import ClientError


def extract_farmer_intent(farmer_query: str) -> dict:
    """
    Extracts structured intent from a farmer's plain English query using Amazon Bedrock (Claude 3 Haiku).
    
    Args:
        farmer_query (str): The farmer's input text.
        
    Returns:
        dict: A dictionary containing the structured intent data.
        
    Raises:
        Exception: If the model invocation fails or the response is not valid JSON.
    """
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Configuration
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    region = os.environ.get("AWS_REGION", "us-east-1")
    
    # Initialize Bedrock Runtime Client
    try:
        aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        
        if not aws_access_key_id or not aws_secret_access_key:
            print("⚠️  AWS credentials not found, using mock AI response")
            return {
                "input_mode": "voice",
                "crop": "tomato",
                "quantity": 100,
                "unit": "kg",
                "time": "tomorrow",
                "intent": "find cold storage",
                "urgency": "high",
                "storage_type": "short-term",
                "confidence": 0.5,
                "missing_info": [],
                "mock": True,
                "error": "No AWS credentials"
            }
        
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
    except Exception as e:
        raise Exception(f"Failed to initialize Bedrock client: {str(e)}")

    # Construct the prompt
    prompt_template = """You are an AI decision engine for Indian smallholder farmers using a cold storage marketplace. 
 
 Your task is to extract structured intent from a farmer request. 
 
 IMPORTANT RULES: 
 - Return ONLY valid JSON. 
 - Do NOT add explanations. 
 - Do NOT include markdown. 
 - Do NOT include comments. 
 - Keep values normalized and simple. 
 
 Extract the following fields: 
 - input_mode: always "voice" 
 - crop: name of crop (lowercase) 
 - quantity: numeric value only 
 - unit: kg or ton 
 - time: when storage is needed (e.g., today, tomorrow, date) 
 - intent: farmer's goal (e.g., find cold storage) 
 - urgency: low / medium / high (today / tomorrow / kal → high; 2–3 days / next week → medium; later → low) 
 - storage_type: short-term / medium-term / long-term (tomato, leafy vegetables → short-term; potato, banana → medium-term; onion → long-term) 
 - confidence: number between 0 and 1 indicating certainty 
 - missing_info: list of strings indicating what information is missing (e.g., ["crop", "quantity"]) 
 
 Farmer request: 
 "{FARMER_QUERY}" """

    formatted_prompt = prompt_template.replace("{FARMER_QUERY}", farmer_query)

    # Prepare the request body for Claude 3 (Messages API)
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": formatted_prompt
            }
        ],
        "temperature": 0.0
    })

    try:
        # Invoke the model
        response = bedrock_runtime.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )

        # Parse the response body
        response_body = json.loads(response.get("body").read())
        
        # Extract the text content from the response
        response_content = response_body.get("content", [])
        if not response_content:
            raise Exception("Empty response content from model")
            
        response_text = response_content[0].get("text", "").strip()

        # Clean up potential markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()

        # Parse JSON and return as Python dict
        intent_data = json.loads(response_text)
        
        return intent_data

    except ClientError as e:
        error_message = str(e)
        if "AccessDeniedException" in error_message and "INVALID_PAYMENT_INSTRUMENT" in error_message:
            print("\n⚠️  AWS BEDROCK PAYMENT ISSUE:")
            print("   Your AWS account needs a valid payment method for Bedrock.")
            print("   Go to: AWS Console → Billing → Payment Methods")
            print("   Add a valid credit card, then try again.")
            print("   ⚠️  RETURNING MOCK DATA FOR NOW.\n")
            
            # Return a mock response so development can continue
            return {
                "input_mode": "voice",
                "crop": "tomato",
                "quantity": 100,
                "unit": "kg",
                "time": "tomorrow",
                "intent": "find cold storage",
                "urgency": "high",
                "storage_type": "short-term",
                "confidence": 0.5,
                "missing_info": [],
                "mock": True,
                "error": "Payment method required for Bedrock"
            }
        elif "Model use case details have not been submitted" in error_message:
            print("\n⚠️  AWS BEDROCK ERROR: You have not submitted the Use Case Details form for Anthropic models.")
            print("   👉 Go to AWS Console -> Bedrock -> Model access -> Manage model access -> Submit Use Case Details.")
            print("   ⚠️  RETURNING MOCK DATA FOR TESTING PURPOSES ONLY.\n")
            
            # Return a mock response so development can continue
            return {
                "input_mode": "voice",
                "crop": "tomato",
                "quantity": 100,
                "unit": "kg",
                "time": "tomorrow",
                "intent": "find cold storage",
                "urgency": "high",
                "storage_type": "short-term",
                "confidence": 0.5,
                "missing_info": [],
                "mock": True,
                "error": "Use case details required"
            }
        
        raise Exception(f"AWS Bedrock ClientError: {error_message}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse JSON response: {str(e)}. Response text: {response_text}")
    except Exception as e:
        raise Exception(f"An error occurred: {str(e)}")
