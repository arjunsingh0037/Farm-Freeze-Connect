// Configuration
const API_BASE_URL = (typeof window !== 'undefined' && window.location ? window.location.origin : '') + '/api/v1';

// Check if page loaded successfully
console.log('✅ FarmFreeze Connect JavaScript loaded successfully');

// State
let mediaRecorder = null;
let audioChunks = [];
let recordingTimer = null;
let recordingSeconds = 0;

// DOM Elements
const recordBtn = document.getElementById('recordBtn');
const recordingStatus = document.getElementById('recordingStatus');
const recordingTimerEl = document.getElementById('recordingTimer');
const audioFileInput = document.getElementById('audioFile');
const textQueryForm = document.getElementById('textQueryForm');
const detectLocationBtn = document.getElementById('detectLocation');
const loadBookingsBtn = document.getElementById('loadBookings');
const resultsSection = document.getElementById('resultsSection');
const loadingOverlay = document.getElementById('loadingOverlay');

// Utility Functions
function showLoading() {
    loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    loadingOverlay.classList.add('hidden');
}

function showError(message) {
    alert('❌ Error: ' + message);
}

function showSuccess(message) {
    alert('✅ ' + message);
}

// Location Detection
detectLocationBtn.addEventListener('click', async () => {
    if (!navigator.geolocation) {
        showError('Geolocation is not supported by your browser');
        return;
    }

    showLoading();
    navigator.geolocation.getCurrentPosition(
        (position) => {
            document.getElementById('latitude').value = position.coords.latitude.toFixed(4);
            document.getElementById('longitude').value = position.coords.longitude.toFixed(4);
            hideLoading();
            showSuccess('Location detected!');
        },
        (error) => {
            hideLoading();
            showError('Could not detect location: ' + error.message);
        }
    );
});

// Voice Recording
recordBtn.addEventListener('click', async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showError('Audio recording is not supported by your browser');
        return;
    }

    if (mediaRecorder && mediaRecorder.state === 'recording') {
        // Stop recording
        mediaRecorder.stop();
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        recordingSeconds = 0;

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            clearInterval(recordingTimer);
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            await processVoiceBooking(audioBlob);
            
            // Reset UI
            recordBtn.innerHTML = '<span class="btn-icon">🎙️</span> Start Recording';
            recordingStatus.classList.add('hidden');
            
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        
        // Update UI
        recordBtn.innerHTML = '<span class="btn-icon">⏹️</span> Stop Recording';
        recordingStatus.classList.remove('hidden');
        
        // Start timer
        recordingTimer = setInterval(() => {
            recordingSeconds++;
            recordingTimerEl.textContent = recordingSeconds + 's';
        }, 1000);

    } catch (error) {
        showError('Could not access microphone: ' + error.message);
    }
});

// Audio File Upload
audioFileInput.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    await processVoiceBooking(file);
    audioFileInput.value = ''; // Reset input
});

// Process Voice Booking
async function processVoiceBooking(audioBlob) {
    showLoading();

    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'recording.wav');
    formData.append('farmer_name', 'Web User');
    formData.append('farmer_phone', '+919999999999');
    formData.append('farmer_lat', document.getElementById('latitude').value);
    formData.append('farmer_lng', document.getElementById('longitude').value);
    formData.append('language_code', 'hi-IN');

    try {
        const response = await fetch(`${API_BASE_URL}/voice/book`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Voice booking failed');
        }

        const data = await response.json();
        displayResults(data);
        
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

// Text Query
textQueryForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const query = document.getElementById('queryText').value.trim();
    const lat = parseFloat(document.getElementById('latitude').value);
    const lng = parseFloat(document.getElementById('longitude').value);

    if (!query) {
        showError('Please enter your storage requirements');
        return;
    }

    if (isNaN(lat) || isNaN(lng)) {
        showError('Please provide valid location coordinates');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE_URL}/ai/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                farmer_query: query,
                farmer_lat: lat,
                farmer_lng: lng,
                farmer_name: 'Web User',
                farmer_phone: '+919999999999'
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Query failed');
        }

        const data = await response.json();
        displayResults(data);

    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
});

