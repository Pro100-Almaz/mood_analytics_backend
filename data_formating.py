import json


def format_egov_output(data, query):
    """
    Given a list of lists (each inner list containing dictionaries with 'url' and 'short_description'),
    convert them to a single formatted string.
    """
    sections = []
    for section in data:
        if not section:
            continue
        block_lines = []
        for item in section:
            item_str = f"URL: {item.get('url', '')}\nОписание: {item.get('short_description', '')}"
            block_lines.append(item_str)
        sections.append("\n\n".join(block_lines))

    formatted_egov_text = "\n\n" + ("-" * 40 + "\n\n").join(sections)

    prompt = f"Вот список обращений: [ {formatted_egov_text} ]"

    message_format = (
        f"Сделай выводы по следующему заявлению и если оно не соответствует теме иссследования: {query}\n\n"
        "При несоответствии пропусти его, не включая в ответ.\n\n"
        "Если соответствует, то сделай вывод и добавь в общий массив объект с полем link и summary, "
        "а также relev_score с твоей оценкой вероятности соответствия.\n\n"
        "Верни все результатаы в одном массиве для использование в Python коде без лишнего текста только список."
    )

    final_payload = {
        "prompt": prompt,
        "message_format": message_format
    }

    return final_payload

