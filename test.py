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


# all_posts = []
# APIFY_ACTOR_URL = "https://api.apify.com/v2/acts/apify~instagram-post-scraper/run-sync?token=apify_api_JlD1DxdITmx9pjL6j67F13R7zsHSN82f8xxQ"
#
# payload = {
#     "usernames": ['tengrinewskz', 'holanewskz', 'qumash_kz', 'kazpress.kz', 'astanovka98',
#                   'vastane.kz', 'qazpress.kz', 'astana_newtimes', 'taspanewskz', 'kris.p.media'],
#     "resultsLimit": 50,
#     "searchType": "posts",
#     "includeComments": True,
#     "includeTaggedPosts": False,
#     "includeStories": False,
# }
#
# url = APIFY_ACTOR_URL
# if APIFY_TOKEN:
#     url += f"?token={APIFY_TOKEN}"
#
# response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
# print(response.json())
#
# if 200 <= response.status_code < 300:
#     data = response.json()
#     print(data)
#     for post in data:
#         all_posts.append({
#             'post_id': post['post_id'],
#             'url': post['url'],
#             'message': post['message']
#         })


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

def process_search_task(question, full):
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
                    # if data_type == 'Dialog':
                    #     try:
                    #         result = []
                    #         success_status = False
                    #         retries = 0
                    #         summary = {}
                    #         while not success_status and retries < 5:
                    #             for query in param.get("keywords", []):
                    #                 parsing_result = parse_dialog(query, begin_date, max_pages=max_pages)
                    #                 if parsing_result:
                    #                     for record in parsing_result:
                    #                         if not any(item.get("url") == record.get("url") for item in result):
                    #                             print("Adding to result of egov dialog")
                    #                             for data in parsing_result:
                    #                                 result.append(data)
                    #
                    #             summary = process_data_from_ai(result, question)
                    #             success_status = summary['status'] == 'success'
                    #             retries += 1
                    #
                    #         response['egov']['dialog']['assistant_reply'] = summary.get('assistant_reply', [])
                    #         response['egov']['dialog']['all'] = result
                    #     except Exception as e:
                    #         track_error(str(e), "egov.dialog", "Error")
                    #         continue

                    if data_type == 'Opendata':
                        try:
                            result = []
                            for query in param.get("keywords", []):
                                parsing_result = parse_opendata(query, max_pages=1)
                                if parsing_result:
                                    for record in parsing_result:
                                        result.append({
                                            'url': record['link'],
                                            'short_description': record['info']['descriptionRu']
                                        })

                            response['egov']["opendata"]['assistant_reply'] = process_data_from_ai(result, question).get('assistant_reply', [])
                            response['egov']['opendata']['all'] = result
                        except Exception as e:
                            track_error(str(e), "egov.opendata", "Error")
                            continue

                    # elif data_type == 'NLA':
                    #     try:
                    #         result = []
                    #         for query in param.get("keywords", []):
                    #             parsing_result = parse_npa(query, begin_date, max_pages=max_pages)
                    #             result.append(parsing_result)
                    #
                    #         response['egov']["npa"]['assistant_reply'] = process_data_from_ai(result, question).get('assistant_reply', [])
                    #         response['egov']['npa']['all'] = result
                    #     except Exception as e:
                    #         track_error(str(e), "egov.nla", "Error")
                    #         continue
                    #
                    # elif data_type == 'Budgets':
                    #     try:
                    #         result = []
                    #         for query in param.get("keywords", []):
                    #             parsing_result = parse_budget(query, max_pages=max_pages)
                    #             for record in parsing_result:
                    #                 try:
                    #                     result.append({
                    #                         'link': record['detail_url'],
                    #                         'summary': record['title'],
                    #                         'relev_score': '0.9'
                    #                     })
                    #                 except Exception:
                    #                     continue
                    #
                    #         response['egov']["budgets"]['assistant_reply'] = []
                    #         response['egov']["budgets"]['all'] = result
                    #     except Exception as e:
                    #         track_error(str(e), "egov.budgets", "Error")
                    #         continue

            # elif tool == 'Adilet':
            #     response.setdefault('adilet', {})
            #     for param in source.get("params", []):
            #         data_type = param.get("type")
            #         if data_type == 'NLA':
            #             try:
            #                 result = []
            #                 success_status = False
            #                 retries = 0
            #                 summary = {}
            #                 while not success_status and retries < 5:
            #                     for query in param.get("keywords", []):
            #                         parsing_result = parse_adilet(query, begin_date, max_pages=max_pages)
            #                         if parsing_result:
            #                             for record in parsing_result:
            #                                 result.append({
            #                                     'url': record['detail_url'],
            #                                     'short_description': record['title']
            #                                 })
            #
            #                         summary = process_data_from_ai(result, question)
            #                         success_status = summary['status'] == 'success'
            #                         retries += 1
            #
            #                 response['adilet']["npa"]['assistant_reply'] = summary.get('assistant_reply', [])
            #                 response['adilet']["npa"]['all'] = result
            #             except Exception as e:
            #                 track_error(str(e), "adilet.nla", "Error")
            #                 continue
            #         elif data_type == 'Research':
            #             # Add your processing for Research if needed
            #             pass
            #
            # elif tool == 'Web':
            #     try:
            #         user_query = source.get("params", [])
            #         user_query_str = ", ".join(user_query)
            #         url = "https://api.perplexity.ai/chat/completions"
            #         headers = {
            #             "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            #             "Content-Type": "application/json"
            #         }
            #         payload = {
            #             "model": "llama-3.1-sonar-small-128k-online",
            #             "messages": [
            #                 {
            #                     "role": "system",
            #                     "content": "Будьте точным, СВЕРХКРАТКИМ и лаконичным исследователем для правительства Казахстана. Отвечай все на русском! Исключи анализ НПА и законов."
            #                 },
            #                 {
            #                     "role": "user",
            #                     "content": f"Запрос: {user_query_str}. В начало своего ответа поставь мой первичный запрос без пояснений и потом твой ответ"
            #                 }
            #             ]
            #         }
            #         url_response = requests.post(url, json=payload, headers=headers)
            #         if url_response.status_code == 200:
            #             json_data = url_response.json()
            #             citations = json_data.get("citations")
            #             research = json_data.get("choices", [{}])[0].get("message", {}).get("content")
            #             response['web'] = {"citations": citations, "research": research}
            #     except Exception as e:
            #         track_error(str(e), "web", "Error")
            #         continue

            # elif tool == 'FB':
            #     try:
            #         result = []
            #         keywords = source.get("params", [])
            #         posts = process_posts_fb(keywords)
            #         comments_data = fetch_comments_for_posts_fb(posts)
            #
            #         for comment in comments_data:
            #             result.append({
            #                 'url': comment.get('url'),
            #                 'short_description': comment.get('message')
            #             })
            #
            #         summary = process_data_from_ai(result, question)
            #
            #         response['facebook']['assistant_reply'] = summary.get('assistant_reply', [])
            #         response['facebook']['all'] = result
            #     except Exception as e:
            #         track_error(str(e), "fb", "Error")
            #         continue

            # elif tool == 'Instagram':
            #     result = []

    except Exception as e:
        return {"error": str(e)}

    try:
        # task_id = self.request.id

        assistant_replies = []
        if "egov" in response:
            if "dialog" in response["egov"] and "assistant_reply" in response["egov"]["dialog"]:
                assistant_replies.append({"egov_dialog": response["egov"]["dialog"]["assistant_reply"]})
            if "opendata" in response["egov"] and "assistant_reply" in response["egov"]["opendata"]:
                assistant_replies.append({"egov_opendata": response["egov"]["opendata"]["assistant_reply"]})
            if "npa" in response["egov"] and "assistant_reply" in response["egov"]["npa"]:
                assistant_replies.append({"egov_npa": response["egov"]["npa"]["assistant_reply"]})
        if "adilet" in response:
            if "npa" in response["adilet"] and "assistant_reply" in response["adilet"]["npa"]:
                assistant_replies.append({"adilet_npa": response["adilet"]["npa"]["assistant_reply"]})
        if "facebook" in response:
            if "assistant_reply" in response["facebook"]:
                assistant_replies.append({"facebook": response["facebook"]["assistant_reply"]})

        # conn = psycopg2.connect(**DB_CONFIG)
        # cursor = conn.cursor()
        #
        # cursor.execute("""
        #         CREATE TABLE IF NOT EXISTS search (
        #             id SERIAL PRIMARY KEY,
        #             celery_id VARCHAR(64) NOT NULL,
        #             question TEXT,
        #             assistant_replies JSONB,
        #             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        #         )
        #     """)
        # conn.commit()
        #
        # cursor.execute(
        #     "INSERT INTO search (celery_id, question, assistant_replies) VALUES (%s, %s, %s)",
        #     (task_id, question, json.dumps(assistant_replies))
        # )
        # conn.commit()
        #
        # cursor.close()
        # conn.close()

        opinion = json.loads(analyze_opinion(question, assistant_replies))
    except Exception as e:
        opinion = None


    return {"status": "success", "response": response, "opinion": opinion}


result = process_search_task(question, False)
