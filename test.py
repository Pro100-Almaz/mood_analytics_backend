from parsing_scripts.dialog import *
from celery_worker import *



keywords= ["водоснабжение", "субсидии", "разграничение полномочий", "питьевая вода", "ЗРК 411-VI", "водный кодекс",
             "центральные органы", "местные органы", "представительные органы"]

question = ("НАЙДИ СТАТЬИ, ПУБЛИКАЦИИ по закону О внесении изменений и дополнений в Водный кодекс Республики Казахстан "
            "по вопросам разграничения полномочий между местными представительными, центральными и местными "
            "исполнительными органами по субсидированию питьевого водоснабжения ЗРК от 25 января 2021 года № "
            "411-VI /опубл. 28.01.2021")

begin_date = "01.05.2021"
result_list = []

## Egov -> Dialog
# for query in keywords:
#     parsing_result = parse_dialog(query, begin_date, max_pages=1)
#     if parsing_result:
#         for result in parsing_result:
#             if not any(item.get("url") == result.get("url") for item in result_list):
#                 for data in parsing_result:
#                     result_list.append(data)

## Egov -> Opendata
# for keyword in keywords:
#     parsing_result = parse_opendata(question, max_pages=1)
#     if parsing_result:
#         for record in parsing_result:
#             result_list.append({
#                 'url': record['link'],
#                 'short_description': record['info']['descriptionRu']
#             })


## Egov -> NLA
# for keyword in keywords:
#     parsing_result = parse_npa(keyword, begin_date, max_pages=1)
#     if parsing_result:
#         for record in parsing_result:
#             result_list.append({
#                 'url': record['detail_url'],
#                 'short_description': record['title']
#             })

## Adilet -> NLA
# for keyword in keywords:
#     parsing_result = parse_adilet(keyword, begin_date, max_pages=1)
#     if parsing_result:
#         for record in parsing_result:
#             result_list.append({
#                 'url': record['detail_url'],
#                 'short_description': record['title']
#             })


# posts = process_posts(keywords)
# comments_data = fetch_comments_for_posts(posts)
#
# for comment in comments_data:
#     result_list.append({
#         'url': comment.get('url'),
#         'short_description': comment.get('message')
#     })


all_posts = []
APIFY_ACTOR_URL = "https://api.apify.com/v2/acts/apify~instagram-post-scraper/run-sync?token=apify_api_JlD1DxdITmx9pjL6j67F13R7zsHSN82f8xxQ"

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
print(response.json())

if 200 <= response.status_code < 300:
    data = response.json()
    print(data)
    for post in data:
        all_posts.append({
            'post_id': post['post_id'],
            'url': post['url'],
            'message': post['message']
        })

# result = process_data_from_ai(result_list, question)
#
# print(result)
