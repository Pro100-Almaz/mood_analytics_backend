import time
import requests
from bs4 import BeautifulSoup

base_url = "https://adilet.zan.kz/rus/search/docs/"


def parse_adilet(query, begin_date=None, max_pages=1):
    page = 1
    headers = {
        'Accept-Language': 'ru',
    }
    data = []
    while page <= int(max_pages):
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
                link_tag = post.find('a', href=True)
                if link_tag:
                    link = "https://adilet.zan.kz" + link_tag['href']
                    data.append({
                        "title": post.find('h4').get_text(strip=True),
                        "subtitle": post.find('p').get_text(strip=True),
                        "detail_url": link
                    })
                    # detailed_info = parse_detail_adilet(link)
                    # if detailed_info:
                    #     data.append(detailed_info)
            page += 1
            #time.sleep(1)
        except:
            print("Ошибка при получении страницы")
        finally:
            session.close()
    return data


def parse_detail_adilet(url):
    headers = {
        'Accept-Language': 'ru',
    }
    session = requests.Session()
    try:
        response = session.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Ошибка загрузки страницы: {response.status_code}")
            return None
        soup = BeautifulSoup(response.text, 'lxml')
        header = soup.find("div", {"class": "slogan"})
        if header:
            title_element = header.find('h1')
            title = title_element.get_text(strip=True) if title_element else "Заголовок не найден"
            status_el = header.find('span', {"class": "status"})
            status = status_el.get_text(strip=True) if status_el else "Статус не найден"
            info = header.find('p').get_text(strip=True)

        article = soup.find("article")
        article.attrs.clear()
        print(url)
        text = ""
        for child in article.children:
            if child.name == 'table':
                for tag in child.find_all(True):
                    tag.attrs.clear()
                text += f"\n{child.prettify()}\n"
            elif child.name:
                child_text = child.get_text()
                child_text = " ".join(child_text.split())
                text += f"{child_text}\n"

        data = {
            "title": title,
            "status": status,
            "info": info,
            "text": text,
            "detail_url": url
        }
        response = requests.get(f"{url}/info", headers=headers)
        soup = BeautifulSoup(response.text, 'lxml')
        table = soup.find('table', id='ethernatable')
        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) == 2:
                key = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)
                data[key] = value
        return data
    except:
        print("Ошибка при получении детальной страницы адилет")
    finally:
        session.close()



