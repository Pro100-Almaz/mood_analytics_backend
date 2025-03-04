import requests
from bs4 import BeautifulSoup
import time

base_url = "https://dialog.egov.kz/search"

def get_detailed_info(detail_url, type_):
    session = requests.Session()
    try:
        response = requests.get(detail_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            if type_ == "appeal":
                first_focus_block = soup.find('div', id='firstFocus')
                if first_focus_block:
                    question_block = first_focus_block.find('div', class_='b-question')
                    if question_block:
                        question_text_element = question_block.find('p', recursive=False)
                        question_text = question_text_element.get_text() if question_text_element else "Текст обращения не найден"
                    else:
                        question_text = "Текст обращения не найден"
                    date_element = question_block.find('i', class_="fa-calendar") if question_block else None
                    date_text = date_element.next_sibling.strip() if date_element else "Дата обращения не найдена"
                else:
                    question_text = "Текст обращения не найден"
                    date_text = "Дата обращения не найдена"
                answers_block = soup.find('div', id='answers')
                if answers_block:
                    answer_block = answers_block.find('div', class_='media-body')
                    if answer_block:
                        answer_text_element = answer_block.find('p', recursive=False)
                        answer_text = answer_text_element.get_text(strip=True) if answer_text_element else "Текст ответа не найден"
                    else:
                        answer_text = "Текст ответа не найден"
                else:
                    answer_text = "Текст ответа не найден"

            elif type_ == "post":
                first_focus_block = soup.find('div', id='firstFocus')
                question_block = first_focus_block.find('div', class_='b-question') if first_focus_block else None
                if question_block:
                    text_content = []
                    for element in question_block.find_all(['h5', 'p'], recursive=False):
                        if element.get('class') == ['blog-info']:
                            break
                        text_content.append(element.get_text(strip=True))
                    question_text = " ".join(text_content)
                    date_element = question_block.find('i', class_="fa-calendar")
                    date_text = date_element.next_sibling.strip() if date_element else "Дата обращения не найдена"
                    answer_text = ""
                else:
                    question_text = "Текст обращения не найден"
                    date_text = "Дата обращения не найдена"
                    answer_text = ""
            return {
                "url": detail_url,
                "type": type_,
                "question_text": question_text.replace("\n", "").replace("\r", ""),
                "date": date_text,
                # "answer_text": answer_text.replace("\n", "").replace("\r", "")
            }
        else:
            print(f"Ошибка при загрузке страницы: {response.status_code}")
            return None
    except Exception as e:
        print("Ошибка при получении детальной страницы диалогов:", e)
    finally:
        session.close()


def parse_dialog(query_value, begin_date=None, end_date=None, max_pages=1):
    page = 1
    data = []
    total_parsed = 0  # Counter for collected elements
    while page <= int(max_pages) and total_parsed < 5:
        params = {"searchText": query_value, "page": page, "answered": "true"}
        if begin_date:
            params["beginDate"] = begin_date
        if end_date:
            params["endDate"] = end_date
        headers = {"Accept-Language": "ru"}

        session = requests.Session()
        try:
            response = session.get(base_url, params=params, headers=headers, timeout=30)
            if response.status_code != 200:
                print("Error loading page %s: %s" % (page, response.status_code))
                break

            soup = BeautifulSoup(response.text, "lxml")
            tab_pane = soup.find("div", class_="tab-pane")
            if not tab_pane:
                print("Parent element 'tab-pane' not found on page %s" % page)
                break

            results = tab_pane.find_all("div", class_="row")
            if not results:
                print("No result cards on page %s" % page)
                break

            for result in results:
                if total_parsed >= 5:
                    break

                readmore_link = result.find("a", class_="readmore")
                if readmore_link and "href" in readmore_link.attrs:
                    link = readmore_link["href"]
                    if "/blogs/all-questions/" not in link:
                        continue
                    type_ = "appeal" if "/blogs/all-questions/" in link else "post"

                    h3 = result.find("h3")
                    if h3 and h3.get_text(strip=True) == "Канахин Николай":
                        continue

                    content = None
                    next_node = h3.next_sibling if h3 else None
                    while next_node:
                        if next_node.name is None and next_node.strip():
                            content = next_node.strip()
                            break
                        next_node = next_node.next_sibling

                    if content is None:
                        paragraph = result.find("p")
                        if paragraph:
                            content = paragraph.get_text(strip=True)

                    data.append({
                        "url": f"https://dialog.egov.kz{link}",
                        "short_description": content or "",
                    })
                    total_parsed += 1

            print(f"Парсинг страницы {page} завершен. Всего элементов: {total_parsed}")
            if total_parsed >= 5:
                break

            page += 1
            time.sleep(1)
        except Exception as e:
            print("Exception on page %s: %s" % (page, e))
            break
        finally:
            session.close()
    return data

# Example usage:
# results = parse_dialog("пример запроса", max_pages=3)
# print(results)
