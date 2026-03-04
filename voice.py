#!/usr/bin/env python3
"""
FarmFreeze Voice Input - Real-time Recording
Record voice from terminal and process cold storage booking
"""
import os
import sys
import json
import tempfile
import time

# Try to import audio recording
try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

# Try to import requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

class VoiceBooking:
    def __init__(self):
        self.api_url = "http://localhost:8000/api/voice/enhanced-book"
        self.farmer_name = "Voice User"
        self.farmer_phone = "+919999999999"
        self.language = "hi-IN"
        self.sample_rate = 16000
    
    def record_voice_live(self, duration=10):
        """Record voice in real-time from terminal"""
        if not AUDIO_AVAILABLE:
            print("❌ Audio recording not available")
            print("Install: pip install sounddevice soundfile")
            return None
        
        print(f"🎤 Recording for {duration} seconds...")
        print("🔴 SPEAK NOW!")
        
        try:
            # Record audio
            audio_data = sd.rec(
                int(duration * self.sample_rate), 
                samplerate=self.sample_rate, 
                channels=1, 
                dtype='float64'
            )
            
            # Show countdown
            for i in range(duration, 0, -1):
                print(f"⏱️  {i} seconds remaining...")
                sd.wait(1000)  # Wait 1 second
            
            sd.wait()  # Wait until recording is finished
            print("⏹️  Recording complete!")
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            sf.write(temp_file.name, audio_data, self.sample_rate)
            
            return temp_file.name
            
        except Exception as e:
            print(f"❌ Recording failed: {e}")
            return None
    
    def process_voice(self, audio_file=None):
        """Process voice input for booking"""
        if not REQUESTS_AVAILABLE:
            print("❌ Requests library not available")
            print("Install: pip install requests")
            return
            
        if not audio_file:
            # Record new audio
            audio_file = self.record_voice_live()
            if not audio_file:
                return
        
        print("📤 Processing voice...")
        
        try:
            with open(audio_file, 'rb') as f:
                files = {'audio_file': f}
                data = {
                    'farmer_name': self.farmer_name,
                    'farmer_phone': self.farmer_phone,
                    'language_code': self.language,
                    'store_in_s3': 'true'
                }
                
                response = requests.post(self.api_url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                self.show_result(result)
            else:
                print(f"❌ Server error: {response.status_code}")
                print("Make sure server is running: .\\start.bat")
                
        except requests.exceptions.ConnectionError:
            print("❌ Server not running!")
            print("Start server: .\\start.bat")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            # Cleanup temp file
            if audio_file and os.path.exists(audio_file):
                try:
                    os.unlink(audio_file)
                except:
                    pass
    
    def show_result(self, result):
        """Show booking result"""
        print("\n" + "="*50)
        print("📊 VOICE BOOKING RESULT")
        print("="*50)
        
        # Transcription
        if result.get('transcription'):
            t = result['transcription']
            print(f"🎯 You said: '{t['transcript']}'")
            print(f"   Confidence: {t['confidence']*100:.1f}%")
        
        # S3 Storage
        if result.get('voice_storage'):
            s = result['voice_storage']
            print(f"📁 Stored in S3: {s['s3_key']}")
        
        # AI Understanding
        if result.get('intent'):
            intent = result['intent']
            crop = intent.get('crop', 'unknown')
            qty = intent.get('quantity', 0)
            unit = intent.get('unit', 'kg')
            print(f"🧠 AI understood: {crop} - {qty} {unit}")
        
        # Missing Information
        if result.get('requires_more_info'):
            missing = result.get('missing_fields', [])
            print(f"⚠️  Missing: {', '.join(missing)}")
            
            if result.get('recommendation'):
                rec = result['recommendation']['recommendation_text']
                print(f"💡 Please provide: {rec}")
                print("🔄 Try recording again with complete information")
        
        # Successful Booking
        elif result.get('success') and result.get('booking'):
            b = result['booking']
            print(f"✅ BOOKING SUCCESSFUL!")
            print(f"   📋 Reference: {b['booking_reference']}")
            print(f"   🏪 Storage: {b['cold_storage_name']}")
            print(f"   📦 Quantity: {b['quantity_kg']} kg")
            print(f"   📅 Date: {b['booking_date']}")
            print(f"   💰 Cost: ₹{b['total_cost']}")
        
        # Failed Booking
        else:
            print(f"❌ Booking failed: {result.get('message', 'Unknown error')}")
        
        print("="*50)
    
    def interactive_mode(self):
        """Interactive voice recording mode"""
        while True:
            print(f"\n🎤 VOICE BOOKING OPTIONS:")
            print("1. Record voice now (10 seconds)")
            print("2. Record voice now (5 seconds)")
            print("3. Test audio file")
            print("4. Change settings")
            print("5. Exit")
            
            choice = input("Select (1-5): ").strip()
            
            if choice == '1':
                self.process_voice()
            elif choice == '2':
                audio_file = self.record_voice_live(5)
                if audio_file:
                    self.process_voice(audio_file)
            elif choice == '3':
                audio_file = input("Audio file path: ").strip().strip('"')
                if audio_file and os.path.exists(audio_file):
                    self.process_voice(audio_file)
                else:
                    print("❌ File not found")
            elif choice == '4':
                self.settings_menu()
            elif choice == '5':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice")
    
    def settings_menu(self):
        """Settings menu"""
        print(f"\n⚙️  CURRENT SETTINGS:")
        print(f"   Name: {self.farmer_name}")
        print(f"   Phone: {self.farmer_phone}")
        print(f"   Language: {self.language}")
        print("\n1. Change name")
        print("2. Change phone")
        print("3. Change language")
        print("4. Back")
        
        choice = input("Select (1-4): ").strip()
        
        if choice == '1':
            name = input("Enter name: ").strip()
            if name:
                self.farmer_name = name
                print(f"✅ Name updated: {self.farmer_name}")
        elif choice == '2':
            phone = input("Enter phone: ").strip()
            if phone:
                self.farmer_phone = phone
                print(f"✅ Phone updated: {self.farmer_phone}")
        elif choice == '3':
            print("Languages: 1=Hindi 2=English(IN) 3=English(US)")
            lang_choice = input("Select (1-3): ").strip()
            lang_map = {'1': 'hi-IN', '2': 'en-IN', '3': 'en-US'}
            if lang_choice in lang_map:
                self.language = lang_map[lang_choice]
                print(f"✅ Language updated: {self.language}")
    
    def run(self):
        """Main function"""
        print("🎤 FarmFreeze Voice Booking")
        print("="*30)
        
        # Check if file provided as argument
        if len(sys.argv) > 1:
            audio_file = sys.argv[1]
            if os.path.exists(audio_file):
                print(f"📁 Testing file: {audio_file}")
                self.process_voice(audio_file)
            else:
                print(f"❌ File not found: {audio_file}")
        else:
            # Check if live recording is available
            if not AUDIO_AVAILABLE:
                print("❌ Live recording not available")
                print("📝 Please provide an audio file:")
                print("   python voice.py \"your_audio.wav\"")
                return
            
            # Show examples and start interactive mode
            print("📝 Example voice inputs:")
            print("   Hindi: 'मुझे 100 किलो टमाटर स्टोर करना है कल से'")
            print("   English: 'I need to store 50 kg potatoes from tomorrow'")
            print("   Incomplete: 'मुझे स्टोरेज चाहिए' (gets recommendations)")
            
            self.interactive_mode()

if __name__ == "__main__":
    booking = VoiceBooking()
    booking.run()