from celery import Celery
import requests
import os
import psycopg2
import json
from dotenv import load_dotenv
from data_formating import format_egov_output

from parsing_scripts.adilet import parse_adilet
from parsing_scripts.dialog import parse_dialog
from parsing_scripts.npa import parse_npa
from parsing_scripts.budget import parse_budget
from parsing_scripts.opendata import parse_opendata
from openAI_search_texts import get_search_queries, process_search_queries, analyze_opinion

load_dotenv()

PERPLEXITY_API_KEY = os.environ.get("API_TOKEN")
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")

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


def process_data_from_ai(result, question):
    format_egov_data = format_egov_output(result, question)
    user_message = format_egov_data["message_format"] + format_egov_data["prompt"]
    shortened_prompt = " ".join(user_message.split())
    shortened_prompt = shortened_prompt if len(shortened_prompt) <= 10000 else shortened_prompt[:10000]
    response = process_search_queries(shortened_prompt)

    return response


def process_posts_fb(keywords):
    all_posts = []

    for keyword in keywords:
        payload = {
            "location": "Almaty",
            "max_posts": 20,
            "query": keyword,
            "search_type": "posts"
        }

        url = APIFY_ACTOR_URL
        if APIFY_TOKEN:
            url += f"?token={APIFY_TOKEN}"

        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})

        if 200 <= response.status_code < 300:
            data = response.json()
            for post in data:
                all_posts.append({
                    'post_id': post.get('post_id'),
                    'url': post.get('url'),
                    'message': post.get('message')
                })

    return all_posts


def fetch_comments_for_posts_fb(posts):
    all_comments = []

    payload = {
        "includeNestedComments": False,
        "resultsLimit": 10,
        "startUrls": [
            {
                "url": post.get('url'),
            } for post in posts
        ]
    }

    url = APIFY_COMMENTS_URL
    if APIFY_TOKEN:
        url += f"?token={APIFY_TOKEN}"

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)


    if 200 <= response.status_code < 300:
        data = response.json()
        for comment in data:
            all_comments.append(
                {
                    'url': comment.get('facebookUrl', ""),
                    'message': comment.get('text', "")
                }
            )

    if len(all_comments) == 0:
        return posts

    return all_comments


def process_posts_ig():
    all_posts = []

    payload = {
        "usernames": ['tengrinewskz', 'holanewskz', 'qumash_kz', 'kazpress.kz', 'astanovka98',
                      'vastane.kz', 'qazpress.kz', 'astana_newtimes', 'taspanewskz', 'kris.p.media'],
        "resultsLimit": 50,
        "searchType": "posts",
        "includeComments": True,
        "includeTaggedPosts": False,
        "includeStories": False,
    }

    url = APIFY_ACTOR_URL
    if APIFY_TOKEN:
        url += f"?token={APIFY_TOKEN}"

    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})

    if 200 <= response.status_code < 300:
        data = response.json()
        for post in data:
            all_posts.append({
                'post_id': post['post_id'],
                'url': post['url'],
                'message': post['message']
            })

    return all_posts


def fetch_comments_for_posts_ig(posts):
    all_comments = []

    payload = {
        "includeNestedComments": False,
        "resultsLimit": 50,
        "startUrls": [
            {
                "url": post.get('url'),
            } for post in posts
        ]
    }

    url = APIFY_COMMENTS_URL
    if APIFY_TOKEN:
        url += f"?token={APIFY_TOKEN}"

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)


    if 200 <= response.status_code < 300:
        data = response.json()
        for comment in data:
            all_comments.append(
                {
                    'url': comment.get('facebookUrl', ""),
                    'message': comment.get('text', "")
                }
            )

    if len(all_comments) == 0:
        return posts

    return all_comments


