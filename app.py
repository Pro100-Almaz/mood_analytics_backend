import glob
import requests
import os
import ast
import psycopg2
import io
from flask import Flask, request, jsonify
from docx import Document
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

DB_CONFIG = {
    "user": os.environ.get("PG_USER"),
    "password": os.environ.get("PG_PASSWORD"),
    "database": os.environ.get("PG_DB"),
    "host": os.environ.get("PG_HOST"),
    "port": os.environ.get("PG_PORT")
}

PERPLEXITY_API_KEY = os.environ.get("API_TOKEN")


def extract_text_from_docx(file_stream):
    doc = Document(file_stream)
    parsing_data = {
        "title": "",
        "date": "",
        "statistic": "",
        "description": "",
        "source": "",
        "articles_publication": "",
        "opinion": "",
        "dominating_opinion": ""
    }

    for table in doc.tables:
        for row in table.rows:
            row_text = [cell.text for cell in row.cells]
            if row_text[1] == "Название закона":
                parsing_data["title"] = row_text[2]
            elif row_text[1] == "Дата принятия":
                parsing_data["date"] = row_text[2]
            elif row_text[1] == "Статистика":
                parsing_data["statistic"] = row_text[2]
            elif row_text[1] == "Основные положения":
                parsing_data["description"] = row_text[2]
            elif row_text[1] == "Источники информации":
                parsing_data["source"] = row_text[2]
            elif row_text[1] == "Статьи и публикация":
                parsing_data["articles_publication"] = row_text[2]
            elif row_text[1] == "Мнение населения":
                parsing_data["opinion"] = row_text[2]
            elif row_text[1] == "Доминирующее мнение":
                parsing_data["dominating_opinion"] = row_text[2]

    return parsing_data["title"]


def save_to_postgres(text):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS digest (
                id SERIAL PRIMARY KEY,
                title TEXT,
                date TEXT,
                statistic TEXT,
                description TEXT,
                source TEXT,
                articles_publication TEXT,
                opinion TEXT,
                dominating_opinion TEXT
            )
        """)

        cursor.execute("INSERT INTO digest (title, date, statistic, description, source, articles_publication,"
                       "opinion, dominating_opinion ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                       (text["title"], text["date"], text["statistic"], text["description"], text["source"],
                        text["articles_publication"], text["opinion"], text["dominating_opinion"]))
        conn.commit()

        cursor.close()
        conn.close()
        return {"message": "Data saved successfully."}
    except Exception as e:
        return {"error": str(e)}


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
                user_query = source.get("params", [])
                user_query = ", ".join(user_query)
                url = "https://api.perplexity.ai/chat/completions"

                headers = {
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Будьте точным, СВЕРХКРАТКИМ и лаконичным исследователем для правительства Казахстана. Отвечай все на русском! Исключи анализ НПА и законов."
                        },
                        {
                            "role": "user",
                            "content": f"Запрос: {user_query}. В начало своего ответа поставь мой первичный запрос без пояснений и потом твой ответ"
                        }
                    ]
                }

                url_response = requests.post(url, json=payload, headers=headers)

                if url_response.status_code == 200:
                    citations = url_response.json()["citations"]
                    research = url_response.json()["choices"][0]["message"]["content"]
                    response['web'] = {
                        "citations": citations,
                        "research": research
                    }

            elif tool == 'FB':
                pass
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 400

    print(response)

    return {"status": "success", "response": response}, 200


# Flask route to handle file uploads
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if not file.filename.endswith(".docx"):
        return jsonify({"error": "Invalid file type. Only .docx allowed."}), 400

    try:
        file_stream = io.BytesIO(file.read())

        extracted_text = extract_text_from_docx(file_stream)

        return jsonify({"status": "success", "text": extracted_text}), 200

    except Exception as e:
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500


# Route to fetch saved documents
@app.route("/digests", methods=["GET"])
def fetch_documents():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT id, title, date FROM digest ORDER BY date")
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify([{"id": row[0], "title": row[1], "date": row[2]} for row in rows])

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/digest", methods=["GET"])
def fetch_document():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Get ID from query parameters
        doc_id = request.args.get("id")

        if doc_id:  # If ID is provided, fetch specific document
            cursor.execute("SELECT id, title, date FROM digest WHERE id = %s", (doc_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                return jsonify({"id": row[0], "title": row[1], "date": row[2]})
            else:
                return jsonify({"error": "Document not found"}), 404

        else:  # If no ID is provided, return all documents
            cursor.execute("SELECT id, title, date FROM documents")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            return jsonify([{"id": row[0], "title": row[1], "date": row[2]} for row in rows])

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("Starting flask project!")
    app.run(debug=True)
