import re
from datetime import datetime
from typing import Dict, List

KZ_CITIES = [
    'Алматы','Астана','Шымкент','Караганда','Актобе','Тараз','Павлодар',
    'Усть-Каменогорск','Семей','Атырау','Костанай','Кызылорда','Актау',
    'Петропавловск','Талдыкорган','Кокшетау','Уральск'
]

CATEGORY_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    'market_kz': {
        'Электроника': ['телефон','компьютер','ноутбук','планшет','наушники'],
        'Для дома и сада': ['мебель','стол','диван','кровать','шкаф'],
        'Личные вещи': ['одежда','обувь','сумка','часы','украшения'],
        'Детям': ['игрушка','коляска','автокресло','одежда детская'],
    },
    'krisha_kz': {
        'Квартиры': ['квартира','1-комнат','2-комнат','3-комнат','студия'],
        'Дома': ['дом','коттедж','дача'],
        'Коммерческая': ['офис','магазин','склад','помещение'],
        'Участки': ['участок','земля','территория'],
        'Гаражи': ['гараж','паркинг','машиноместо']
    }
}

def now_str() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def parse_price(text: str) -> int:
    """
    Извлекает цену из произвольного текста карточки.
    1) Сначала собираем все числа (5+ знаков или группы 1 234 567).
    2) Предпочитаем те, у которых прямо рядом указана валюта (₸|тг|тенге).
    3) Если валюты нет — берём максимальное число >= 10_000 (чтобы отсечь '3 эт', '55 м²').
    Иначе возвращаем 0.
    """
    pattern = re.compile(r'(?P<num>\d{1,3}(?:[ \u00A0,]\d{3})*|\d+)\s*(?P<cur>₸|тг|тенге)?', re.IGNORECASE)
    candidates = []
    for m in pattern.finditer(text):
        raw = (
            m.group('num')
            .replace(' ', '')
            .replace('\u00A0', '')
            .replace(',', '')
        )
        if not raw.isdigit():
            continue
        val = int(raw)
        cur = m.group('cur')
        candidates.append((val, bool(cur)))

    if not candidates:
        return 0

    with_currency = [v for v, has_cur in candidates if has_cur]
    if with_currency:
        return max(with_currency)

    no_currency = [v for v, has_cur in candidates if not has_cur]
    best = max(no_currency) if no_currency else 0
    return best if best >= 10_000 else 0


def detect_city(text: str) -> str:
    for c in KZ_CITIES:
        if c in text:
            return c
    return "Не указано"

def determine_category(title: str, desc: str, site_key: str) -> str:
    text = f"{title or ''} {desc or ''}".lower()
    for cat, kws in CATEGORY_KEYWORDS.get(site_key, {}).items():
        if any(kw in text for kw in kws):
            return cat
    return "Другое"

def format_price(p: int) -> str:
    try:
        return f"{int(p):,} ₸".replace(",", " ")
    except Exception:
        return "—"
