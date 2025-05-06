# routes/visualize.py
from flask import Blueprint, request, jsonify
from services.gemini_viz import design_spec, generate_code

viz_bp = Blueprint("visualize", __name__)

@viz_bp.route("/", methods=["POST"])
def visualize():
    payload = request.get_json(force=True)
    question = payload.get("nl") or payload.get("sql")
    data   = payload.get("data")  # list of dicts

    if not question or not data:
        return jsonify({"error":"Provide 'nl' (or 'sql') and 'data'"}), 400

    # Prepare a small sample to give context to the LLM
    df_sample = {
        "columns": list(data[0].keys()),
        "example_row": data[0]
    }

    
    spec = design_spec(question, df_sample)
    code = generate_code(spec)
    return jsonify({"spec": spec, "code": code}), 200
    
