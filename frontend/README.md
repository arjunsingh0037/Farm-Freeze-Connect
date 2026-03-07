# FarmFreeze Connect - Frontend

Simple, clean frontend for the FarmFreeze cold storage booking system.

## Features

- 🎤 **Voice Booking**: Record audio directly in browser or upload audio files
- 💬 **Text Query**: Type storage requirements in natural language
- 📍 **Location Detection**: Auto-detect user location or enter manually
- 📊 **Storage Search**: View available cold storage facilities with pricing
- ✅ **Quick Booking**: Book storage with one click
- 📋 **Booking Management**: View all your bookings

## Setup

### 1. Start the Backend Server

Make sure the backend is running on `http://localhost:8001`:

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8001
```

Or use the start script:

```bash
.\start.bat
```

### 2. Serve the Frontend

You can use any static file server. Here are a few options:

**Option A: Python HTTP Server**
```bash
cd frontend
python -m http.server 3000
```

**Option B: Node.js http-server**
```bash
cd frontend
npx http-server -p 3000
```

**Option C: VS Code Live Server**
- Install "Live Server" extension
- Right-click `index.html` → "Open with Live Server"

### 3. Open in Browser

Navigate to: `http://localhost:3000`

## Usage

### Voice Booking

1. Click "Start Recording" button
2. Speak your requirements (e.g., "I need to store 100 kg tomatoes from tomorrow")
3. Click "Stop Recording"
4. System will transcribe, understand intent, and show available storage options
5. Click "Book Now" on your preferred storage

### Text Query

1. Type your requirements in the text area
2. Ensure location is set (or click "Detect Location")
3. Click "Find Storage"
4. Review results and book

### View Bookings

1. Click "Load Bookings" button
2. View all your booking history with details

## API Endpoints Used

- `POST /api/v1/voice/enhanced-book` - Voice booking with transcription
- `POST /api/v1/ai/query` - Text query processing
- `POST /api/v1/bookings` - Create booking
- `GET /api/v1/bookings` - List all bookings

## Browser Requirements

- Modern browser with:
  - MediaRecorder API support (for voice recording)
  - Geolocation API support (for location detection)
  - Fetch API support

Tested on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Configuration

To change the API URL, edit `app.js`:

```javascript
const API_BASE_URL = 'http://localhost:8001/api/v1';
```

## Troubleshooting

**Voice recording not working:**
- Ensure browser has microphone permissions
- Use HTTPS or localhost (required for getUserMedia)

**Location detection not working:**
- Grant location permissions in browser
- Manually enter coordinates if needed

**API errors:**
- Ensure backend server is running on port 8001
- Check browser console for detailed error messages
- Verify CORS is enabled in backend

## Tech Stack

- Pure HTML5, CSS3, JavaScript (no frameworks)
- Responsive design
- Modern UI with gradient backgrounds
- Clean, minimal code

## File Structure

```
frontend/
├── index.html      # Main HTML structure
├── styles.css      # All styling
├── app.js          # Application logic
└── README.md       # This file
```
