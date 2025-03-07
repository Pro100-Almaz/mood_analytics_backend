import re

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

# user_query = keywords
# user_query_str = ", ".join(user_query)
# url = "https://api.perplexity.ai/chat/completions"
# headers = {
#     "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
#     "Content-Type": "application/json"
# }
# payload = {
#     "model": "llama-3.1-sonar-small-128k-online",
#     "messages": [
#         {
#             "role": "system",
#             "content": "Будьте точным, СВЕРХКРАТКИМ и лаконичным исследователем для правительства Казахстана. Отвечай все на русском! Исключи анализ НПА и законов."
#         },
#         {
#             "role": "user",
#             "content": f"Запрос: {user_query_str}. В начало своего ответа поставь мой первичный запрос без пояснений и потом твой ответ"
#         }
#     ]
# }
# url_response = requests.post(url, json=payload, headers=headers)
# if url_response.status_code == 200:
#     json_data = url_response.json()
#     citations = json_data.get("citations")
#     research = json_data.get("choices", [{}])[0].get("message", {}).get("content")
#     print({"citations": citations, "research": research})
    # response['web'] = {"citations": citations, "research": research}

# result = process_data_from_ai(result_list, question)
#
# print(result)

class ProcessStatus(Enum):
    ERROR = 'Error'
    SUCCESS = 'Success'
    INFO = 'Info'

def process_facebook_test(question, keywords, task_id):
    try:
        query = f"site:instagram.com Изменения в Водном кодексе Казахстана"
        cx = '969efef82512648ba'
        pattern = re.compile(r"(https?:\/\/(?:www\.)?instagram\.com\/(?:p|reel)\/([^/?#&]+)).*")

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
                    if pattern.match(link):
                        all_links.append(link)

        client = ApifyClient(APIFY_TOKEN)

        run_input = {
            "directUrls": all_links[:1],
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


    except Exception as e:
        track_error(str(e), 'instagram', ProcessStatus.ERROR)
        return {"status": "error"}

process_facebook_test(question, keywords, 0)

