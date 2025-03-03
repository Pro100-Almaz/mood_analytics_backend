import json


def format_egov_output(data, query):
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
        f"Сделай выводы по следующему заявлению и если оно не соответствует теме иссследования: {query}\n"
        "При несоответствии пропусти его, не включая в ответ.\n"
        "Если соответствует, то сделай вывод и добавь в общий массив объект с полем link и summary, "
        "а также relev_score с твоей оценкой вероятности соответствия.\n"
        "Верни все результатаы в одном массиве для использование в PYTHON КОДЕ БЕЗ ЛИШНЕГО ТЕКСТА ТОЛЬКО СПИСОК."
        "Если не подходит не один вариант то просто верни пустой список."
    )

    final_payload = {
        "prompt": prompt,
        "message_format": message_format
    }

    return final_payload

