from __future__ import annotations
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .utils import parse_price, detect_city, determine_category, now_str


class BaseAdapter:
    site_key = 'base'

    def extract(self, html: bytes, page_url: str) -> list[dict]:
        """Верни список словарей (одна запись = одно объявление)."""
        raise NotImplementedError


# ---------- market.kz ----------
class MarketKZAdapter(BaseAdapter):
    site_key = 'market_kz'

    def extract(self, html: bytes, page_url: str) -> list[dict]:
        soup = BeautifulSoup(html, 'lxml')
        items: list[dict] = []

        cards = soup.select('.a-card, .ads-list-item, .product-card')
        if cards:
            for c in cards:
                title_el = c.select_one('a[title], .a-card__title, h2, h3')
                title = title_el.get_text(" ", strip=True) if title_el else None
                if not title:
                    title = c.get_text(" ", strip=True)[:120]

                text_all = c.get_text(" ", strip=True)
                price = parse_price(text_all)
                if price <= 0:
                    continue
                location = detect_city(text_all)

                desc_el = c.select_one('.a-card__description, .desc, p')
                desc = desc_el.get_text(" ", strip=True) if desc_el else title

                a = c.select_one('a[href]')
                href = a['href'] if a and a.has_attr('href') else None
                url = urljoin(page_url, href) if href else "N/A"

                items.append({
                    'marketplace': 'market.kz',
                    'category': determine_category(title, desc, self.site_key),
                    'title': title,
                    'price': price,
                    'description': (desc[:200] + '...') if len(desc) > 200 else desc,
                    'seller': 'Не указан',
                    'location': location,
                    'date_posted': 'Не указано',
                    'url': url,
                    'scraped_at': now_str()
                })
            return items

        text = soup.get_text("\n", strip=True)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for i, line in enumerate(lines):
            if len(line) < 6:
                continue
            block = " ".join(lines[i:i + 5])
            price = parse_price(block)
            if price <= 0:
                continue
            location = detect_city(block)
            desc = " ".join(lines[max(0, i - 1):i + 2])
            items.append({
                'marketplace': 'market.kz',
                'category': determine_category(line, desc, self.site_key),
                'title': line[:140],
                'price': price,
                'description': (desc[:200] + '...') if len(desc) > 200 else desc,
                'seller': 'Не указан',
                'location': location,
                'date_posted': 'Не указано',
                'url': "N/A",
                'scraped_at': now_str()
            })
        return items


# ---------- krisha.kz ----------
class KrishaAdapter(BaseAdapter):
    site_key = 'krisha_kz'

    def extract(self, html: bytes, page_url: str) -> list[dict]:
        soup = BeautifulSoup(html, 'lxml')
        items: list[dict] = []

        cards = soup.select(".a-card, .a-card__inc, .card--listing")
        for c in cards:
            title_el = c.select_one('.a-card__title, a[title], h3, h2')
            title = title_el.get_text(" ", strip=True) if title_el else ""

            # --- цена ---
            price_el = c.select_one(
                '.a-card__price, .a-card__price ~ span, .card__price, .price, [data-price]'
            )
            if price_el:
                price_text = price_el.get_text(" ", strip=True)
            else:
                price_text = c.get_text(" ", strip=True)

            price = parse_price(price_text)
            if price <= 0:
                a_price = c.select_one('a[href][title]')
                if a_price:
                    price = parse_price(a_price.get_text(" ", strip=True))
            if price <= 0:
                continue

            # --- прочее ---
            text_all = c.get_text(" ", strip=True)
            location = detect_city(text_all)

            desc_el = c.select_one('.a-card__description, .desc, p')
            desc = desc_el.get_text(" ", strip=True) if desc_el else title

            a = c.select_one('a[href]')
            href = a['href'] if a and a.has_attr('href') else None
            url = urljoin(page_url, href) if href else "N/A"

            items.append({
                'marketplace': 'krisha.kz',
                'category': determine_category(title, desc, self.site_key),
                'title': title,
                'price': price,
                'description': (desc[:200] + '...') if len(desc) > 200 else desc,
                'seller': 'Не указан',
                'location': location,
                'date_posted': 'Не указано',
                'url': url,
                'scraped_at': now_str()
            })

        return items