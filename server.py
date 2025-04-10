#!/usr/bin/env python3
import os
import json
import flask
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Data directory
DATA_DIR = "data"

# Ensure data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

@app.route('/entries', methods=['GET'])
def get_entries():
    """Get all journal entries"""
    entries = {}
    if os.path.exists(DATA_DIR):
        for filename in os.listdir(DATA_DIR):
            if filename.endswith('.json'):
                date_str = filename[:-5]  # Remove .json extension
                file_path = os.path.join(DATA_DIR, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        entries[date_str] = json.load(f)
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
    return jsonify(entries)

@app.route('/entries/<date_str>', methods=['GET'])
def get_entry(date_str):
    """Get a specific journal entry"""
    file_path = os.path.join(DATA_DIR, f"{date_str}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                entry = json.load(f)
                return jsonify(entry)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Entry not found"}), 404

@app.route('/entries/<date_str>', methods=['POST'])
def save_entry(date_str):
    """Save a journal entry"""
    content = request.json
    file_path = os.path.join(DATA_DIR, f"{date_str}.json")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/entries/<date_str>', methods=['DELETE'])
def delete_entry(date_str):
    """Delete a journal entry"""
    file_path = os.path.join(DATA_DIR, f"{date_str}.json")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Entry not found"}), 404

if __name__ == '__main__':
    # Run the server on local network
    app.run(host='0.0.0.0', port=5000, debug=True) 