import re

import requests
from bs4 import BeautifulSoup, Comment
import time

base_url = "https://budget.egov.kz/application/search"


def parse_budget(query_text, max_pages=1):
    page = 1
    data = []

    while page <= max_pages:
        params = {
            'querytext': query_text,
            'page': page,
        }
        headers = {
            'Accept-Language': 'ru',
        }
        response = requests.get(base_url, params=params, headers=headers)
        if response.status_code != 200:
            print(f"Ошибка запроса страницы {page}: {response.status_code}")
            break

        soup = BeautifulSoup(response.text, 'lxml')
        h2_tags = soup.find_all('h2')
        if not h2_tags:
            print(f"На странице {page} нет тегов <h2> с ссылками.")
            break
        for h2 in h2_tags:
            link_tag = h2.find('a', href=True)
            if link_tag:
                link = link_tag['href']
                full_link = f"https://budget.egov.kz{link}"
                print(f"Переход по ссылке: {full_link}")

                detailed_info = parse_detail_page(full_link)
                if detailed_info:
                    data.append(detailed_info)

        print(f"Парсинг страницы {page} завершен.")
        page += 1
        time.sleep(1)

    return data


def parse_block(block, title, data):
    data[title] = data.get(title, {"Подпрограммы": [],
                                   "files": []})
    table = block.find('tbody')
    data[title]['common'] = parse_table(table)
    sub_blocks = block.find_all(attrs={"id": re.compile(r"^tab-subprogram-REPORT")})
    for sub_block in sub_blocks:
        sub = sub_block.find('table')
        for input_tag in sub.find_all(['input', 'a']):
            input_tag.decompose()
        for tag in sub.find_all(True):
            tag.attrs.clear()
        sub.attrs.clear()
        for comment in sub.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        data[title]["Подпрограммы"].append(f"{sub}".replace("\n", ""))

    comment = block.find(string=lambda text: isinstance(text, Comment) and text.strip() == "filelist")
    file_table = comment.next_sibling.next_sibling.find('tbody')
    if file_table:
        files = file_table.find_all('tr')
        for file in files:
            file_content = file.find_all('td')
            data[title]["files"].append({
                "title": file_content[1].text,
                "date": file_content[2].text,
                "link": "https://budget.egov.kz" + file_content[3].find('a')['href']
            })


def parse_detail_page(url):
    headers = {
        'Accept-Language': 'ru',
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Ошибка загрузки страницы: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, 'lxml')

    title_element = soup.find('h1')
    title = title_element.get_text(strip=True) if title_element else "Заголовок не найден"

    data = {"title": title, "detail_url": url}

    project_block = soup.find('div', id="tab-PROJECT")
    if project_block:
        parse_block(project_block, "project", data)

    approved_block = soup.find('div', id="tab-APPROVED")
    if approved_block:
        parse_block(approved_block, "approved", data)

    report_block = soup.find('div', id="tab-REPORT")
    if report_block:
        parse_block(report_block, "report", data)

    egz_table = soup.find('div', {"id": "egzPlan_wrapper"})
    if egz_table:
        egz_table.find('table')
        for tag in egz_table.find_all(True):
            tag.attrs.clear()
        egz_table.attrs.clear()
        data["Сведения по пунктам плана государственных закупок"] = f"{egz_table}"
    return data


def parse_table(table):
    parsed_data = {
        "info": "",
        "Вид бюджетной программы": "",
        "Расходы по бюджетной программе": "<table><tbody>",
        "Прямые показатели": "<table><tbody>",
    }

    info_parsing = True
    program_type_parsing = False
    budget_parsing = False
    direct_parsing = False
    for child in table.children:
        if "indicatorlist" in child:
            program_type_parsing = False
            budget_parsing = True

        if "direct indicators" in child:
            parsed_data["Расходы по бюджетной программе"] += "</tbody></table>"
            budget_parsing = False
            direct_parsing = True

        if child.name == 'tr':
            cols = child.find_all('td')
            if len(cols) > 1 and info_parsing:
                key = cols[0].get_text(strip=True).replace('Комментировать', '').replace('\n', '')
                value = cols[1].get_text(strip=True).replace('Комментировать', '').replace('\n', '')
                parsed_data["info"] += f"{key}: {value}\n"
                continue

            if len(cols) > 1 and program_type_parsing:
                key = cols[0].get_text(strip=True).replace('Комментировать', '').replace('\n', '')
                value = cols[1].get_text(strip=True).replace('Комментировать', '').replace('\n', '')
                parsed_data["Вид бюджетной программы"] += f"{key}: {value} \n"
                continue

            if budget_parsing:
                for input_tag in child.find_all(['input', 'a']):
                    input_tag.decompose()
                for tag in child.find_all(True):
                    tag.attrs.clear()
                parsed_data["Расходы по бюджетной программе"] += f"{child}".replace("\n", "")

            if direct_parsing:
                for input_tag in child.find_all(['input', 'a']):
                    input_tag.decompose()
                for tag in child.find_all(True):
                    tag.attrs.clear()
                parsed_data["Прямые показатели"] += f"{child}".replace("\n", "")

            if child.text.replace('\n', '') == "Вид бюджетной программы":
                info_parsing = False
                program_type_parsing = True

    parsed_data["Прямые показатели"] += "</tbody></table>"
    return parsed_data


#parse_detail_page('https://budget.egov.kz/budgetprogram/budgetprogram?govAgencyId=3568&budgetId=2271590')
