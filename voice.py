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
        self.farmer_lat = 28.6139  # Default Delhi
        self.farmer_lng = 77.2090
        self.language = "hi-IN"
        self.sample_rate = 16000
        self.auto_detect_location = True  # New setting
    
    def get_real_location(self):
        """Get real-time location based on IP address as a fallback for terminal apps"""
        try:
            print("📍 Detecting your real-time location...")
            response = requests.get('https://ipapi.co/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.farmer_lat = float(data.get('latitude', 28.6139))
                self.farmer_lng = float(data.get('longitude', 77.2090))
                city = data.get('city', 'Unknown')
                region = data.get('region', 'Unknown')
                print(f"✅ Location detected: {city}, {region} ({self.farmer_lat}, {self.farmer_lng})")
            else:
                print("⚠️  Could not detect real-time location, using default (Delhi).")
        except Exception as e:
            print(f"⚠️  Location detection failed: {e}. Using default (Delhi).")

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
    
    def process_voice(self, audio_file=None, confirmed=False):
        """Process voice input for booking"""
        if not REQUESTS_AVAILABLE:
            print("❌ Requests library not available")
            print("Install: pip install requests")
            return
            
        # Auto-detect location if enabled
        if self.auto_detect_location and not confirmed:
            self.get_real_location()
            
        if not audio_file:
            # Record new audio
            audio_file = self.record_voice_live()
            if not audio_file:
                return
        
        if not confirmed:
            print("📤 Processing voice and finding best cold storage...")
        else:
            print("📤 Finalizing your booking...")
        
        try:
            with open(audio_file, 'rb') as f:
                # Prepare multipart/form-data
                files = {'audio_file': (os.path.basename(audio_file), f, 'audio/wav')}
                data = {
                    'farmer_name': self.farmer_name,
                    'farmer_phone': self.farmer_phone,
                    'farmer_lat': str(self.farmer_lat),
                    'farmer_lng': str(self.farmer_lng),
                    'language_code': self.language,
                    'store_in_s3': 'true',
                    'confirmed': 'true' if confirmed else 'false'
                }
                
                response = requests.post(self.api_url, files=files, data=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                
                # If this was a preview and successful, ask for agreement
                if not confirmed and result.get('success') and result.get('booking') and not result.get('requires_more_info'):
                    self.show_result(result, preview=True)
                    agree = input("\n🤝 Do you AGREE to book this storage? (yes/no): ").strip().lower()
                    if agree in ['yes', 'y', 'haan']:
                        # Call again with confirmed=True
                        self.process_voice(audio_file, confirmed=True)
                    else:
                        print("❌ Booking cancelled by user.")
                else:
                    self.show_result(result, preview=confirmed)
            else:
                print(f"❌ Server error: {response.status_code}")
                print(f"Details: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            # Cleanup temp file
            if audio_file and os.path.exists(audio_file):
                try:
                    os.unlink(audio_file)
                except:
                    pass
    
    def show_result(self, result, preview=False):
        """Show booking result"""
        print("\n" + "="*50)
        if preview:
            print("📋 BOOKING PREVIEW (Confirmation Required)")
        else:
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
                rec = result['recommendation']
                print(f"💡 Please provide: {rec['recommendation_text']}")
                
                if rec.get('audio_available') and rec.get('audio_uri'):
                    print(f"🔊 Voice guidance available: {rec['audio_uri']}")
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
        print(f"   Location: {self.farmer_lat}, {self.farmer_lng}")
        print(f"   Auto-detect Location: {'Enabled' if self.auto_detect_location else 'Disabled'}")
        print("\n1. Change name")
        print("2. Change phone")
        print("3. Change language")
        print("4. Change location (lat, lng)")
        print("5. Refresh real-time location")
        print("6. Toggle auto-detect location")
        print("7. Back")
        
        choice = input("Select (1-7): ").strip()
        
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
        elif choice == '4':
            try:
                lat = float(input("Enter latitude: ").strip())
                lng = float(input("Enter longitude: ").strip())
                self.farmer_lat = lat
                self.farmer_lng = lng
                self.auto_detect_location = False  # Disable auto-detect if manual override
                print(f"✅ Location updated: {self.farmer_lat}, {self.farmer_lng}")
                print("⚠️  Auto-detect location disabled for manual override.")
            except ValueError:
                print("❌ Invalid input")
        elif choice == '5':
            self.get_real_location()
        elif choice == '6':
            self.auto_detect_location = not self.auto_detect_location
            print(f"✅ Auto-detect location: {'Enabled' if self.auto_detect_location else 'Disabled'}")
    
    def run(self):
        """Main function"""
        print("🎤 FarmFreeze Voice Booking")
        print("="*30)
        
        # Get real-time location on startup
        self.get_real_location()
        
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