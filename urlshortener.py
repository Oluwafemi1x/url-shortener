import random
import string
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS to allow requests from your Angular frontend

# In-memory store for URLs (use a database like SQLite or Redis for production)
url_store = {}

# Generate a short URL key
def generate_short_key(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Endpoint to shorten a URL
@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    original_url = request.json.get('url')
    
    if not original_url:
        return jsonify({"error": "URL is required"}), 400
    
    # Generate a unique short key
    short_key = generate_short_key()
    while short_key in url_store:
        short_key = generate_short_key()
    
    # Store the mapping
    url_store[short_key] = original_url
    
    return jsonify({
        "short_url": f"http://localhost:5000/{short_key}",
        "original_url": original_url
    }), 201

# Endpoint to redirect a short URL to the original URL
@app.route('/<short_key>', methods=['GET'])
def redirect_to_original(short_key):
    original_url = url_store.get(short_key)
    
    if original_url:
        return redirect(original_url)
    else:
        return jsonify({"error": "Short URL not found"}), 404

# Run the Flask application
if __name__ == '__main__': 
    app.run(debug=True)