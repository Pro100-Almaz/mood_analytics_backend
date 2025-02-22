import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

base_url = "https://data.egov.kz"
API_KEY = "148a518f9f904eada3d3cbbbb607ef07"


def get_detailed_data(link, session):
    try:
        parsed_url = urlparse(link)
        query_params = parse_qs(parsed_url.query)
        index = query_params.get("index", [None])[0]
        if not index:
            raise ValueError("Индекс набора данных не найден в ссылке.")
        info_url = f"{base_url}/meta/{index}/v2?pretty"
        data_url = f"{base_url}/api/v4/{index}/v2"
        query_params = {"apiKey": API_KEY}
        info_response = session.get(info_url)
        info_response.raise_for_status()
        dataset_info = info_response.json()
        data_response = session.get(data_url, params=query_params)
        data_response.raise_for_status()
        dataset_data = data_response.json()
        return {"info": dataset_info, "data": dataset_data, "link": link}
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении данных: {e}")
        return None
    except ValueError as e:
        print(e)
        return None


def parse_opendata(query_value, max_pages=1):
    session = requests.Session()
    page = 1
    data = []
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru;q=0.5",
        "Connection": "keep-alive",
    })
    while page <= max_pages:
        params = {"text": query_value, 'page': page, "ok": "Искать"}

        response = session.get(base_url + "/datasets/search", params=params)
        if response.status_code != 200:
            print(response.url)
            print(f"Ошибка при загрузке страницы {page}: {response.status_code}")
            break
        soup = BeautifulSoup(response.text, 'lxml')
        tab_pane = soup.find('div', class_='content-page')
        if not tab_pane:
            print(f"Родительский элемент 'content-page' не найден на странице {page}")
            break
        cards = tab_pane.find_all('div', class_='search-result-item')
        if not cards:
            print(f"На странице {page} нет карточек")
            break

        print(f"Парсинг страницы {page}...")
        for card in cards:
            readmore_link = card.find('h4').find('a')
            if readmore_link and 'href' in readmore_link.attrs:
                link = readmore_link['href']
                print(f"Переход по ссылке: {link}")
                detailed_info = get_detailed_data(f"{base_url}{link}", session)
                if detailed_info:
                    data.append(detailed_info)
        page += 1
        time.sleep(1)
    return data
