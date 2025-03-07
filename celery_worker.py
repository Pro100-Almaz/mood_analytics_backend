from enum import Enum

from celery import Celery
import requests
import os
from psycopg2 import sql, connect
from psycopg2.extras import Json
import json
from dotenv import load_dotenv
from data_formating import format_egov_output
from apify_client import ApifyClient

from parsing_scripts.adilet import parse_adilet
from parsing_scripts.dialog import parse_dialog
from parsing_scripts.npa import parse_npa
from parsing_scripts.budget import parse_budget
from parsing_scripts.opendata import parse_opendata
from openAI_search_texts import get_search_queries, process_search_queries, analyze_opinion

load_dotenv()

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_TOKEN")
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

APIFY_ACTOR_URL = "https://api.apify.com/v2/acts/danek~facebook-search-ppr/run-sync-get-dataset-items"
APIFY_COMMENTS_URL = "https://api.apify.com/v2/acts/apify~facebook-comments-scraper/run-sync-get-dataset-items"


# Configure Celery with a Redis broker (adjust if needed)
celery_app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')


DB_CONFIG = {
    "user": os.environ.get("PG_USER"),
    "password": os.environ.get("PG_PASSWORD"),
    "database": os.environ.get("PG_DB"),
    "host": os.environ.get("PG_HOST"),
    "port": os.environ.get("PG_PORT")
}

class ProcessStatus(Enum):
    ERROR = 'Error'
    SUCCESS = 'Success'
    INFO = 'Info'


def process_data_from_ai(result, question):
    format_egov_data = format_egov_output(result, question)
    user_message = format_egov_data["message_format"] + format_egov_data["prompt"]
    shortened_prompt = " ".join(user_message.split())
    shortened_prompt = shortened_prompt if len(shortened_prompt) <= 10000 else shortened_prompt[:10000]
    response = process_search_queries(shortened_prompt)

    return response


def track_error(error, step, log_level):
    try:
        with connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                query = sql.SQL(
                    "INSERT INTO {} (log_level, message, step) VALUES (%s, %s, %s)"
                ).format(sql.Identifier("logs"))

                cursor.execute(query, (log_level.value, error, step))
                conn.commit()
    except Exception as e:
        print("Error saving log entry:", str(e))


@celery_app.task(bind=True)
def process_search_task(self, question, full=False):
    begin_date = "01.01.2019"
    max_pages = 5 if full else 1
    process_ids = []

    try:
        data = get_search_queries(question)
    except Exception as e:
        track_error(str(e), 'get_search_queries', ProcessStatus.ERROR)
        return {"status": "error", "response": "OpenAI Error while getting search keywords!"}

    task_id = self.request.id
    sources = data.get("sources", [])

    if not sources:
        track_error("Empty sources!", 'empty_search_result', ProcessStatus.ERROR)
        return {"status": "error", "response": "OpenAI Error while getting search sources!"}

    try:
        for source in sources:
            tool = source.get("tool")

            if not tool:
                track_error("Empty tool!", 'empty_tool_result', ProcessStatus.ERROR)
                continue

            if tool == "Egov":
                params = source.get("params", {})

                if not params:
                    track_error("Empty params got Egov!", 'empty_params_result', ProcessStatus.ERROR)
                    continue

                for param in params:
                    data_type = param.get("type")
                    keywords = param.get("keywords", [])

                    if data_type == "Dialog":
                        task = process_egov_dialog.delay(question, keywords, task_id, begin_date, max_pages)
                    elif data_type == "Opendata":
                        task = process_egov_opendata.delay(question, keywords, task_id, begin_date, max_pages)
                    elif data_type == "NLA":
                        task = process_egov_nla.delay(question, keywords, task_id, begin_date, max_pages)
                    elif data_type == "Budgets":
                        task = process_egov_budgets.delay(question, keywords, task_id, begin_date, max_pages)
                    else:
                        continue

                    process_ids.append({
                        "process_type": data_type,
                        "task_id": task.id
                    })

            elif tool == "Adilet":
                params = source.get("params", {})

                if not params:
                    track_error("Empty params got Adilet!", 'empty_params_result', ProcessStatus.ERROR)
                    continue

                for param in params:
                    data_type = param.get("type")
                    keywords = param.get("keywords", [])

                    if data_type == "NLA":
                        task = process_adilet_nla.delay(question, keywords, task_id, begin_date, max_pages)
                    else:
                        continue

                    process_ids.append({
                        "process_type": data_type,
                        "task_id": task.id
                    })

            elif tool == "FB" or tool == "Instagram" or tool == "Web":
                keywords = source.get("params", {})

                if not keywords:
                    track_error(f"Empty params got {tool}!", 'empty_params_result', ProcessStatus.ERROR)
                    continue

                if tool == "FB":
                    task = process_facebook.delay(question, keywords, task_id)
                elif tool == "Instagram":
                    task = process_instagram.delay(question, keywords, task_id)
                elif tool == "Web":
                    task = process_web.delay(question, keywords, task_id)
                else:
                    continue

                process_ids.append({
                    "process_type": tool,
                    "task_id": task.id
                })

        return {"status": "success", "process_ids": process_ids}

    except Exception as e:
        track_error(str(e), 'source_iteration', ProcessStatus.ERROR)
        return {"status": "error", "response": "OpenAI Error while processing search results!"}


