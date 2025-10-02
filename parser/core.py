from __future__ import annotations
import logging, random, time, os
from dataclasses import dataclass, field
from typing import Optional, List
from urllib.parse import urlparse

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .adapters import MarketKZAdapter, KrishaAdapter
from .utils import format_price

logger = logging.getLogger("scraper")
logger.setLevel(logging.INFO)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0",
]

ADAPTERS = {
    'market.kz': MarketKZAdapter(),
    'krisha.kz': KrishaAdapter(),
}

def pick_adapter(domain: str):
    # гибкий матч: поддомены тоже подхватятся
    for key in ADAPTERS:
        if key in domain:
            return ADAPTERS[key]
    return None

@dataclass
class ScrapeResult:
    items: List[dict] = field(default_factory=list)
    df: Optional[pd.DataFrame] = None
    file_csv: Optional[str] = None
    file_xlsx: Optional[str] = None

class Scraper:
    def __init__(self, verify_ssl: bool = True, base_delay=(1.1, 2.6)):
        self.verify_ssl = verify_ssl
        self.base_delay = base_delay
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        s = requests.Session()
        s.verify = self.verify_ssl
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retries)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        return s

    def _headers(self):
        return {"User-Agent": random.choice(USER_AGENTS)}

    def fetch(self, url: str, timeout: int = 15) -> Optional[bytes]:
        try:
            r = self.session.get(url, headers=self._headers(), timeout=timeout)
            r.raise_for_status()
            # анти-бан задержка
            time.sleep(random.uniform(*self.base_delay))
            return r.content
        except Exception as e:
            logger.warning(f"fetch failed: {e}")
            return None

    def scrape_url(self, url: str) -> ScrapeResult:
        domain = urlparse(url).netloc
        adapter = pick_adapter(domain)
        if not adapter:
            raise ValueError(f"Этот домен пока не поддерживается: {domain}")

        html = self.fetch(url)
        if html is None:
            raise RuntimeError("Не удалось получить страницу. Проверь ссылку/доступ/SSL.")

        items = adapter.extract(html, url)

        df = pd.DataFrame(items)
        csv_path = None
        xlsx_path = None
        if not df.empty:
            ts = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            safe_domain = domain.replace(':', '_').replace('/', '_')
            csv_path = f'export_{safe_domain}_{ts}.csv'
            xlsx_path = f'export_{safe_domain}_{ts}.xlsx'

            # сохраняем рядышком с приложением
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            try:
                df.to_excel(xlsx_path, index=False)
            except Exception:
                # openpyxl может отсутствовать — не валим весь процесс
                xlsx_path = None
        else:
            logger.info("Парсер отработал, но элементов не найдено.")

        return ScrapeResult(items=items, df=(df if not df.empty else None),
                            file_csv=csv_path, file_xlsx=xlsx_path)