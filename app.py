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


def process_data_from_ai(result, question):
    format_egov_data = format_egov_output(result, question)
    user_message = format_egov_data["message_format"] + format_egov_data["prompt"]
    shortened_prompt = " ".join(user_message.split())
    shortened_prompt = shortened_prompt if len(shortened_prompt) <= 10000 else shortened_prompt[:10000]
    response = process_search_queries(shortened_prompt)

    print(response)

    try:
        struct_data = ast.literal_eval(response)
        return struct_data
    except Exception as e:
        return {"code": 400, "error": str(e)}

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

    response = {}

    try:
        print(data)
        for source in data.get("research", []):
            tool = source.get("tool", None)
            if tool is None:
                continue

            if tool == 'Egov':
                response['egov'] = {}
                for param in source.get("params", []):
                    data_type = param.get("type", None)

                    if data_type == 'Dialog':
                        result = []
                        for query in param.get("keywords", []):
                            parsing_result = parse_dialog(query, begin_date, max_pages=max_pages)
                            result.append(parsing_result)

                        response['egov']["dialog"] = process_data_from_ai(result, question)

                    if data_type == 'Opendata':
                        result = []
                        for query in param.get("keywords", []):
                            parsing_result = parse_opendata(query, max_pages=max_pages)
                            for record in parsing_result:
                                try:
                                    result.append({
                                        'link': record['link'],
                                        'summary': record['info']['descriptionKk'],
                                        'relev_score': '0.9'
                                    })
                                except Exception as e:
                                    continue

                        response['egov']["opendata"] = result

                        return response

                    if data_type == 'NLA':
                        result = []
                        for query in param.get("keywords", []):
                            parsing_result = parse_npa(query, begin_date, max_pages=max_pages)
                            for record in parsing_result:
                                try:
                                    result.append({
                                        'link': record['details_url'],
                                        'summary': record['title'],
                                        'relev_score': '0.9'
                                    })
                                except Exception as e:
                                    continue

                        response['egov']["npa"] = result

                    if data_type == 'Budgets':
                        result = []
                        for query in param.get("keywords", []):
                            parsing_result = parse_budget(query, max_pages=max_pages)
                            for record in parsing_result:
                                try:
                                    result.append({
                                        'link': record['detail_url'],
                                        'summary': record['title'],
                                        'relev_score': '0.9'
                                    })
                                except Exception as e:
                                    continue

                        response['egov']["npa"] = result

            elif tool == 'Adilet':
                response['adilet'] = {}
                for param in source.get("params", []):
                    data_type = param.get("type", None)

                    if data_type == 'NLA':
                        result = []
                        for query in param.get("keywords", []):
                            parsing_result = parse_adilet(query, begin_date, max_pages=max_pages)
                            for record in parsing_result:
                                try:
                                    result.append({
                                        'link': record['detail_url'],
                                        'summary': record['title'],
                                        'relev_score': '0.9'
                                    })
                                except Exception as e:
                                    continue

                        response['egov']["npa"] = result

                    if data_type == 'Research':
                        pass

            elif tool == 'Web':
                pass
            elif tool == 'FB':
                pass
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 400

    print(response)

    return {"status": "success", "response": response}, 200


if __name__ == '__main__':
    print("Starting flask project!")
    app.run(debug=True)
