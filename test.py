import requests
from bs4 import BeautifulSoup



# session = requests.Session()
# base_url = "https://dialog.egov.kz/search"
# params = {
#     "searchText": "НАЙДИ СТАТЬИ, ПУБЛИКАЦИИ по закону О внесении изменений и дополнений в Водный кодекс Республики Казахстан по вопросам разграничения полномочий между местными представительными, центральными и местными исполнительными органами по субсидированию питьевого водоснабжения",
#     'page': 1,
#     "answered": "true"
# }
# headers = {
#     'Accept-Language': 'ru',
# }
#
# response = session.get(base_url, params=params, headers=headers)
#
# soup = BeautifulSoup(response.text, 'lxml')
# tab_pane = soup.find('div', class_='tab-pane')
#
# results = tab_pane.find_all('div', class_='row')
#
# print(results)
#
# for result in results:
#     readmore_link = result.find('a', class_='readmore')
#     if readmore_link and 'href' in readmore_link.attrs:
#         content = None
#         link = readmore_link['href']
#         if "/blogs/all-questions/" not in link:
#             continue
#         type_ = "appeal" if "/blogs/all-questions/" in link else "post"
#         print(f"Переход по ссылке: {link}, тип: {type_}")
#
#         h3 = result.find('h3')
#         if h3.get_text(strip=True) == "Канахин Николай":
#             continue
#
#         next_node = h3.next_sibling
#         while next_node:  # Перебираем соседние узлы, пока не найдем текст
#             if next_node.name is None and next_node.strip():  # Если это текстовый узел
#                 content = next_node.strip()
#                 # print(f"Текст после <h3>: {next_node.strip()}")
#                 break
#             next_node = next_node.next_sibling  # Переходим к следующему узлу
#
#         if content is None:
#             paragraph = result.find('p')
#             if paragraph:
#                 content = paragraph.strip()

        # print(f"https://dialog.egov.kz{link}\nshort_description: ", content)