@celery_app.task(bind=True)
def process_egov_dialog(self, question, keywords, task_id, begin_date, max_pages):
    try:
        result = []
        success_status = False
        retries = 0
        summary = {}
        while not success_status and retries < 1:
            for query in keywords:
                parsing_result = parse_dialog(query, begin_date, max_pages=max_pages)
                if parsing_result:
                    for record in parsing_result:
                        if not any(item.get("url") == record.get("url") for item in result):
                            for data in parsing_result:
                                result.append(data)

                        if len(result) >= 1:
                            break

                if len(result) >= 1:
                    break

            summary = process_data_from_ai(result, question)
            success_status = summary['status'] == 'success'
            retries += 1

        if success_status:
            summary["all"] = result
            del summary["status"]
            with connect(**DB_CONFIG) as conn:
                with conn.cursor() as cursor:
                    query = sql.SQL(
                        "INSERT INTO {} (task_id, data) VALUES (%s, %s)"
                    ).format(sql.Identifier("egov_dialog"))

                    cursor.execute(query, (task_id, Json(summary.get('assistant_reply', {"Error": "Empty result!"}))))
                    conn.commit()

            return {"status": "success", "response": summary}

        return {"status": "error"}
    except Exception as e:
        track_error(str(e), 'egov_dialog', ProcessStatus.ERROR)
        return {"status": "error"}


@celery_app.task(bind=True)
def process_egov_opendata(self, question, keywords, task_id, begin_date, max_pages):
    try:
        result = []
        for query in keywords:
            parsing_result = parse_opendata(query, max_pages=max_pages)
            for record in parsing_result:
                result.append({
                    'url': record['link'],
                    'short_description': record['info']['descriptionKk'],
                })

                if len(result) >= 1:
                    break

            if len(result) >= 1:
                break


        summary = process_data_from_ai(result, question)

        if summary['status'] == 'success':
            summary["all"] = result
            del summary["status"]
            with connect(**DB_CONFIG) as conn:
                with conn.cursor() as cursor:
                    query = sql.SQL(
                        "INSERT INTO {} (task_id, data) VALUES (%s, %s)"
                    ).format(sql.Identifier("egov_opendata"))

                    cursor.execute(query, (task_id, Json(summary.get('assistant_reply', {"Error": "Empty result!"}))))
                    conn.commit()

            return {"status": "success", "response": summary}

        return {"status": "error"}

    except Exception as e:
        track_error(str(e), 'egov_opendata', ProcessStatus.ERROR)
        return {"status": "error"}


@celery_app.task(bind=True)
def process_egov_nla(self, question, keywords, task_id, begin_date, max_pages):
    try:
        result = []
        for query in keywords:
            parsing_result = parse_npa(query, begin_date, max_pages=max_pages)
            result.append(parsing_result)

            if len(result) >= 1:
                break

        summary = process_data_from_ai(result, question)

        if summary['status'] == 'success':
            summary["all"] = result
            del summary["status"]
            with connect(**DB_CONFIG) as conn:
                with conn.cursor() as cursor:
                    query = sql.SQL(
                        "INSERT INTO {} (task_id, data) VALUES (%s, %s)"
                    ).format(sql.Identifier("egov_nla"))

                    cursor.execute(query, (task_id, Json(summary.get('assistant_reply', {"Error": "Empty result!"}))))
                    conn.commit()

            return {"status": "success", "response": summary}

        return {"status": "error"}

    except Exception as e:
        track_error(str(e), 'egov_nla', ProcessStatus.ERROR)
        return {"status": "error"}


@celery_app.task(bind=True)
def process_egov_budgets(self, question, keywords, task_id, begin_date, max_pages):
    try:
        result = []
        for query in keywords:
            parsing_result = parse_npa(query, begin_date, max_pages=max_pages)
            result.append(parsing_result)

            if len(result) >= 1:
                break

        summary = process_data_from_ai(result, question)

        if summary['status'] == 'success':
            summary["all"] = result
            del summary["status"]
            with connect(**DB_CONFIG) as conn:
                with conn.cursor() as cursor:
                    query = sql.SQL(
                        "INSERT INTO {} (task_id, data) VALUES (%s, %s)"
                    ).format(sql.Identifier("egov_budget"))

                    cursor.execute(query, (task_id, Json(summary.get('assistant_reply', {"Error": "Empty result!"}))))
                    conn.commit()

            return {"status": "success", "response": summary}

        return {"status": "error"}

    except Exception as e:
        track_error(str(e), 'egov_budgets', ProcessStatus.ERROR)
        return {"status": "error"}


