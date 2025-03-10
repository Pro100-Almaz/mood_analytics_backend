import json
from langchain_core.output_parsers import BaseOutputParser
from pydantic import BaseModel, Field, parse_obj_as
from typing import List


class MainResponse(BaseModel):
    link: str = Field(description="ссылка на данное обращение")
    summary: str = Field(description="краткое описание данного обращения")
    relev_score: float = Field(description="оценка вероятности соответствия данного обращения")
    opinion: str = Field(description="степень положительности обращения: негативное, позитивное или нейтральное")

    def to_dict(self):
        return {
            "link": self.link,
            "summary": self.summary,
            "opinion": self.opinion,
            "relev_score": self.relev_score
        }


class OutputParser(BaseOutputParser):
    def parse(self, text: str) -> List[MainResponse]:
        try:
            parsed_data = json.loads(text)
            return [MainResponse(**item).to_dict() for item in parsed_data]
        except json.JSONDecodeError:
            return []


def format_output(data, query):
    """
    Given a list of lists (each inner list containing dictionaries with 'url' and 'short_description'),
    convert them to a single formatted string.
    """
    sections = []
    block_lines = []
    for item in data:
        description = item.get('short_description', '').replace("\n", "").replace("\r", "")
        item_str = f"URL: {item.get('url', '')}.Описание: {description}"
        block_lines.append(item_str)
    sections.append("\n".join(block_lines))

    formatted_egov_text = "\n" + ("-" * 40 + "\n").join(sections)

    prompt = f"Вот список обращений: [ {formatted_egov_text} ]"

    message_format = (
        f"Проанализируй каждый из этих обращений"
        "и составь из них один общий массив объектов с полями link и summary, "
        "а также relev_score с твоей оценкой вероятности соответствия.\n"
        "помимо этого определи степень положительности обращения: негативное, позитивное или нейтральное в поле opinion\n"
        "ВЕРНИ ТОЛЬКО РЕЗУЛЬТАТ В JSON ФОРМАТЕ, БЕЗ ПОЯСНИТЕЛЬНОГО ТЕКСТА."
        f"\nТема исследования: {query}"
    )
    print(prompt)

    final_payload = {
        "prompt": prompt,
        "message_format": message_format
    }

    return final_payload
