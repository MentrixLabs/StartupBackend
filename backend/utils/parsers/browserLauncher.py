import random

from playwright.async_api import ViewportSize

from backend.utils.parsers.parserConfig import ParserConfig


class ChromeBrowserLauncher:

    @classmethod
    async def launch(cls, p, debug=ParserConfig.DEBUG_BROWSER):
        browser = await p.chromium.launch(
            headless=not debug,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--start-maximized",
                "--disable-web-security"
            ],
            slow_mo=random.randint(300, 800)
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            extra_http_headers={
                "Sec-Ch-Ua": "\"Not:A-Brand\";v=\"24\", \"Chromium\";v=\"134\""
            },
            viewport=ViewportSize({"width": 1920, "height": 1080}),
            locale="ru-RU"
        )
        return browser, context

    @classmethod
    async def shutdown(cls, browser):
        await browser.close()