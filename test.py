import requests
import json
import os
import ast
from dotenv import load_dotenv
import codecs


load_dotenv()

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")

APIFY_ACTOR_URL = "https://api.apify.com/v2/acts/danek~facebook-search-ppr/run-sync-get-dataset-items"
APIFY_COMMENTS_URL = "https://api.apify.com/v2/acts/danek~facebook-comments-ppr/run-sync-get-dataset-items"

keywords = ["водоснабжение", "субсидии", "водный кодекс"]

# Other search parameters
location = "Almaty"
max_posts = 20
search_type = "posts"

def process_posts():
    all_posts = []

    for keyword in keywords:
        payload = {
            "location": location,
            "max_posts": max_posts,
            "query": keyword,
            "search_type": search_type
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
    for post in posts:
        payload = {
            "includeNestedComments": False,
            "resultsLimit": 50,
            "startUrls": [
                {
                    "url": post.get('url'),
                    "method": "GET"
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
            print(data)
            post["comments"] = []
            for comment in data:
                post["comments"].append({
                    'comments': comment['comments'],
                    'like_count': comment['like_count']
                })

    return posts

if __name__ == "__main__":
    posts = process_posts()

    comments_data = fetch_comments_for_posts(posts)

    print(json.dumps(comments_data, indent=4))
