# 🤖 Claude API Fallback Implementation Prompt

## Task Overview
Implement a robust AI service with Claude API fallback for a FarmFreeze Connect project. The system should try AWS Bedrock first, then fallback to direct Claude API, and finally use mock data if both fail.

## Required Changes

### 1. Modify AI Service File (`backend/app/ai_service.py`)

Replace the existing AI service with this enhanced version that includes Claude API fallback:

```python
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
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get Claude API key from environment
    claude_api_key = os.environ.get("CLAUDE_API_KEY")
    
    if not claude_api_key:
        print("⚠️  Claude API key not found, using mock response")
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
            "error": "No Claude API key",
            "fallback_used": "claude_api"
        }
    
    # Construct the prompt (same as Bedrock)
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
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
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
            # Return mock data as last resort
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
                "error": f"Both Bedrock and Claude API failed. Bedrock: {error_message}, Claude: {fallback_error}",
                "fallback_used": "mock"
            }
        
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
```

### 2. Update Environment Configuration

Create or update `backend/.env.example`:

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here

# Bedrock Model
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# Claude API Fallback (when Bedrock fails)
CLAUDE_API_KEY=your_claude_api_key_here

# S3 Bucket for Voice Storage
S3_BUCKET_NAME=farmfreeze-voice-uploads

# Database
DATABASE_URL=sqlite:///./farmfreeze.db

# Application Settings
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production
```

### 3. Ensure Dependencies

Make sure `requests` is in your `requirements.txt`:

```txt
# HTTP Requests
requests==2.31.0
```

### 4. Create Test Script

Create `test_claude_fallback.py` to verify the implementation:

```python
#!/usr/bin/env python3
"""
Test script for Claude API fallback functionality
"""
import sys
import os

# Add backend to path
sys.path.insert(0, 'backend')

def test_claude_fallback():
    """Test the Claude API fallback functionality"""
    print("🧪 Testing Claude API Fallback")
    print("=" * 40)
    
    try:
        from backend.app.ai_service import extract_farmer_intent
        
        # Test queries
        test_queries = [
            "मुझे 100 किलो टमाटर स्टोर करना है कल से",
            "I need to store 50 kg potatoes from tomorrow", 
            "मुझे स्टोरेज चाहिए",
            "Need cold storage for 200 kg onions"
        ]
        
        print("📝 Test Queries:")
        for i, query in enumerate(test_queries, 1):
            print(f"   {i}. {query}")
        
        print("\n🔄 Testing AI Processing...")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Test {i} ---")
            print(f"Input: {query}")
            
            try:
                result = extract_farmer_intent(query)
                
                # Show which service was used
                fallback_used = result.get('fallback_used', 'unknown')
                if fallback_used == 'bedrock':
                    print("✅ AWS Bedrock successful")
                elif fallback_used == 'claude_api':
                    print("🔄 Claude API fallback used")
                elif fallback_used == 'mock':
                    print("⚠️  Mock data used (both services failed)")
                
                # Show extracted data
                crop = result.get('crop', 'unknown')
                quantity = result.get('quantity', 0)
                unit = result.get('unit', 'kg')
                urgency = result.get('urgency', 'unknown')
                
                print(f"Extracted: {crop} - {quantity} {unit} (urgency: {urgency})")
                
                if result.get('mock'):
                    print(f"⚠️  Error: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n" + "=" * 40)
        print("🎉 Test completed!")
        
        # Show configuration status
        print("\n📋 Configuration Status:")
        aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
        claude_key = os.environ.get("CLAUDE_API_KEY")
        
        print(f"   AWS Credentials: {'✅ Found' if aws_key else '❌ Missing'}")
        print(f"   Claude API Key: {'✅ Found' if claude_key else '❌ Missing'}")
        
        if not aws_key and not claude_key:
            print("\n⚠️  No AI credentials found!")
            print("   Add to backend/.env:")
            print("   AWS_ACCESS_KEY_ID=your_aws_key")
            print("   CLAUDE_API_KEY=your_claude_key")
        elif not aws_key:
            print("\n💡 Only Claude API available (Bedrock will fallback)")
        elif not claude_key:
            print("\n💡 Only AWS Bedrock available (no fallback)")
        else:
            print("\n✅ Both AI services configured!")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're in the project root directory")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_claude_fallback()
```

### 5. Setup Instructions

1. **Get Claude API Key**: 
   - Visit https://console.anthropic.com/
   - Create account and generate API key
   - Add to `.env`: `CLAUDE_API_KEY=your_claude_api_key_here`

2. **Test the Implementation**:
   ```bash
   python test_claude_fallback.py
   ```

3. **Expected Behavior**:
   - System tries AWS Bedrock first
   - If Bedrock fails → Falls back to Claude API
   - If both fail → Returns mock data
   - Response includes `fallback_used` field indicating which service was used

### 6. Fallback Chain Logic

```
Primary: AWS Bedrock (Claude 3 Haiku)
    ↓ (if fails)
Fallback: Direct Claude API (claude-3-haiku-20240307)
    ↓ (if fails)
Last Resort: Mock Data
```

### 7. Error Handling

The system handles these failure scenarios:
- AWS credentials missing
- Bedrock payment method issues
- Use case details not submitted
- Network/SSL errors
- API rate limits
- JSON parsing errors

### 8. Response Format

All responses include a `fallback_used` field:
- `"bedrock"` - AWS Bedrock successful
- `"claude_api"` - Claude API fallback used
- `"mock"` - Both services failed, mock data returned

This implementation provides a robust AI service that gracefully degrades through multiple fallback layers, ensuring the application continues working even when primary services are unavailable.