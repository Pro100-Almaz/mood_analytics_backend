import time
import requests
from bs4 import BeautifulSoup

base_url = "https://adilet.zan.kz/rus/search/docs/"


def parse_adilet(query, begin_date=None, max_pages=1):
    page = 1
    headers = {'Accept-Language': 'ru'}
    data = []
    total_parsed = 0  # Counter to track the number of collected elements

    while page <= int(max_pages) and total_parsed < 5:  # Stop if 5 elements are collected
        params = {"fulltext": query, 'page': page, "st": "new"}
        if begin_date:
            params['dt'] = begin_date
        session = requests.Session()

        try:
            response = session.get(base_url, headers=headers, params=params)
            print(response.url)
            if response.status_code != 200:
                print(f"Ошибка запроса страницы {page}: {response.status_code}")
                break

            soup = BeautifulSoup(response.text, 'lxml')
            posts = soup.find_all('div', {"class": "post_holder"})
            if not posts:
                break

            for post in posts:
                if total_parsed >= 5:  # Stop collecting after 5 items
                    break

                link_tag = post.find('a', href=True)
                if link_tag:
                    link = "https://adilet.zan.kz" + link_tag['href']
                    data.append({
                        "title": post.find('h4').get_text(strip=True),
                        "subtitle": post.find('p').get_text(strip=True),
                        "detail_url": link
                    })
                    total_parsed += 1  # Increment counter

            page += 1
        except Exception as e:
            print(f"Ошибка при получении страницы: {e}")
        finally:
            session.close()

    return data


# Example usage
results = parse_adilet("налоговый кодекс", max_pages=3)
print(results)
