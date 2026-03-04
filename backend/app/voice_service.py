"""
Voice Service for FarmFreeze Connect
Handles voice input processing using Amazon Transcribe
"""
import boto3
import json
import time
import uuid
import os
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any
import tempfile
import wave


class VoiceService:
    """Service for handling voice input and transcription"""
    
    def __init__(self):
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self.s3_bucket = os.environ.get("S3_BUCKET_NAME", "farmfreeze-voice-uploads")
        
        # Load environment variables from .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        # Initialize AWS clients
        try:
            aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
            
            if not aws_access_key_id or not aws_secret_access_key:
                print("⚠️  AWS credentials not found in environment")
                self.transcribe_client = None
                self.s3_client = None
                self.polly_client = None
                return
            
            self.transcribe_client = boto3.client(
                'transcribe',
                region_name=self.region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            self.s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            self.polly_client = boto3.client(
                'polly',
                region_name=self.region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            print("✅ AWS clients initialized successfully")
        except Exception as e:
            print(f"Warning: AWS clients initialization failed: {e}")
            self.transcribe_client = None
            self.s3_client = None
            self.polly_client = None
    
    def upload_audio_to_s3(self, audio_file_path: str, object_key: str) -> str:
        """
        Upload audio file to S3 bucket
        
        Args:
            audio_file_path: Local path to audio file
            object_key: S3 object key
            
        Returns:
            S3 URI of uploaded file
        """
        try:
            self.s3_client.upload_file(
                audio_file_path,
                self.s3_bucket,
                object_key
            )
            return f"s3://{self.s3_bucket}/{object_key}"
        except Exception as e:
            raise Exception(f"Failed to upload audio to S3: {str(e)}")
    
    def start_transcription_job(self, audio_s3_uri: str, job_name: str, language_code: str = "hi-IN") -> str:
        """
        Start Amazon Transcribe job
        
        Args:
            audio_s3_uri: S3 URI of audio file
            job_name: Unique job name
            language_code: Language code (hi-IN for Hindi, en-IN for Indian English)
            
        Returns:
            Job name
        """
        try:
            response = self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': audio_s3_uri},
                MediaFormat='wav',  # Assuming WAV format
                LanguageCode=language_code,
                Settings={
                    'ShowSpeakerLabels': False,
                    'ShowAlternatives': True,
                    'MaxAlternatives': 3
                }
            )
            return job_name
        except Exception as e:
            raise Exception(f"Failed to start transcription job: {str(e)}")
    
    def get_transcription_result(self, job_name: str, max_wait_time: int = 60) -> Dict[str, Any]:
        """
        Get transcription result (with polling)
        
        Args:
            job_name: Transcription job name
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            Transcription result
        """
        try:
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                response = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    # Get the transcript
                    transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    
                    # Download transcript content
                    import urllib.request
                    with urllib.request.urlopen(transcript_uri) as response:
                        transcript_content = response.read().decode('utf-8')
                    transcript_data = json.loads(transcript_content)
                    
                    # Extract the main transcript
                    transcript_text = transcript_data['results']['transcripts'][0]['transcript']
                    
                    return {
                        'status': 'completed',
                        'transcript': transcript_text,
                        'confidence': self._calculate_average_confidence(transcript_data),
                        'alternatives': self._extract_alternatives(transcript_data)
                    }
                
                elif status == 'FAILED':
                    failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                    raise Exception(f"Transcription failed: {failure_reason}")
                
                # Wait before polling again
                time.sleep(2)
            
            raise Exception(f"Transcription job timed out after {max_wait_time} seconds")
            
        except Exception as e:
            raise Exception(f"Failed to get transcription result: {str(e)}")
    
    def _calculate_average_confidence(self, transcript_data: Dict) -> float:
        """Calculate average confidence score from transcript data"""
        try:
            items = transcript_data['results']['items']
            confidences = [float(item.get('alternatives', [{}])[0].get('confidence', 0)) 
                          for item in items if 'alternatives' in item]
            return sum(confidences) / len(confidences) if confidences else 0.0
        except:
            return 0.0
    
    def _extract_alternatives(self, transcript_data: Dict) -> list:
        """Extract alternative transcriptions"""
        try:
            alternatives = transcript_data['results']['transcripts']
            return [alt['transcript'] for alt in alternatives[:3]]  # Top 3 alternatives
        except:
            return []
    
    def transcribe_audio_file(self, audio_file_path: str, language_code: str = "hi-IN") -> Dict[str, Any]:
        """
        Complete transcription workflow for audio file
        
        Args:
            audio_file_path: Path to audio file
            language_code: Language code
            
        Returns:
            Transcription result
        """
        if not self.transcribe_client or not self.s3_client:
            # Return mock data for development
            return self._get_mock_transcription(audio_file_path)
        
        try:
            # Generate unique identifiers
            job_name = f"farmfreeze-transcribe-{uuid.uuid4().hex[:8]}"
            object_key = f"audio/{job_name}.wav"
            
            # Upload to S3
            audio_s3_uri = self.upload_audio_to_s3(audio_file_path, object_key)
            
            # Start transcription
            self.start_transcription_job(audio_s3_uri, job_name, language_code)
            
            # Get result
            result = self.get_transcription_result(job_name)
            
            # Cleanup S3 object (optional)
            try:
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=object_key)
            except:
                pass  # Ignore cleanup errors
            
            return result
            
        except Exception as e:
            raise Exception(f"Audio transcription failed: {str(e)}")
    
    def transcribe_audio_bytes(self, audio_bytes: bytes, language_code: str = "hi-IN") -> Dict[str, Any]:
        """
        Transcribe audio from bytes data
        
        Args:
            audio_bytes: Audio data as bytes
            language_code: Language code
            
        Returns:
            Transcription result
        """
        # Save bytes to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name
        
        try:
            result = self.transcribe_audio_file(temp_file_path, language_code)
            return result
        finally:
            # Cleanup temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    def _get_mock_transcription(self, audio_file_path: str) -> Dict[str, Any]:
        """Return mock transcription for development/testing"""
        
        # Simple mock based on file name or return generic
        mock_transcripts = [
            "मुझे 100 किलो टमाटर स्टोर करना है कल से",
            "I need to store 50 kg potatoes from tomorrow",
            "मुझे 200 किलो प्याज के लिए कोल्ड स्टोरेज चाहिए आज से",
            "Need cold storage for 150 kg tomatoes starting today",
            "मुझे आलू के लिए स्टोरेज चाहिए 75 किलो"
        ]
        
        # Use a simple hash to pick consistent mock data
        import hashlib
        file_hash = hashlib.md5(audio_file_path.encode()).hexdigest()
        mock_index = int(file_hash[:2], 16) % len(mock_transcripts)
        
        return {
            'status': 'completed',
            'transcript': mock_transcripts[mock_index],
            'confidence': 0.85,
            'alternatives': [mock_transcripts[mock_index]],
            'mock': True
        }

    def generate_voice_recommendation(self, text: str, language_code: str = "hi-IN") -> bytes:
        """
        Generate voice recommendation using Amazon Polly
        
        Args:
            text: Text to convert to speech
            language_code: Language code (hi-IN for Hindi, en-IN for Indian English)
            
        Returns:
            Audio bytes
        """
        if not self.polly_client:
            # Return mock audio for development
            return self._get_mock_audio()
        
        try:
            # Map language codes to Polly voice IDs
            voice_map = {
                "hi-IN": "Aditi",  # Hindi voice
                "en-IN": "Raveena",  # Indian English voice
                "en-US": "Joanna"  # US English voice
            }
            
            voice_id = voice_map.get(language_code, "Aditi")
            
            # Generate speech
            response = self.polly_client.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=voice_id,
                LanguageCode=language_code if language_code in ["hi-IN", "en-IN"] else None
            )
            
            # Return audio stream
            return response['AudioStream'].read()
            
        except Exception as e:
            raise Exception(f"Voice generation failed: {str(e)}")
    def store_voice_input_s3(self, audio_bytes: bytes, farmer_info: dict, language_code: str = "hi-IN") -> dict:
        """
        Store voice input in S3 bucket with metadata

        Args:
            audio_bytes: Audio data as bytes
            farmer_info: Dictionary with farmer details (name, phone, etc.)
            language_code: Language code

        Returns:
            Dictionary with S3 storage information
        """
        try:
            # Generate unique filename with timestamp and farmer info
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            farmer_name = farmer_info.get('name', 'unknown').replace(' ', '_')
            farmer_phone = farmer_info.get('phone', 'unknown')

            # Create structured S3 key
            s3_key = f"voice-inputs/{timestamp}_{farmer_name}_{farmer_phone[-4:]}_{language_code}.wav"

            if not self.s3_client:
                # Mock storage for development
                return {
                    'stored': True,
                    's3_key': s3_key,
                    's3_uri': f"s3://{self.s3_bucket}/{s3_key}",
                    'bucket': self.s3_bucket,
                    'size_bytes': len(audio_bytes),
                    'timestamp': timestamp,
                    'mock': True
                }

            # Save bytes to temporary file first
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name

            try:
                # Upload to S3 with metadata
                self.s3_client.upload_file(
                    temp_file_path,
                    self.s3_bucket,
                    s3_key,
                    ExtraArgs={
                        'Metadata': {
                            'farmer-name': farmer_info.get('name', 'unknown'),
                            'farmer-phone': farmer_info.get('phone', 'unknown'),
                            'language-code': language_code,
                            'upload-timestamp': timestamp,
                            'content-type': 'audio/wav'
                        },
                        'ContentType': 'audio/wav'
                    }
                )

                return {
                    'stored': True,
                    's3_key': s3_key,
                    's3_uri': f"s3://{self.s3_bucket}/{s3_key}",
                    'bucket': self.s3_bucket,
                    'size_bytes': len(audio_bytes),
                    'timestamp': timestamp,
                    'mock': False
                }

            finally:
                # Cleanup temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

        except Exception as e:
            raise Exception(f"Failed to store voice input in S3: {str(e)}")

    def list_stored_voice_inputs(self, farmer_phone: str = None, limit: int = 10) -> list:
        """
        List stored voice inputs from S3

        Args:
            farmer_phone: Filter by farmer phone (optional)
            limit: Maximum number of results

        Returns:
            List of stored voice input metadata
        """
        if not self.s3_client:
            # Return mock data for development
            return [
                {
                    's3_key': 'voice-inputs/20260304_120000_farmer_9999_hi-IN.wav',
                    'size': 1024,
                    'last_modified': '2026-03-04T12:00:00Z',
                    'farmer_info': 'farmer_9999',
                    'mock': True
                }
            ]

        try:
            # List objects in the voice-inputs folder
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix='voice-inputs/',
                MaxKeys=limit
            )

            voice_inputs = []
            for obj in response.get('Contents', []):
                s3_key = obj['Key']

                # Filter by farmer phone if specified
                if farmer_phone and farmer_phone[-4:] not in s3_key:
                    continue

                # Get object metadata
                try:
                    metadata_response = self.s3_client.head_object(
                        Bucket=self.s3_bucket,
                        Key=s3_key
                    )
                    metadata = metadata_response.get('Metadata', {})
                except:
                    metadata = {}

                voice_inputs.append({
                    's3_key': s3_key,
                    's3_uri': f"s3://{self.s3_bucket}/{s3_key}",
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'farmer_name': metadata.get('farmer-name', 'unknown'),
                    'farmer_phone': metadata.get('farmer-phone', 'unknown'),
                    'language_code': metadata.get('language-code', 'unknown'),
                    'upload_timestamp': metadata.get('upload-timestamp', 'unknown'),
                    'mock': False
                })

            return voice_inputs

        except Exception as e:
            raise Exception(f"Failed to list voice inputs from S3: {str(e)}")
    
    def _get_mock_audio(self) -> bytes:
        """Return mock audio bytes for development"""
        # Return a minimal MP3 header (silent audio)
        return b'\xff\xfb\x90\x00' + b'\x00' * 100
    
    def generate_missing_field_prompt(self, missing_fields: list, language_code: str = "hi-IN") -> str:
        """
        Generate appropriate prompt text for missing fields
        
        Args:
            missing_fields: List of missing field names
            language_code: Language for the prompt
            
        Returns:
            Prompt text in the specified language
        """
        if language_code.startswith("hi"):
            # Hindi prompts
            field_prompts = {
                "crop": "कृपया बताएं कि आप कौन सी फसल स्टोर करना चाहते हैं?",
                "quantity": "कृपया बताएं कि आप कितनी मात्रा में फसल स्टोर करना चाहते हैं?",
                "time": "कृपया बताएं कि आप कब से स्टोरेज शुरू करना चाहते हैं?",
                "location": "कृपया अपना स्थान बताएं।"
            }
            
            if len(missing_fields) == 1:
                return field_prompts.get(missing_fields[0], "कृपया अधिक जानकारी दें।")
            else:
                return f"कृपया निम्नलिखित जानकारी दें: {', '.join(missing_fields)}"
        
        else:
            # English prompts
            field_prompts = {
                "crop": "Please tell me which crop you want to store?",
                "quantity": "Please tell me how much quantity you want to store?",
                "time": "Please tell me when you want to start storage?",
                "location": "Please provide your location."
            }
            
            if len(missing_fields) == 1:
                return field_prompts.get(missing_fields[0], "Please provide more information.")
            else:
                return f"Please provide the following information: {', '.join(missing_fields)}"

    def store_voice_input_s3(self, audio_bytes: bytes, farmer_info: dict, language_code: str = "hi-IN") -> dict:
        """
        Store voice input in S3 bucket with metadata
        
        Args:
            audio_bytes: Audio data as bytes
            farmer_info: Dictionary with farmer details (name, phone, etc.)
            language_code: Language code
            
        Returns:
            Dictionary with S3 storage information
        """
        try:
            # Generate unique filename with timestamp and farmer info
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            farmer_name = farmer_info.get('name', 'unknown').replace(' ', '_')
            farmer_phone = farmer_info.get('phone', 'unknown')
            
            # Create structured S3 key
            s3_key = f"voice-inputs/{timestamp}_{farmer_name}_{farmer_phone[-4:]}_{language_code}.wav"
            
            if not self.s3_client:
                # Mock storage for development
                return {
                    'stored': True,
                    's3_key': s3_key,
                    's3_uri': f"s3://{self.s3_bucket}/{s3_key}",
                    'bucket': self.s3_bucket,
                    'size_bytes': len(audio_bytes),
                    'timestamp': timestamp,
                    'mock': True
                }
            
            # Save bytes to temporary file first
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Upload to S3 with metadata
                self.s3_client.upload_file(
                    temp_file_path,
                    self.s3_bucket,
                    s3_key,
                    ExtraArgs={
                        'Metadata': {
                            'farmer-name': farmer_info.get('name', 'unknown'),
                            'farmer-phone': farmer_info.get('phone', 'unknown'),
                            'language-code': language_code,
                            'upload-timestamp': timestamp,
                            'content-type': 'audio/wav'
                        },
                        'ContentType': 'audio/wav'
                    }
                )
                
                return {
                    'stored': True,
                    's3_key': s3_key,
                    's3_uri': f"s3://{self.s3_bucket}/{s3_key}",
                    'bucket': self.s3_bucket,
                    'size_bytes': len(audio_bytes),
                    'timestamp': timestamp,
                    'mock': False
                }
                
            finally:
                # Cleanup temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            raise Exception(f"Failed to store voice input in S3: {str(e)}")
    
    def list_stored_voice_inputs(self, farmer_phone: str = None, limit: int = 10) -> list:
        """
        List stored voice inputs from S3
        
        Args:
            farmer_phone: Filter by farmer phone (optional)
            limit: Maximum number of results
            
        Returns:
            List of stored voice input metadata
        """
        if not self.s3_client:
            # Return mock data for development
            return [
                {
                    's3_key': 'voice-inputs/20260304_120000_farmer_9999_hi-IN.wav',
                    'size': 1024,
                    'last_modified': '2026-03-04T12:00:00Z',
                    'farmer_info': 'farmer_9999',
                    'mock': True
                }
            ]
        
        try:
            # List objects in the voice-inputs folder
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix='voice-inputs/',
                MaxKeys=limit
            )
            
            voice_inputs = []
            for obj in response.get('Contents', []):
                s3_key = obj['Key']
                
                # Filter by farmer phone if specified
                if farmer_phone and farmer_phone[-4:] not in s3_key:
                    continue
                
                # Get object metadata
                try:
                    metadata_response = self.s3_client.head_object(
                        Bucket=self.s3_bucket,
                        Key=s3_key
                    )
                    metadata = metadata_response.get('Metadata', {})
                except:
                    metadata = {}
                
                voice_inputs.append({
                    's3_key': s3_key,
                    's3_uri': f"s3://{self.s3_bucket}/{s3_key}",
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'farmer_name': metadata.get('farmer-name', 'unknown'),
                    'farmer_phone': metadata.get('farmer-phone', 'unknown'),
                    'language_code': metadata.get('language-code', 'unknown'),
                    'upload_timestamp': metadata.get('upload-timestamp', 'unknown'),
                    'mock': False
                })
            
            return voice_inputs
            
        except Exception as e:
            raise Exception(f"Failed to list voice inputs from S3: {str(e)}")


# Global voice service instance
voice_service = VoiceService()