// Display Results
function displayResults(data) {
    resultsSection.classList.remove('hidden');
    
    // Display Intent
    const intentDisplay = document.getElementById('intentDisplay');
    const intent = data.intent || {};
    
    intentDisplay.innerHTML = `
        <h3 style="margin-bottom: 16px;">🎯 Understood Requirements</h3>
        ${intent.crop ? `<div class="intent-item"><span class="intent-label">Crop:</span><span class="intent-value">${intent.crop}</span></div>` : ''}
        ${intent.quantity ? `<div class="intent-item"><span class="intent-label">Quantity:</span><span class="intent-value">${intent.quantity} ${intent.unit || 'kg'}</span></div>` : ''}
        ${intent.duration_days ? `<div class="intent-item"><span class="intent-label">Duration:</span><span class="intent-value">${intent.duration_days} days</span></div>` : ''}
        ${intent.time ? `<div class="intent-item"><span class="intent-label">Start Time:</span><span class="intent-value">${intent.time}</span></div>` : ''}
        ${intent.urgency ? `<div class="intent-item"><span class="intent-label">Urgency:</span><span class="intent-value">${intent.urgency}</span></div>` : ''}
        ${intent.storage_type ? `<div class="intent-item"><span class="intent-label">Storage Type:</span><span class="intent-value">${intent.storage_type}</span></div>` : ''}
        ${intent.confidence ? `<div class="intent-item"><span class="intent-label">Confidence:</span><span class="intent-value">${(intent.confidence * 100).toFixed(1)}%</span></div>` : ''}
    `;

    // Display Storage Results
    const storageResults = document.getElementById('storageResults');
    const storages = data.available_storages || [];

    if (storages.length === 0) {
        storageResults.innerHTML = '<p class="text-center">No storage facilities found matching your requirements.</p>';
        return;
    }

    storageResults.innerHTML = storages.map(storage => `
        <div class="storage-card">
            <div class="storage-header">
                <div>
                    <div class="storage-name">${storage.storage_name}</div>
                    <div class="storage-address">📍 ${storage.address}</div>
                </div>
                <div class="storage-distance">${storage.distance_km} km</div>
            </div>
            
            <div class="storage-details">
                <div class="detail-item">
                    <span class="detail-label">Price/kg/day</span>
                    <span class="detail-value">₹${storage.price_per_kg_per_day}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Total Cost</span>
                    <span class="detail-value">₹${storage.total_cost.toFixed(2)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Available Capacity</span>
                    <span class="detail-value">${(storage.available_capacity_kg / 1000).toFixed(1)} tons</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Supported Crops</span>
                    <span class="detail-value">${storage.supported_crops}</span>
                </div>
            </div>
            
            <div class="storage-actions">
                <button class="btn btn-success" onclick="bookStorage(${storage.storage_id}, ${intent.quantity || 0}, '${intent.crop || ''}')">
                    <span class="btn-icon">✅</span>
                    Book Now
                </button>
            </div>
        </div>
    `).join('');

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Book Storage
async function bookStorage(storageId, quantity, crop) {
    const lat = parseFloat(document.getElementById('latitude').value);
    const lng = parseFloat(document.getElementById('longitude').value);

    if (!confirm('Confirm booking for this storage facility?')) {
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE_URL}/bookings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                farmer_name: 'Web User',
                farmer_phone: '+919999999999',
                cold_storage_id: storageId,
                quantity_kg: quantity,
                booking_date: new Date().toISOString().split('T')[0],
                duration_days: 7,
                crop_type: crop
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Booking failed');
        }

        const data = await response.json();
        showSuccess(`Booking confirmed! Reference: ${data.booking_reference}`);
        
        // Reload bookings
        loadBookings();

    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

// Load Bookings
loadBookingsBtn.addEventListener('click', loadBookings);

async function loadBookings() {
    showLoading();

    try {
        const response = await fetch(`${API_BASE_URL}/bookings`);

        if (!response.ok) {
            throw new Error('Failed to load bookings');
        }

        const bookings = await response.json();
        displayBookings(bookings);

    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

// Display Bookings
function displayBookings(bookings) {
    const bookingsList = document.getElementById('bookingsList');

    if (!bookings || bookings.length === 0) {
        bookingsList.innerHTML = '<p class="text-center mt-20">No bookings found.</p>';
        return;
    }

    bookingsList.innerHTML = bookings.map(booking => `
        <div class="booking-card">
            <div class="booking-header">
                <div class="booking-reference">📋 ${booking.booking_reference}</div>
                <div class="booking-status status-${booking.status.toLowerCase()}">
                    ${booking.status}
                </div>
            </div>
            <div class="booking-details">
                <div class="booking-detail">
                    <strong>Storage:</strong> ${booking.cold_storage_name}
                </div>
                <div class="booking-detail">
                    <strong>Crop:</strong> ${booking.crop_type || 'N/A'}
                </div>
                <div class="booking-detail">
                    <strong>Quantity:</strong> ${booking.quantity_kg} kg
                </div>
                <div class="booking-detail">
                    <strong>Date:</strong> ${booking.booking_date}
                </div>
                <div class="booking-detail">
                    <strong>Duration:</strong> ${booking.duration_days} days
                </div>
                <div class="booking-detail">
                    <strong>Total Cost:</strong> ₹${booking.total_cost.toFixed(2)}
                </div>
            </div>
        </div>
    `).join('');
}

// Make bookStorage available globally
window.bookStorage = bookStorage;

// Initialize and verify page loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 FarmFreeze Connect initialized');
    console.log('📡 API Base URL:', API_BASE_URL);
    
    // Verify all required elements exist
    const requiredElements = [
        'recordBtn', 'recordingStatus', 'recordingTimerEl', 
        'audioFileInput', 'textQueryForm', 'detectLocationBtn',
        'loadBookingsBtn', 'resultsSection', 'loadingOverlay'
    ];
    
    let allElementsFound = true;
    requiredElements.forEach(id => {
        const element = document.getElementById(id);
        if (!element) {
            console.error(`❌ Required element not found: ${id}`);
            allElementsFound = false;
        }
    });
    
    if (allElementsFound) {
        console.log('✅ All UI elements loaded successfully');
    } else {
        console.error('⚠️ Some UI elements are missing');
    }
    
    // Mark page as loaded
    document.body.classList.add('page-loaded');
});

// Fallback: ensure loader is hidden
window.addEventListener('load', function() {
    setTimeout(function() {
        document.body.classList.add('page-loaded');
        console.log('✅ Page fully loaded');
    }, 500);
});
