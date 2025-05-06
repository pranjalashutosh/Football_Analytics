from flask import Flask
import os
from flask_cors import CORS
from routes.interactive import interactive_bp
import redis
#from routes.query import query_bp
#from routes.visualize import viz_bp
#from flask import Blueprint, request, jsonify
#from services.db import fetch_df
#from services.gemini_sql import question_to_sql
#from routes.visualize import viz_bp


app = Flask(__name__)
CORS(app)

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

app.redis_client = redis_client


#app.register_blueprint(query_bp, url_prefix='/query')

#app.register_blueprint(viz_bp, url_prefix="/visualize")

app.register_blueprint(interactive_bp, url_prefix="/interactive")

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5000)
