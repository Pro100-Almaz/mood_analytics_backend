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

class ProcessStatus(Enum):
    ERROR = 'Error'
    SUCCESS = 'Success'
    INFO = 'Info'


def process_egov_opendata(question, keywords, task_id, max_pages):
    try:
        result = []
        for query in keywords:
            parsing_result = parse_opendata(query, max_pages=max_pages)
            for record in parsing_result:
                result.append({
                    'url': record['link'],
                    'short_description': record['info']['descriptionKk'],
                })

                if len(result) >= 5:
                    break

            if len(result) >= 5:
                break


        summary = process_data_from_ai(result, question)

        if summary['status'] == 'success':
            summary["all"] = result
            del summary["status"]
            with connect(**DB_CONFIG) as conn:
                with conn.cursor() as cursor:
                    query = sql.SQL(
                        "INSERT INTO {} (task_id, data) VALUES (%s, %s)"
                    ).format(sql.Identifier("egov_opendata"))

                    cursor.execute(query, (task_id, Json(summary.get('assistant_reply', {"Error": "Empty result!"}))))
                    conn.commit()

            return {"status": "success", "response": summary}

        return {"status": "error", "response": summary}
    except Exception as e:
        track_error(str(e), 'egov_opendata', ProcessStatus.ERROR)
        return {"status": "error"}

res = process_egov_opendata(question, keywords, 1, 1)
print(res)