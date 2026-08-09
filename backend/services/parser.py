from utils.parsers.botParser import OzonParser


async def get_data_by_url(url: str):
    url = url.split('?')[0]
    parser = OzonParser()
    parsed_data = await parser.parse(url)

    if parsed_data["success"]:
        return parsed_data
    else:
        raise LookupError(f"Данные url {url} не парсятся")