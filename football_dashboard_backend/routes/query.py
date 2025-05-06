from flask import Blueprint, request, jsonify
from services.db import fetch_df
from services.gemini_sql import question_to_sql
from utils.validation import is_safe_sql

query_bp = Blueprint("query", __name__)

@query_bp.route("/", methods=["POST"])
def run_query():
    data = request.get_json(force=True)
    nl  = data.get("nl")
    raw = data.get("sql")
    sql = None

    try:
        if nl:
            sql = question_to_sql(nl)
        elif raw:
            if not is_safe_sql(raw):
                return jsonify({"error": "Raw SQL failed safety check"}), 400
            sql = raw.strip()
        else:
            return jsonify({"error": "Provide 'nl' or 'sql'"}), 400

        df = fetch_df(sql)
        return {"sql": sql, "rows": len(df),
                "data": df.to_dict("records")}, 200
    except Exception as e:
        return jsonify({"error": str(e), "sql": sql}), 400
