from flask import request, jsonify
import openai
import os
from dotenv import load_dotenv
from app.services.reports import instance_report
import json

# Load env vars
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# In-memory memory store
chat_memory = {}
MEMORY_WINDOW = 5

# Helper to format initial system message
def build_system_message(report_data):
    return {
        "role": "system",
        "content": (
            "You are a helpful financial assistant. The user has provided the following instance data:\n\n"
            f"{json.dumps(report_data, indent=2)}\n\n"
            "Use this data to help answer follow-up questions about their spending, categories, or habits."
        )
    }

# Helper to format user messages from chat history
def build_message_log(instance_id, user_message):
    history = chat_memory.get(instance_id, [])
    return history[-MEMORY_WINDOW:] + [{"role": "user", "content": user_message}]

# Endpoint
def handle_chat(id,message):

    # Get instance report for context
    try:
        report_data = instance_report(id)
    except Exception as e:
        return jsonify({"error": "Failed to load instance report", "details": str(e)}), 500

    # Build conversation log
    messages = [build_system_message(report_data)] + build_message_log(id, message)

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        assistant_reply = response.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({"error": "LLM request failed", "details": str(e)}), 500

    # Update memory
    history = chat_memory.get(id, [])
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": assistant_reply})
    chat_memory[id] = history[-MEMORY_WINDOW:]  # Limit to last 5 messages

    return {"response": assistant_reply}
