from celery import Celery
import requests
import os
import ast
from dotenv import load_dotenv
from data_formating import format_egov_output

from parsing_scripts.adilet import parse_adilet
from parsing_scripts.dialog import parse_dialog
from parsing_scripts.npa import parse_npa
from parsing_scripts.budget import parse_budget
from parsing_scripts.opendata import parse_opendata
from openAI_search_texts import get_search_queries, process_search_queries

load_dotenv()

PERPLEXITY_API_KEY = os.environ.get("API_TOKEN")
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")

APIFY_ACTOR_URL = "https://api.apify.com/v2/acts/danek~facebook-search-ppr/run-sync-get-dataset-items"
APIFY_COMMENTS_URL = "https://api.apify.com/v2/acts/apify~facebook-comments-scraper/run-sync-get-dataset-items"


# Configure Celery with a Redis broker (adjust if needed)
celery_app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')


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
        return response


def process_posts(keywords):
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
                    'post_id': post['post_id'],
                    'url': post['url'],
                    'message': post['message']
                })

    return all_posts


def fetch_comments_for_posts(posts):
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


@celery_app.task
def process_search_task(question, full):
    begin_date = "01.05.2021"
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
                            for query in param.get("keywords", []):
                                parsing_result = parse_dialog(query, begin_date, max_pages=max_pages)
                                result.append(parsing_result)
                            response['egov']["dialog"] = process_data_from_ai(result, question)
                        except Exception as e:
                            response['egov']["dialog"] = []

                    elif data_type == 'Opendata':
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
                                except Exception:
                                    continue
                        response['egov']["opendata"] = result

                    elif data_type == 'NLA':
                        result = []
                        for query in param.get("keywords", []):
                            parsing_result = parse_npa(query, begin_date, max_pages=max_pages)
                            result.append(parsing_result)

                        response['egov']["npa"] = process_data_from_ai(result, question)
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
                        result = []
                        for query in param.get("keywords", []):
                            parsing_result = parse_adilet(query, begin_date, max_pages=max_pages)
                            result.append(parsing_result)

                        response['adilet']["npa"] = process_data_from_ai(result, question)
                    elif data_type == 'Research':
                        # Add your processing for Research if needed
                        pass

            elif tool == 'Web':
                # Combine parameters into a single query string
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

            elif tool == 'FB':
                keywords = source.get("params", [])
                posts = process_posts(keywords)
                comments_data = fetch_comments_for_posts(posts)

                response['facebook'] = comments_data

    except Exception as e:
        # Optionally, you can log e and return an error object
        return {"error": str(e)}

    return {"status": "success", "response": response}
