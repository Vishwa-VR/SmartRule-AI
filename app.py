"""
app.py
------
Flask entry point for the SmartRuleAI web edition.

Run locally:
    python app.py

Deploy on Railway:
    gunicorn app:app --bind 0.0.0.0:$PORT   (see Procfile)
"""

import os

from flask import Flask, jsonify, request, render_template

from database import Database
from knowledge_base import KnowledgeBase
from rules import RuleManager
from chatbot import Chatbot
from mood import time_greeting

app = Flask(__name__)

db = Database()
db.seed_sample_data()
kb = KnowledgeBase(db)
rule_manager = RuleManager(db)
chatbot = Chatbot(db)


# ----------------------------------------------------------------------
# Frontend
# ----------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


# ----------------------------------------------------------------------
# Greeting / mood
# ----------------------------------------------------------------------
@app.route("/api/greeting")
def api_greeting():
    text, emoji, part = time_greeting()
    stats = db.get_stats()
    return jsonify({
        "greeting": text,
        "emoji": emoji,
        "part_of_day": part,
        "stats": stats,
        "suggestions": chatbot.quick_questions(6),
    })


# ----------------------------------------------------------------------
# Chat
# ----------------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400
    try:
        result = chatbot.get_response(message)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.route("/api/suggestions")
def api_suggestions():
    n = request.args.get("n", default=6, type=int)
    return jsonify({"suggestions": chatbot.quick_questions(n)})


@app.route("/api/tip")
def api_tip():
    fact = chatbot.random_tip()
    if not fact:
        return jsonify({"tip": None})
    return jsonify({"tip": fact.to_dict()})


# ----------------------------------------------------------------------
# History
# ----------------------------------------------------------------------
@app.route("/api/history")
def api_history():
    q = request.args.get("q")
    rows = chatbot.search_history(q) if q else chatbot.get_history()
    return jsonify({"history": [dict(row) for row in rows]})


@app.route("/api/history", methods=["DELETE"])
def api_history_clear():
    chatbot.clear_history()
    return jsonify({"cleared": True})


# ----------------------------------------------------------------------
# Knowledge base (facts)
# ----------------------------------------------------------------------
@app.route("/api/facts", methods=["GET"])
def api_facts_list():
    return jsonify({"facts": [f.to_dict() for f in kb.get_all_facts()]})


@app.route("/api/facts", methods=["POST"])
def api_facts_create():
    data = request.get_json(silent=True) or {}
    try:
        fact_id = kb.add_fact(
            data.get("concept", ""), data.get("statement", ""),
            data.get("keywords", ""), is_base=0,
            category=data.get("category", "custom"), polarity=data.get("polarity", "neutral"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": fact_id})


@app.route("/api/facts/<int:fact_id>", methods=["PUT"])
def api_facts_update(fact_id):
    data = request.get_json(silent=True) or {}
    try:
        kb.update_fact(
            fact_id, data.get("concept", ""), data.get("statement", ""),
            data.get("keywords", ""), category=data.get("category", "custom"),
            polarity=data.get("polarity", "neutral"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"updated": True})


@app.route("/api/facts/<int:fact_id>", methods=["DELETE"])
def api_facts_delete(fact_id):
    kb.delete_fact(fact_id)
    return jsonify({"deleted": True})


# ----------------------------------------------------------------------
# Rule base
# ----------------------------------------------------------------------
@app.route("/api/rules", methods=["GET"])
def api_rules_list():
    return jsonify({"rules": [r.to_dict() for r in rule_manager.get_all_rules()]})


@app.route("/api/rules", methods=["POST"])
def api_rules_create():
    data = request.get_json(silent=True) or {}
    try:
        rule_id = rule_manager.add_rule(
            data.get("name", ""), data.get("if_concept", ""),
            data.get("then_concept", ""), data.get("description", ""),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": rule_id})


@app.route("/api/rules/<int:rule_id>", methods=["DELETE"])
def api_rules_delete(rule_id):
    rule_manager.delete_rule(rule_id)
    return jsonify({"deleted": True})


# ----------------------------------------------------------------------
# Stats
# ----------------------------------------------------------------------
@app.route("/api/stats")
def api_stats():
    return jsonify(db.get_stats())


# ----------------------------------------------------------------------
# Security checklist tool
# ----------------------------------------------------------------------
@app.route("/api/checklist", methods=["POST"])
def api_checklist():
    data = request.get_json(silent=True) or {}
    answers = data.get("answers") or {}
    try:
        result = chatbot.run_checklist(answers)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
