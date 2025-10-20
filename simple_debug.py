#!/usr/bin/env python3

import sys
import os
import logging
import traceback
from flask import Flask, jsonify

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a simple diagnostic Flask app
app = Flask(__name__)

@app.route('/')
def index():
    return """
    <html>
    <head>
        <title>Swiss Asset Manager - Diagnostics</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; padding: 20px; }
            h1 { color: #003366; }
            .success { color: green; font-weight: bold; }
            .button { background: #003366; color: white; padding: 10px 15px;
                     text-decoration: none; display: inline-block; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>Swiss Asset Manager - Diagnostic Page</h1>
        <p class="success">✅ Test server is running correctly!</p>
        <p>This confirms that a Flask server can run and respond on this port.</p>
        <p><a href="/test_app" class="button">Test Main App</a></p>
    </body>
    </html>
    """

@app.route('/test_app')
def test_app():
    """Test importing and checking the main app"""
    try:
        # Try to import the main app
        logger.info("Attempting to import main app...")
        sys.path.append(os.getcwd())
        
        # Import app and check its routes
        from app import app as main_app
        routes = [str(rule) for rule in main_app.url_map.iter_rules()]
        
        return jsonify({
            "success": True,
            "message": "Main app successfully imported",
            "routes": routes
        })
    except Exception as e:
        logger.error(f"Error testing main app: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })

if __name__ == "__main__":
    print("="*70)
    print("SWISS ASSET MANAGER - DIAGNOSTIC SERVER")
    print("="*70)
    print("🔍 Starting diagnostic server on port 8888...")
    print("📊 Visit http://localhost:8888 to view the diagnostic page")
    print("⚠️ Press Ctrl+C to stop")
    print("="*70)
    app.run(host="0.0.0.0", port=8888, debug=True)
