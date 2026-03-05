"""
Notification Service for FarmFreeze Connect
Handles SMS notifications using Amazon SNS
"""
import boto3
import os
from typing import Optional

class NotificationService:
    """Service for sending notifications to farmers"""
    
    def __init__(self):
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        
        # Initialize AWS SNS client
        try:
            aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
            
            if not aws_access_key_id or not aws_secret_access_key:
                print("⚠️  AWS credentials not found for SNS")
                self.sns_client = None
                return
            
            self.sns_client = boto3.client(
                'sns',
                region_name=self.region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            print("✅ AWS SNS client initialized successfully")
        except Exception as e:
            print(f"Warning: AWS SNS initialization failed: {e}")
            self.sns_client = None

    def send_sms(self, phone_number: str, message: str) -> Optional[str]:
        """
        Send SMS notification via Amazon SNS
        
        Args:
            phone_number: Farmer's phone number (with country code, e.g., +91...)
            message: SMS message content
            
        Returns:
            Message ID if successful, None otherwise
        """
        if not self.sns_client:
            print("⚠️  SNS client not available, skipping SMS")
            return None
            
        try:
            # Ensure phone number is in E.164 format (simplified check)
            if not phone_number.startswith('+'):
                phone_number = f"+91{phone_number}" # Default to India
                
            response = self.sns_client.publish(
                PhoneNumber=phone_number,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SenderID': {
                        'DataType': 'String',
                        'StringValue': 'FRMFREEZE'
                    },
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': 'Transactional'
                    }
                }
            )
            message_id = response.get('MessageId')
            print(f"✅ SMS sent successfully to {phone_number}. MessageId: {message_id}")
            return message_id
        except Exception as e:
            print(f"❌ Failed to send SMS via SNS: {e}")
            return None

    def send_booking_confirmation(self, farmer_name: str, phone_number: str, booking_ref: str, storage_name: str, qty: float):
        """Send a standard booking confirmation SMS"""
        message = (
            f"Namaste {farmer_name}! Your FarmFreeze booking is CONFIRMED.\n"
            f"Ref: {booking_ref}\n"
            f"Storage: {storage_name}\n"
            f"Quantity: {qty} kg\n"
            f"Thank you for using FarmFreeze Connect!"
        )
        return self.send_sms(phone_number, message)

# Global notification service instance
notification_service = NotificationService()
