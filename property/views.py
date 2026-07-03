from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Property, Property_Image, Favorite
from .forms import PropertyForm, PropertyImageForm
from django.http import JsonResponse
from django.db.models import Avg
import os
from django.http import JsonResponse
from groq import Groq
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Property, Favorite, Message




load_dotenv()

api_key = os.getenv("GROQ_API_KEY")


AI_RATE_LIMIT = 15
AI_RATE_WINDOW = 60  

AI_REPLY_LANGUAGES = {
    'tg': 'Tajik',
    'ru': 'Russian',
    'en': 'English',
}


_CITY_KEYWORDS = ['dushanbe', 'душанбе', 'khujand', 'хуҷанд', 'худжанд', 'kulob', 'кӯлоб', 'куляб', 'bokhtar', 'бохтар']
_TYPE_KEYWORDS = {
    'apartment': ['apartment', 'квартира', 'квартираи', 'flat'],
    'house': ['house', 'ҳавлӣ', 'хонаи', 'дом', 'ҳавлигӣ'],
    'room': ['room', 'ҳуҷра', 'комната'],
}


def _find_relevant_properties(user_message):
    
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


def _format_properties_context(properties):
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


@login_required
def ask_groq_view(request):
    if request.method != 'POST':
        return JsonResponse({'response': 'Метод пуштибонӣ намешавад.'}, status=405)

   
    from django.core.cache import cache
    cache_key = f'ai_rate_{request.user.pk}'
    request_count = cache.get(cache_key, 0)
    if request_count >= AI_RATE_LIMIT:
        return JsonResponse(
            {'response': 'Шумо занҷираи дархостҳоро зиёд кардед. Лутфан баъд аз як дақиқа кӯшиш кунед.'},
            status=429,
        )
    cache.set(cache_key, request_count + 1, timeout=AI_RATE_WINDOW)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return JsonResponse({'response': 'Хатогӣ: API Key танзим нашудааст.'}, status=500)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'response': 'Дархости нодуруст.'}, status=400)

    user_message = (data.get('message') or '').strip()
    if not user_message:
        return JsonResponse({'response': 'Лутфан паём нависед.'}, status=400)
    if len(user_message) > 2000:
        return JsonResponse({'response': 'Паём хеле дароз аст (макс. 2000 аломат).'}, status=400)

    reply_lang = AI_REPLY_LANGUAGES.get((data.get('lang') or '').lower(), 'Tajik')

    # Дастрасии контекстӣ ба БОЗ — ҷустуҷӯи воқеӣ дар асоси паёми корбар,
    # на такя ба маълумоти статикии frontend.
    relevant_properties = _find_relevant_properties(user_message)
    properties_context = _format_properties_context(relevant_properties)

    client = Groq(api_key=api_key)

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
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
                },
                {"role": "user", "content": user_message}
            ],
            model="openai/gpt-oss-120b",
        )
        return JsonResponse({'response': chat_completion.choices[0].message.content})
    except Exception:
        return JsonResponse({'response': 'Хатогӣ ҳангоми пайвастшавӣ ба AI. Лутфан баъдтар кӯшиш кунед.'}, status=502)


