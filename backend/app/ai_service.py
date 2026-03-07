"""
AI Service for FarmFreeze Connect
Integrates Amazon Bedrock AI for natural language processing with Claude API fallback
"""
import json
import os
import boto3
import requests
from botocore.exceptions import ClientError


def extract_farmer_intent_claude_api(farmer_query: str) -> dict:
    """
    Fallback method using Claude API directly when Bedrock fails
    
    Args:
        farmer_query (str): The farmer's input text.
        
    Returns:
        dict: A dictionary containing the structured intent data.
    """
    # Get Claude API key from environment
    claude_api_key = os.environ.get("CLAUDE_API_KEY")
    
    if not claude_api_key:
        raise Exception("CLAUDE_API_KEY not found in environment variables.")
    
    # Construct the prompt (strictly follow the instructions)
    prompt_template = """You are an AI decision engine for Indian smallholder farmers using a cold storage marketplace. 
 
 Your task is to extract structured intent from a farmer request. 
 
 IMPORTANT RULES: 
 - Return ONLY valid JSON. 
 - Do NOT include explanations. 
 - Do NOT include markdown. 
 - Do NOT include comments. 
 - Normalize values. 
 
 RULES FOR URGENCY: 
 - today or tomorrow -> high 
 - 2-3 days -> medium 
 - later -> low 
 
 RULES FOR STORAGE TYPE: 
 - tomato -> short-term 
 - leafy vegetables -> short-term 
 - banana -> medium-term 
 - potato -> medium-term 
 - onion -> long-term 
 
 Extract ONLY the following fields in JSON: 
 - crop: string 
 - quantity: number (amount of crop, NOT duration)
 - unit: "kg" or "ton" 
 - time: string (when to start: today, tomorrow, etc.)
 - duration_days: number (how many days to store, extract from phrases like "5 days", "10 days", "एक हफ्ते". If not mentioned, return null)
 - intent: string 
 - urgency: "low" | "medium" | "high" 
 - storage_type: "short-term" | "medium-term" | "long-term" 
 - confidence: number (0.0 - 1.0) 
 
 Farmer request: 
 "{FARMER_QUERY}" """

    formatted_prompt = prompt_template.replace("{FARMER_QUERY}", farmer_query)
    
    # Claude API request
    headers = {
        "Content-Type": "application/json",
        "x-api-key": claude_api_key,
        "anthropic-version": "2023-06-01"
    }
    
    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 1024,
        "temperature": 0.0,
        "messages": [
            {
                "role": "user",
                "content": formatted_prompt
            }
        ]
    }
    
    try:
        print("🔄 Using Claude API fallback...")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Claude API error: {response.status_code} - {response.text}")
        
        response_data = response.json()
        response_text = response_data["content"][0]["text"].strip()
        
        # Clean up potential markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Parse JSON and add fallback indicator
        intent_data = json.loads(response_text)
        intent_data["fallback_used"] = "claude_api"
        
        print("✅ Claude API fallback successful")
        return intent_data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Claude API request failed: {e}")
        raise Exception(f"Claude API request failed: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"❌ Claude API JSON parsing failed: {e}")
        raise Exception(f"Failed to parse Claude API JSON response: {str(e)}. Response text: {response_text}")
    except Exception as e:
        print(f"❌ Claude API error: {e}")
        raise Exception(f"Claude API error: {str(e)}")


def extract_farmer_intent(farmer_query: str) -> dict:
    """
    Extracts structured intent from a farmer's plain English query using Amazon Bedrock (Claude 3 Haiku)
    with Claude API fallback when Bedrock fails.
    
    Args:
        farmer_query (str): The farmer's input text.
        
    Returns:
        dict: A dictionary containing the structured intent data.
        
    Raises:
        Exception: If both Bedrock and Claude API fail or responses are not valid JSON.
    """
    
    # Configuration
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    region = os.environ.get("AWS_REGION", "us-east-1")
    
    # Try Bedrock first
    try:
        aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        
        if not aws_access_key_id or not aws_secret_access_key:
            print("⚠️  AWS credentials not found, trying Claude API fallback...")
            return extract_farmer_intent_claude_api(farmer_query)
        
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        
        # Construct the prompt (strictly follow the instructions)
        prompt_template = """You are an AI decision engine for Indian smallholder farmers using a cold storage marketplace. 
 
 Your task is to extract structured intent from a farmer request. 
 
 IMPORTANT RULES: 
 - Return ONLY valid JSON. 
 - Do NOT include explanations. 
 - Do NOT include markdown. 
 - Do NOT include comments. 
 - Normalize values. 
 
 RULES FOR URGENCY: 
 - today or tomorrow -> high 
 - 2-3 days -> medium 
 - later -> low 
 
 RULES FOR STORAGE TYPE: 
 - tomato -> short-term 
 - leafy vegetables -> short-term 
 - banana -> medium-term 
 - potato -> medium-term 
 - onion -> long-term 
 
 Extract ONLY the following fields in JSON: 
 - crop: string 
 - quantity: number (amount of crop, NOT duration)
 - unit: "kg" or "ton" 
 - time: string (when to start: today, tomorrow, etc.)
 - duration_days: number (how many days to store, extract from phrases like "5 days", "10 days", "एक हफ्ते". If not mentioned, return null)
 - intent: string 
 - urgency: "low" | "medium" | "high" 
 - storage_type: "short-term" | "medium-term" | "long-term" 
 - confidence: number (0.0 - 1.0) 
 
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

        # Invoke the Bedrock model
        print("🔄 Trying AWS Bedrock...")
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
            raise Exception("Empty response content from Bedrock model")
            
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
        intent_data["fallback_used"] = "bedrock"
        
        print("✅ AWS Bedrock successful")
        return intent_data

    except ClientError as e:
        error_message = str(e)
        print(f"⚠️  AWS Bedrock failed: {error_message}")
        
        if "AccessDeniedException" in error_message and "INVALID_PAYMENT_INSTRUMENT" in error_message:
            print("   → Payment method issue, trying Claude API fallback...")
        elif "Model use case details have not been submitted" in error_message:
            print("   → Use case details not submitted, trying Claude API fallback...")
        else:
            print("   → Bedrock error, trying Claude API fallback...")
        
        # Try Claude API fallback
        try:
            return extract_farmer_intent_claude_api(farmer_query)
        except Exception as fallback_error:
            print(f"❌ Claude API fallback also failed: {fallback_error}")
            raise Exception(f"Both Bedrock and Claude API failed. Bedrock: {error_message}, Claude: {fallback_error}")
        
    except json.JSONDecodeError as e:
        print(f"⚠️  Bedrock JSON parsing failed: {e}")
        print("   → Trying Claude API fallback...")
        
        try:
            return extract_farmer_intent_claude_api(farmer_query)
        except Exception as fallback_error:
            print(f"❌ Claude API fallback also failed: {fallback_error}")
            raise Exception(f"Failed to parse JSON from both Bedrock and Claude API. Bedrock response: {response_text}")
    
    except Exception as e:
        print(f"⚠️  Bedrock initialization/request failed: {e}")
        print("   → Trying Claude API fallback...")
        
        try:
            return extract_farmer_intent_claude_api(farmer_query)
        except Exception as fallback_error:
            print(f"❌ Claude API fallback also failed: {fallback_error}")
            raise Exception(f"Both Bedrock and Claude API failed. Bedrock: {str(e)}, Claude: {fallback_error}")