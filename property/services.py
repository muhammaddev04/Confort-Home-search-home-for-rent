"""
Мантиқи тиҷоратии (business logic) марбут ба Property, ки аз views.py берун
кашида шудааст — то view-ҳо борик (thin) бимонанд ва мантиқ бе такрор дар
ҷои ягона санҷида/истифода шавад.
"""
from django.db.models import Avg

from .models import Property


AI_REPLY_LANGUAGES = {
    'tg': 'Tajik',
    'ru': 'Russian',
    'en': 'English',
}

# Калидвожаҳое, ки паёми корбарро ба филтрҳои воқеии Property мепайванданд —
# ин ба AI имкон медиҳад "дастрасии контекстӣ" ба маълумоти БОЗ ба ҷои
# додаҳои статикии frontend дошта бошад.
_CITY_KEYWORDS = ['dushanbe', 'душанбе', 'khujand', 'хуҷанд', 'худжанд', 'kulob', 'кӯлоб', 'куляб', 'bokhtar', 'бохтар']
_TYPE_KEYWORDS = {
    'apartment': ['apartment', 'квартира', 'квартираи', 'flat'],
    'house': ['house', 'ҳавлӣ', 'хонаи', 'дом', 'ҳавлигӣ'],
    'room': ['room', 'ҳуҷра', 'комната'],
}


def find_relevant_properties(user_message):
    """
    Ҷустуҷӯи сабуки калидвожа дар паёми корбар, то ба AI то 5 эълони ВОҚЕӢ
    аз БОЗ дода шавад — ба ҷои он ки AI маълумотро аз худ тахмин занад.
    """
    text = user_message.lower()
    qs = Property.objects.filter(is_available=True)

    for city in _CITY_KEYWORDS:
        if city in text:
            qs = qs.filter(city__icontains=city.split()[0][:4])
            break

    for ptype, keywords in _TYPE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            qs = qs.filter(property_type=ptype)
            break

    return qs.order_by('-created_at')[:5]


def format_properties_context(properties):
    if not properties:
        return "No matching properties were found in the database for this query."
    lines = []
    for p in properties:
        lines.append(
            f"- [ID {p.id}] {p.title} | {p.get_property_type_display()} | {p.price} TJS | "
            f"{p.rooms} rooms, {p.area} m² | {p.city or '—'}, {p.district} | "
            f"{'available' if p.is_available else 'not available'} | /property/{p.id}/"
        )
    return "\n".join(lines)


def build_ai_system_prompt(reply_lang, properties_context):
    return (
        "You are the AI assistant for a real estate platform called Comfort Home."
        "You assist users ONLY within the real estate system: properties (listings), "
        "property details, search & filters, users, favorites, images, landlord actions "
        "(if allowed). You must NOT talk about unrelated topics. Always use real database "
        "data — you are given a REAL_PROPERTIES context block below with actual current "
        "listings relevant to the user's message; base your answer on that data and never "
        "invent or assume missing information. If REAL_PROPERTIES says no matches were "
        "found, tell the user nothing matched — do not make up a listing. If multiple "
        f"results exist, summarize briefly (max 5 items). Reply ONLY in {reply_lang}, "
        "regardless of what language the user wrote in — this is a strict UI-language "
        "requirement set by the platform, not a translation request. Never mix languages "
        "in one response. Short, clear, and useful. No long explanations. No storytelling. "
        "Focus on actions and data. If user asks outside real estate, politely refuse and "
        "return to platform topic. Do not give personal opinions. Be precise and "
        "professional. When mentioning a property include: Title, Price, Location, and a "
        "short 1-2 line description. You are not a general AI — you are a domain-specific "
        "real estate assistant for Comfort Home.\n\n"
        f"REAL_PROPERTIES (current matches from the database for this query):\n{properties_context}"
    )


def get_market_valuation(prop):
    """
    Баҳодиҳии воқеии бозор: миёнаи нарх аз рӯи амволҳои ҳамон шаҳр ва ҳамон
    навъ (ба ғайр аз худи ин эълон). Агар маълумоти кофӣ набошад, market_avg
    None бармегардад — view/шаблон бояд ин ҳолатро алоҳида нишон диҳанд.

    Returns: (market_avg, market_count, market_diff_pct)
    """
    comparables = Property.objects.filter(
        city=prop.city,
        property_type=prop.property_type,
    ).exclude(pk=prop.pk)
    market_avg = comparables.aggregate(avg_price=Avg('price'))['avg_price']
    market_count = comparables.count()
    market_diff_pct = None
    if market_avg:
        market_avg = round(market_avg, 2)
        market_diff_pct = round(((prop.price - market_avg) / market_avg) * 100)
    return market_avg, market_count, market_diff_pct


def serialize_properties_for_map(propertys):
    """Барои /api/properties-map/ — рӯйхати амволҳоро ба JSON-и сабук мубаддал мекунад."""
    return [
        {
            'id': p.id,
            'title': p.title,
            'price': str(p.price),
            'city': p.city or '',
            'district': p.district or '',
            'lat': float(p.latitude),
            'lng': float(p.longitude),
            'type': p.get_property_type_display(),
            'url': f'/property/{p.id}/',
            'image': p.images.first().image.url if p.images.first() else None,
        }
        for p in propertys
    ]