@celery_app.task(bind=True)
def process_adilet_nla(self, question, keywords, task_id, begin_date, max_pages):
    try:
        result = []
        for query in keywords:
            parsing_result = parse_adilet(query, begin_date, max_pages=max_pages)
            if parsing_result:
                for record in parsing_result:
                    result.append({
                        'url': record['detail_url'],
                        'short_description': record['title']
                    })

                    if len(result) >= 1:
                        break

            if len(result) >= 1:
                break

        summary = process_data_from_ai(result, question)

        if summary['status'] == 'success':
            summary["all"] = result
            del summary["status"]
            with connect(**DB_CONFIG) as conn:
                with conn.cursor() as cursor:
                    query = sql.SQL(
                        "INSERT INTO {} (task_id, data) VALUES (%s, %s)"
                    ).format(sql.Identifier("adilet"))

                    cursor.execute(query, (task_id, Json(summary.get('assistant_reply', {"Error": "Empty result!"}))))
                    conn.commit()

            return {"status": "success", "response": summary}

        return {"status": "error"}

    except Exception as e:
        track_error(str(e), 'adilet_nla', ProcessStatus.ERROR)
        return {"status": "error"}


@celery_app.task(bind=True)
def process_web(self, question, keywords, task_id):
    try:
        user_query = keywords
        user_query_str = ", ".join(user_query)
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
                    "content": f"Запрос: {user_query_str}. В начало своего ответа поставь мой первичный запрос без пояснений и потом твой ответ"
                }
            ]
        }
        url_response = requests.post(url, json=payload, headers=headers)
        if url_response.status_code == 200:
            json_data = url_response.json()
            citations = json_data.get("citations")
            research = json_data.get("choices", [{}])[0].get("message", {}).get("content")
            summary = {"citations": citations, "research": research}

            with connect(**DB_CONFIG) as conn:
                with conn.cursor() as cursor:
                    query = sql.SQL(
                        "INSERT INTO {} (task_id, data) VALUES (%s, %s)"
                    ).format(sql.Identifier("web"))

                    cursor.execute(query,(task_id, Json(summary)))
                    conn.commit()

            return {"status": "success", "response": summary}

        return {"status": "error"}
    except Exception as e:
        track_error(str(e), 'web', ProcessStatus.ERROR)
        return {"status": "error"}


@celery_app.task(bind=True)
def process_facebook(self, question, keywords, task_id):
    try:
        search_query = keywords[0]
        query = f"site:facebook.com {search_query}"
        cx = '969efef82512648ba'

        all_links = []
        parsed_data = []

        for start_index in range(1, 21, 10):
            url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={GOOGLE_API_KEY}&cx={cx}&start={start_index}"
            response = requests.get(url)

            if response.status_code != 200:
                track_error('Not 200 status', 'facebook', ProcessStatus.ERROR)
                continue

            results = response.json()

            for item in results.get('items', []):
                all_links.append({"url": item['link']})

        client = ApifyClient(APIFY_TOKEN)

        run_input = {
            "startUrls": all_links,
            "resultsLimit": 50,
            "includeNestedComments": False,
            "viewOption": "RANKED_UNFILTERED",
        }

        run = client.actor("us5srxAYnsrkgUv2v").call(run_input=run_input)

        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            parsed_data.append({
                "url": item.get('facebookUrl'),
                "comment_url": item.get('commentUrl'),
                "short_description": item.get('text')
            })

        with connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                query = sql.SQL(
                    "INSERT INTO {} (task_id, data) VALUES (%s, %s)"
                ).format(sql.Identifier("facebook"))

                cursor.execute(query, (task_id, Json(parsed_data)))
                conn.commit()

        return {"status": "success", "response": parsed_data}

    except Exception as e:
        track_error(str(e), 'web', ProcessStatus.ERROR)
        return {"status": "error"}


@celery_app.task(bind=True)
def process_instagram(self, question, keywords, task_id):
    try:
        search_query = keywords[0]
        query = f"site:instagram.com {search_query}"
        cx = '969efef82512648ba'

        all_links = []
        parsed_data = []

        for start_index in range(1, 21, 10):
            url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={GOOGLE_API_KEY}&cx={cx}&start={start_index}"

            response = requests.get(url)

            if response.status_code != 200:
                track_error('Not 200 status', 'instagram', ProcessStatus.ERROR)
                continue

            results = response.json()

            for item in results.get('items', []):
                if item['link'] not in all_links:
                    parts = item['link'].split('/')
                    link = '/'.join(parts[:3]) + "/" + "/".join(parts[4:])
                    all_links.append(link)

        client = ApifyClient(APIFY_TOKEN)

        run_input = {
            "directUrls": all_links,
            "resultsLimit": 20,
        }

        run = client.actor("SbK00X0JYCPblD2wp").call(run_input=run_input)

        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            if item.get('postUrl', None):
                parsed_data.append({
                    "url": item.get('postUrl'),
                    "short_description": item.get('text')
                })

        with connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                query = sql.SQL(
                    "INSERT INTO {} (task_id, data) VALUES (%s, %s)"
                ).format(sql.Identifier("instagram"))

                cursor.execute(query, (task_id, Json(parsed_data)))
                conn.commit()

        return {"status": "success", "response": parsed_data}

    except Exception as e:
        track_error(str(e), 'instagram', ProcessStatus.ERROR)
        return {"status": "error"}