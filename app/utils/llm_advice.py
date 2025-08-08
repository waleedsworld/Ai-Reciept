import openai
import os
import json
from dotenv import load_dotenv
from app.services.reports import instance_report

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Pass instance ID and optional focus to get suggestions
def llm_advice(id: str, focus: str = None):
    report_data = instance_report(id)
    report_json = json.dumps(report_data, indent=2)

    # Construct the focus line if focus is provided
    focus_line = f"The user's focus is on '{focus}'. " if focus else ""

    prompt = f'''
You are a financial analyst AI. {focus_line}I am sharing a list of my receipts and spending data in JSON format below.

Your task is to analyze the user's spending patterns and generate helpful, personalized, and actionable saving suggestions based on the data and their focus area (if given).

Format:
Respond with only a JSON object like this:
{{
  "suggestions": "text summarizing key spending insights and specific saving strategies"
}}

Goals:
* Identify categories with high or unusual spending.
* Suggest areas to cut down or optimize.
* Recommend behavior or planning changes to improve savings.

Input JSON:
{report_json}

Return only a valid JSON object with a "suggestions" field. No commentary, no explanation, no code blocks.
'''

    try:
        response = openai.chat.completions.create(
            model='gpt-4o',
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ]
        )

        response_text = response.choices[0].message.content.strip()

        # Parse and return just the JSON
        parsed = json.loads(response_text)
        return parsed

    except json.JSONDecodeError:
        print("Failed to parse JSON from model response")
        return {"error": "Invalid response format"}
    except Exception as e:
        print(f"OpenAI error: {str(e)}")
        return {"error": "LLM request failed"}
