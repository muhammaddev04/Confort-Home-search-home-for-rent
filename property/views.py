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

