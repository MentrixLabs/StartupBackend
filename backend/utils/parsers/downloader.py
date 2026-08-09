import requests

from backend.utils.parsers.parserConfig import ParserConfig


class Downloader:

    @classmethod
    async def download_file(cls, url, path):
        try:
            rs = requests.get(url, timeout=10)
            rs.raise_for_status()
            with open(path, 'wb') as f:
                f.write(rs.content)
                if ParserConfig.DEBUG_PARSING:
                    print(f'Идёт запись файла: {path}')
        except Exception as e:
            print(f"Ошибка загрузки {url}: {e}")