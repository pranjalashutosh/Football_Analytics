# routes/interactive.py
import os
import json
import hashlib
import traceback

from flask import Blueprint, request, jsonify, current_app
from services.gemini_unified import (
    get_data_and_chart_spec,
    generate_code,
    execute_plotly_code
)

interactive_bp = Blueprint("interactive", __name__)

# TTL for cache entries (seconds): 24 h
CACHE_TTL = int(os.getenv("CACHE_TTL_SEC", 86400))
# bump this whenever you update your prompts to invalidate old cache
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1")

@interactive_bp.route("/", methods=["POST"])
def interactive():
    # 1. Validate input
    print("🔥  /interactive/ hit with payload:", request.json)
    user_query = request.json.get("nl")
    if not user_query:
        return jsonify({"error": "Missing 'nl' in request body"}), 400
    
        # 1) Build a cache key: version + SHA‑256 of the query
    hash_input = f"{PROMPT_VERSION}:{user_query}".encode("utf-8")
    key = "resp:" + hashlib.sha256(hash_input).hexdigest()

    # 2) Try Redis hit
    cached = current_app.redis_client.get(key)
    if cached:
        # saved as JSON string
        return jsonify(json.loads(cached)), 200

    try:
        # 2. Fetch data + Vega-Lite spec from Gemini
        data, spec = get_data_and_chart_spec(user_query)

        # 3. Generate Plotly Express Python code
        plotly_code = generate_code(spec)

        # 4. Execute that code on the server to produce Plotly JSON
        plotly_json = execute_plotly_code(data, plotly_code)

        # 5. Return everything to the frontend
        resp = {
        "spec": spec,
        "code": plotly_code,
        "plotly_json": plotly_json
        }

    # 4) Store in Redis
        current_app.redis_client.set(key, json.dumps(resp), ex=CACHE_TTL)

        return jsonify(resp), 200

    except Exception as e:
        tb = traceback.format_exc()
        print(tb)  # immediate stdout
        return jsonify({"error": tb}), 500
