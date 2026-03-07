#!/usr/bin/env python3
"""
Simple HTTP server with clean URL routing for FarmFreeze
Serves index.html for / and bookings.html for /bookings
"""
import http.server
import socketserver
import os
from urllib.parse import unquote

PORT = 3000

class FarmFreezeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Decode URL
        self.path = unquote(self.path)
        
        # Clean URL routing
        if self.path == '/' or self.path == '/index' or self.path == '/index.html':
            self.path = '/pages/index.html'
        elif self.path == '/bookings' or self.path == '/bookings.html':
            self.path = '/pages/bookings.html'
        
        # Serve the file
        return http.server.SimpleHTTPRequestHandler.do_GET(self)
    
    def end_headers(self):
        # Add CORS headers if needed
        self.send_header('Access-Control-Allow-Origin', '*')
        http.server.SimpleHTTPRequestHandler.end_headers(self)

# Change to the frontend directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Create and start server
Handler = FarmFreezeHandler
Handler.extensions_map.update({
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
})

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"========================================")
    print(f"  FarmFreeze Frontend Server")
    print(f"========================================")
    print(f"")
    print(f"  Server running at: http://localhost:{PORT}")
    print(f"  Voice Booking: http://localhost:{PORT}/")
    print(f"  My Bookings: http://localhost:{PORT}/bookings")
    print(f"")
    print(f"  Press Ctrl+C to stop")
    print(f"========================================")
    print(f"")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  Server stopped.")
        print("========================================")