def track_error(error, step, log_level):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                log_level VARCHAR(10) NOT NULL,
                message TEXT,
                step VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        cursor.execute(
            "INSERT INTO logs (log_level, message, step) VALUES (%s, %s, %s)",
            (log_level, error, step)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error saving log entry:", str(e))


@celery_app.task(bind=True)
def process_search_task(self, question, full):
    begin_date = "01.01.2021"
    max_pages = 1 if full else 5
    data = get_search_queries(question)
    response = {}

    try:
        for source in data.get("research", []):
            tool = source.get("tool")
            if not tool:
                continue

            if tool == 'Egov':
                response.setdefault('egov', {})
                for param in source.get("params", []):
                    data_type = param.get("type")
                    if data_type == 'Dialog':
                        try:
                            result = []
                            success_status = False
                            retries = 0
                            summary = {}
                            while not success_status and retries < 5:
                                for query in param.get("keywords", []):
                                    parsing_result = parse_dialog(query, begin_date, max_pages=max_pages)
                                    if parsing_result:
                                        for record in parsing_result:
                                            if not any(item.get("url") == record.get("url") for item in result):
                                                print("Adding to result of egov dialog")
                                                for data in parsing_result:
                                                    result.append(data)

                                            if len(result) >= 20:
                                                break

                                summary = process_data_from_ai(result, question)
                                success_status = summary['status'] == 'success'
                                retries += 1

                            response['egov']['dialog'] = summary
                            response['egov']['dialog']['all'] = result
                        except Exception as e:
                            response['egov']["dialog"] = []


                    elif data_type == 'Opendata':
                        result = []
                        for query in param.get("keywords", []):
                            parsing_result = parse_opendata(query, max_pages=max_pages)
                            for record in parsing_result:
                                if len(result) >= 20:
                                    break
                                try:
                                    result.append({
                                        'url': record['link'],
                                        'short_description': record['info']['descriptionKk'],
                                        'relev_score': '0.9'
                                    })
                                except Exception:
                                    continue
                        response['egov']["opendata"] = process_data_from_ai(result, question)
                        response['egov']["opendata"]['all'] = result


                    elif data_type == 'NLA':
                        result = []
                        for query in param.get("keywords", []):
                            parsing_result = parse_npa(query, begin_date, max_pages=max_pages)
                            result.append(parsing_result)

                            if len(result) >= 20:
                                break

                        # response['egov']["npa"] = process_data_from_ai(result, question)
                        response['egov']["npa"]['all'] = result


                    elif data_type == 'Budgets':
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
                                except Exception:
                                    continue

                        response['egov']["budgets"] = result

            elif tool == 'Adilet':
                response.setdefault('adilet', {})
                for param in source.get("params", []):
                    data_type = param.get("type")
                    if data_type == 'NLA':
                        try:
                            result = []
                            for query in param.get("keywords", []):
                                parsing_result = parse_adilet(query, begin_date, max_pages=max_pages)
                                if parsing_result:
                                    if len(result) >= 20:
                                        break

                                    for record in parsing_result:
                                        result.append({
                                            'url': record['detail_url'],
                                            'short_description': record['title']
                                        })

                            # response['adilet']["npa"] = process_data_from_ai(result, question)
                            response['adilet']["npa"] = result
                        except Exception as e:
                            track_error(str(e), "adilet.nla", "Error")
                            continue
                    elif data_type == 'Research':
                        # Add your processing for Research if needed
                        pass

            elif tool == 'Web':
                try:
                    user_query = source.get("params", [])
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
                        response['web'] = {"citations": citations, "research": research}
                except Exception as e:
                    track_error(str(e), "web", "Error")
                    continue

            elif tool == 'FB':
                keywords = source.get("params", [])
                posts = process_posts_fb(keywords)
                comments_data = fetch_comments_for_posts_fb(posts)

                response['facebook'] = comments_data
    except Exception as e:
        return {"error": str(e)}

    try:
        task_id = self.request.id

        # assistant_replies = []
        # if "egov" in response:
        #     if "dialog" in response["egov"] and "assistant_reply" in response["egov"]["dialog"]:
        #         assistant_replies.append({"egov_dialog": response["egov"]["dialog"]["assistant_reply"]})
        #     if "opendata" in response["egov"] and "assistant_reply" in response["egov"]["opendata"]:
        #         assistant_replies.append({"egov_opendata": response["egov"]["opendata"]["assistant_reply"]})
        #     if "npa" in response["egov"] and "assistant_reply" in response["egov"]["npa"]:
        #         assistant_replies.append({"egov_npa": response["egov"]["npa"]["assistant_reply"]})
        # if "adilet" in response:
        #     if "npa" in response["adilet"] and "assistant_reply" in response["adilet"]["npa"]:
        #         assistant_replies.append({"adilet_npa": response["adilet"]["npa"]["assistant_reply"]})
        # if "facebook" in response:
        #     if "assistant_reply" in response["facebook"]:
        #         assistant_replies.append({"facebook": response["facebook"]["assistant_reply"]})

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
                CREATE TABLE IF NOT EXISTS search (
                    id SERIAL PRIMARY KEY,
                    celery_id VARCHAR(64) NOT NULL,
                    question TEXT,
                    assistant_replies JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()

        cursor.execute(
            "INSERT INTO search (celery_id, question, assistant_replies) VALUES (%s, %s, %s)",
            (task_id, question, json.dumps(response))
        )
        conn.commit()

        cursor.close()
        conn.close()

        opinion = analyze_opinion(question, json.dumps(response))
    except Exception as e:
        opinion = None


    return {"status": "success", "response": response, "opinion": opinion}
