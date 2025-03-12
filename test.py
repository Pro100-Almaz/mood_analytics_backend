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


def analyze_law_opinions(opinions: str, model_name: str = "gpt-4") -> str:
    chat = ChatOpenAI(model_name=model_name)

    messages = [
        SystemMessage(content=(
            "Ты должен проанализировать данные, которые я тебе дам и дать результирующую и "
            "обобщающую рецензию. Данные представляют собой различные мнения людей о "
            "тех или иных правках в законе. Ты должен дать своё описание мнения населения."
            "ВСЕГДА ДАВАЙ В КОНЦЕ СВОЁ МНЕНИЕ: доминирующее мнение является отрицательным, позитивным или же нейтральным?"
        )),
        HumanMessage(content=str(opinions))
    ]

    response = chat.invoke(messages)
    return response.content

res = process_facebook(question=question, keywords=keywords, task_id=1)
print(res)