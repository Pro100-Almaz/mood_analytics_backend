import requests
from bs4 import BeautifulSoup
import json
import time

base_url = "https://legalacts.egov.kz/list"
search_url = "https://legalacts.egov.kz/application/advancedsearch"


def get_detailed_info(detail_url):
    session = requests.Session()
    try:
        response = session.get(detail_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')

            try:
                title_element = soup.find('h2')
                title = title_element.get_text(strip=True) if title_element else "Заголовок не найден"

                short_desc_element = next(
                    (small for small in soup.find_all('small') if "Краткое содержание:" in small.get_text()), None
                )
                if short_desc_element:
                    short_description = short_desc_element.get_text(strip=True).replace("Краткое содержание:", "").strip()
                else:
                    short_description = "Краткое содержание не найдено"

                type_element = next(
                    (small for small in soup.find_all('small') if "Тип НПА:" in small.get_text()), None
                )
                if type_element:
                    type_text = type_element.get_text(strip=True).replace("Тип НПА:", "").strip()
                else:
                    type_text = "Тип НПА не найден"

                text_block = soup.find('div', class_='commentable-div')
                text = text_block.get_text(strip=True, separator=" ") if text_block else "Текст не найден"

                return {
                    "title": title,
                    "short_description": short_description,
                    "type": type_text,
                    "text": text.replace("\n", "").replace("\r", ""),
                    "detail_url": detail_url
                }
            except Exception as e:
                print(f"Ошибка при парсинге содержимого страницы: {str(e)}")
                return None
        else:
            print(f"Ошибка загрузки детальной страницы: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Ошибка при выполнении запроса к {detail_url}: {str(e)}")
        return None
    except Exception as e:
        print(f"Неожиданная ошибка при обработке {detail_url}: {str(e)}")
        return None
    finally:
        session.close()


def parse_npa(search_value, begin_date=None, end_date=None, max_pages=1):
    page = 1
    data = []

    while page <= int(max_pages):
        params = {
            'searchValue': search_value,
            'page': page,
            'searchType': 'PART',
            'toXls': 0
        }
        if begin_date:
            params['createBeginDate'] = begin_date
        if end_date:
            params['createEndDate'] = end_date

        headers = {
            'Accept-Language': 'ru',
        }
        session = requests.Session()
        try:
            response = session.get(search_url, params=params, headers=headers)
            if response.status_code != 200:
                print(f"Ошибка запроса страницы {page}: {response.status_code}")
                break
            print(response.url)
            soup = BeautifulSoup(response.text, 'lxml')

            main_content = soup.find('table', class_='advanced_search_result')
            if not main_content:
                print(f"Родительский элемент 'maincontent' не найден на странице {page}.")
                break

            results = main_content.find_all('tr')
            if not results:
                print(f"На странице {page} нет карточек.")
                break
            print(f"Парсинг страницы {page}...")
            for result in results:
                link_tag = result.find('a', href=True)
                if link_tag:
                    all_tds = result.find_all("td")
                    link = link_tag['href']
                    full_link = f"https://legalacts.egov.kz{link}"
                    data.append({
                        "title": all_tds[1].get_text(strip=True),
                        "gov_body": all_tds[2].get_text(strip=True),
                        "type": all_tds[3].get_text(strip=True),
                        "detail_url": full_link,
                    })
                    #print(f"Переход по ссылке: {full_link}")
                    # detailed_info = get_detailed_info(full_link)
                    # if detailed_info:
                    #     data.append(detailed_info)

            page += 1
            #time.sleep(1)
        except:
            print('Ошибка при получении страницы в поиске')
        finally:
            session.close()
    return data
