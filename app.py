import os
import ast
import re
from flask import Flask, request, jsonify
from adilet import parse_adilet
from dialog import parse_dialog
from npa import parse_npa
from budget import parse_budget
from openAI_search_texts import get_search_queries, process_search_queries
from opendata import parse_opendata
from supabase import create_client, Client
from dotenv import load_dotenv
from flask_cors import CORS
from data_formating import format_egov_output


load_dotenv()
app = Flask(__name__)
CORS(app)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


@app.route('/parse/egov/dialog', methods=['POST'])
def parse_dialog_endpoint():
    print(request.json)
    data = request.json
    if not data or not data.get("search_value", None):
        return jsonify({"error": "No data provided"}), 400
    begin_date = data.get("begin_date", None)
    end_date = data.get("end_date", None)
    max_pages = data.get("max_pages", 1)
    final_result = []
    for query in data["search_value"]:
        result = parse_dialog(query, begin_date, end_date, max_pages=max_pages)
        final_result = final_result + result
    return jsonify(final_result)


@app.route('/parse/egov/npa', methods=['POST'])
def parse_npa_endpoint():
    data = request.json
    if not data or not data.get("search_value", None):
        return jsonify({"error": "No data provided"}), 400
    begin_date = data.get("begin_date", None)
    end_date = data.get("end_date", None)
    final_result = []
    for query in data["search_value"]:
        result = parse_npa(query, begin_date, end_date, max_pages=data.get("max_pages", 1))
        final_result = final_result + result
    return jsonify(final_result)


@app.route('/parse/egov/budget', methods=['POST'])
def parse_budget_endpoint():
    data = request.json
    if not data or not data.get("search_value", None):
        return jsonify({"error": "No data provided"}), 400
    final_result = []
    for query in data["search_value"]:
        result = parse_budget(query, max_pages=data.get("max_pages", 1))
        final_result = final_result + result
    return jsonify(final_result)


@app.route('/parse/egov/opendata', methods=['POST'])
def parse_opendata_endpoint():
    data = request.json
    if not data or not data.get("search_value", None):
        return jsonify({"error": "No data provided"}), 400
    final_result = []
    for query in data["search_value"]:
        result = parse_opendata(query, max_pages=data.get("max_pages", 1))
        final_result = final_result + result
    return jsonify(final_result)


@app.route('/parse/adilet/npa', methods=['POST'])
def parse_adilet_endpoint():
    data = request.json
    if not data or not data.get("search_value", None):
        return jsonify({"error": "No data provided"}), 400
    final_result = []
    for query in data["search_value"]:
        result = parse_adilet(query, data.get("begin_date", None), max_pages=data.get("max_pages", 1))
        final_result = final_result + result
    return jsonify(final_result)


@app.route('/search', methods=['POST'])
def search_endpoint():
    data = request.json
    question = data.get("query", None)
    full = data.get("full", False)

    begin_date = "01.05.2021"

    if len(question) > 10:
        max_pages = 1 if full else 5
        data = get_search_queries(question)
    else:
        return jsonify({"error": "Too short request"}), 400

    print(data)

    try:
        for source in data.get("research", []):
            tool = source.get("tool", None)
            if tool is None:
                continue

            print(tool)

            if tool == 'Egov':
                for param in source.get("params", []):
                    data_type = param.get("type", None)

                    if data_type == 'Dialog':
                        result = []
                        for query in param.get("keywords", []):
                            parsing_result = parse_dialog(query, begin_date, max_pages=max_pages)
                            result.append(parsing_result)

                        format_egov_data = format_egov_output(result, question)
                        user_message = format_egov_data["message_format"] + format_egov_data["prompt"]
                        shortened_prompt = " ".join(user_message.split())
                        shortened_prompt = shortened_prompt if len(shortened_prompt) <= 10000 else shortened_prompt[:10000]
                        response = process_search_queries(shortened_prompt)

                        try:
                            struct_data = ast.literal_eval(response)
                            print(struct_data)
                        except Exception as e:
                            print("Error evaluating extracted text:", e)

                        return response

            elif tool == 'Adilet':
                pass
            elif tool == 'Web':
                pass
            elif tool == 'FB':
                pass
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 400

    return {"status": "success", "data": data}, 200


if __name__ == '__main__':
    print("Starting flask project!")
    app.run(debug=True)
