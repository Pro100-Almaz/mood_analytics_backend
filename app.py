import os
import psycopg2
import io
from flask import Flask, request, jsonify, send_file
from docx import Document
from supabase import create_client, Client
from dotenv import load_dotenv
from flask_cors import CORS
from celery_worker import process_search_task
from docxtpl import DocxTemplate

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


def save_request_to_postgres(query, task_id):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id SERIAL PRIMARY KEY,
                query TEXT,
                task_id VARCHAR(36), 
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("INSERT INTO history (query, task_id) VALUES (%s, %s)", (query, task_id))
        conn.commit()

        cursor.close()
        conn.close()
        return {"message": "Data saved successfully."}
    except Exception as e:
        return {"error": str(e)}


@app.route('/search', methods=['POST'])
def search_endpoint():
    data = request.json
    question = data.get("query")
    full = data.get("full", False)

    if not question or len(question) <= 10:
        return jsonify({"error": "Too short request"}), 400

    task = process_search_task.delay(question, full)

    save_request_to_postgres(question, task.id)

    return jsonify({"task_id": task.id}), 202


@app.route('/least', methods=['GET'])
def least_endpoint():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
                SELECT *
                FROM history
                ORDER BY created_at DESC
                LIMIT 10
            """)

        records = cursor.fetchall()
        results = []
        for record in records:
            results.append({
                "id": record[0],
                "query": record[1],
                "task_id": record[2],
                "created_at": record[3].isoformat() if record[3] else None
            })

        cursor.close()
        conn.close()
        return results
    except Exception as e:
        return {"error": str(e)}


def get_all_assistant_replies(celery_id):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query = "SELECT assistant_replies FROM search WHERE celery_id = %s"
        cursor.execute(query, (celery_id,))
        row = cursor.fetchone()

        cursor.close()
        conn.close()

        if row:
            return row[0]
        else:
            return None
    except Exception as e:
        print("Error fetching assistant replies for celery_id {}: {}".format(celery_id, e))
        return None


# @app.route('/get_opinion/<task_id>', methods=['GET'])
# def get_opinion(task_id):
#     get_assistant_reply = get_all_assistant_replies(task_id)
#
#     return jsonify(response)


@app.route('/search_status/<task_id>', methods=['GET'])
def search_status(task_id):
    from celery.result import AsyncResult
    task = AsyncResult(task_id)

    if task.state == "PENDING":
        response = {"state": task.state, "status": "Pending..."}
    elif task.state != "FAILURE":
        response = {"state": task.state, "result": task.result}
    else:
        response = {"state": task.state, "status": str(task.info)}

    return jsonify(response)

@app.route('/generate_digest/<task_id>', methods=['GET'])
def generate_document(task_id):
    try:

        doc = DocxTemplate("template.pages")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="digest_report.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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


@app.route("/digests", methods=["GET"])
def fetch_documents():
    try:
        # Get pagination parameters from query string; default: page=1, per_page=10
        page = request.args.get("page", default=1, type=int)
        per_page = request.args.get("per_page", default=10, type=int)
        offset = (page - 1) * per_page

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # First, count the total number of rows
        cursor.execute("SELECT COUNT(*) FROM digest")
        total_count = cursor.fetchone()[0]

        # Then, fetch only the rows for the current page
        cursor.execute(
            "SELECT id, title, date FROM digest ORDER BY date LIMIT %s OFFSET %s",
            (per_page, offset)
        )
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        response = {
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "data": [{"id": row[0], "title": row[1], "date": row[2]} for row in rows]
        }
        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/digest", methods=["GET"])
def fetch_document():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        doc_id = request.args.get("id")
        if doc_id:
            cursor.execute("SELECT * FROM digest WHERE id = %s", (doc_id,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                conn.close()
                return jsonify({"error": "Document not found"}), 404
            rows = [{"id": row[0], }]
        else:
            return jsonify({"error": "Too short request"}), 400

        cursor.close()
        conn.close()

        with open("template.pages", "rb") as f:
            template_data = io.BytesIO(f.read())

        doc = DocxTemplate(template_data)

        context = {
            "title": row[1],
            "date": row[2],
            "statistic": row[3],
            "description": row[4],
            "source": row[5],
            "articles_publication": row[6],
            "opinion": row[7],
            "dominating_opinion": row[8]
        }
        doc.render(context)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="digest_report.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("Starting flask project!")
    app.run(debug=True)
