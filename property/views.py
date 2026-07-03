import json
import os

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView
from dotenv import load_dotenv
from groq import Groq

from . import services
from .forms import PropertyForm, PropertyImageForm
from .mixins import OwnerQuerysetMixin, RoleRequiredMixin, SetOwnerOnCreateMixin
from .models import Favorite, Message, Property, Property_Image

load_dotenv()


AI_RATE_LIMIT = 15
AI_RATE_WINDOW = 60  
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
api_key=GROQ_API_KEY




@login_required
def ask_groq_view(request):
    if request.method != 'POST':
        return JsonResponse({'response': 'Метод пуштибонӣ намешавад.'}, status=405)

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

    reply_lang = services.AI_REPLY_LANGUAGES.get((data.get('lang') or '').lower(), 'Tajik')
    relevant_properties = services.find_relevant_properties(user_message)
    properties_context = services.format_properties_context(relevant_properties)
    system_prompt = services.build_ai_system_prompt(reply_lang, properties_context)

    client = Groq(api_key=api_key)
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            model="openai/gpt-oss-120b",
        )
        return JsonResponse({'response': chat_completion.choices[0].message.content})
    except Exception:
        return JsonResponse({'response': 'Хатогӣ ҳангоми пайвастшавӣ ба AI. Лутфан баъдтар кӯшиш кунед.'}, status=502)


def properties_map_data(request):
    
    propertys = Property.objects.filter(
        is_available=True,
        latitude__isnull=False,
        longitude__isnull=False,
    ).select_related('owner')[:200]
    return JsonResponse({'properties': services.serialize_properties_for_map(propertys)})




class HomeView(ListView):
    model = Property
    template_name = 'home.html'
    context_object_name = 'propertys'

    def get_queryset(self):
        qs = Property.objects.all()
        city = self.request.GET.get('q')
        if city and isinstance(city, str):
            qs = qs.filter(city__icontains=city.strip())
        district = self.request.GET.get('qu')
        if district and isinstance(district, str):
            qs = qs.filter(district__icontains=district.strip())
        min_price = self.request.GET.get('min_price')
        if min_price:
            qs = qs.filter(price__gte=min_price)
        max_price = self.request.GET.get('max_price')
        if max_price:
            qs = qs.filter(price__lte=max_price)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['favorite_property_ids'] = Favorite.objects.filter(
                user=self.request.user
            ).values_list('property_id', flat=True)
        else:
            context['favorite_property_ids'] = []
        return context


class AboutView(LoginRequiredMixin, TemplateView):
    template_name = 'about.html'


class PropertySearchView(LoginRequiredMixin, ListView):
    
    model = Property
    template_name = 'property_search.html'
    context_object_name = 'propertys'

    def get_queryset(self):
        qs = Property.objects.filter(is_available=True)

        city = (self.request.GET.get('city') or '').strip()
        if city:
            qs = qs.filter(city__icontains=city)

        district = (self.request.GET.get('district') or '').strip()
        if district:
            qs = qs.filter(district__icontains=district)

        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price and max_price:
            qs = qs.filter(price__range=(min_price, max_price))
        elif min_price:
            qs = qs.filter(price__gte=min_price)
        elif max_price:
            qs = qs.filter(price__lte=max_price)

        property_type = self.request.GET.get('property_type')
        if property_type:
            qs = qs.filter(property_type=property_type)

        return qs.order_by('-created_at')


class PropertyDetailView(DetailView):
    """Кушода барои ҳама (анонимӣ низ) — фақат амалҳои интерактивӣ вуруд металабанд."""
    model = Property
    template_name = 'property_detail.html'
    context_object_name = 'property'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user.is_authenticated and 'send_message' in request.POST:
            content = (request.POST.get('content') or '').strip()
            if content:
                Message.objects.create(
                    sender=request.user,
                    receiver=self.object.owner,
                    property=self.object,
                    content=content,
                )
        return redirect('property_detail', pk=self.object.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        prop = self.object
        is_favorited = False
        messages_qs = []

        if self.request.user.is_authenticated:
            is_favorited = Favorite.objects.filter(user=self.request.user, property=prop).exists()
            messages_qs = Message.objects.filter(property=prop).filter(
                Q(sender=self.request.user) | Q(receiver=self.request.user)
            ).order_by('timestamp')

        market_avg, market_count, market_diff_pct = services.get_market_valuation(prop)
        context.update({
            'is_favorited': is_favorited,
            'messages': messages_qs,
            'market_avg': market_avg,
            'market_count': market_count,
            'market_diff_pct': market_diff_pct,
        })
        return context




class PropertyListView(LoginRequiredMixin, RoleRequiredMixin, OwnerQuerysetMixin, ListView):
    model = Property
    allowed_roles = ('landlord', 'admin')
    template_name = 'property_search.html'
    context_object_name = 'propertys'

    def get_queryset(self):
        qs = super().get_queryset()
        city = self.request.GET.get('q')
        if city and isinstance(city, str):
            qs = qs.filter(city__icontains=city.strip())
        district = self.request.GET.get('qu')
        if district and isinstance(district, str):
            qs = qs.filter(district__icontains=district.strip())
        return qs


class PropertyCreateView(LoginRequiredMixin, RoleRequiredMixin, SetOwnerOnCreateMixin, CreateView):
    model = Property
    form_class = PropertyForm
    allowed_roles = ('landlord', 'admin')
    template_name = 'property_form.html'
    success_url = reverse_lazy('property_list')


class PropertyUpdateView(LoginRequiredMixin, OwnerQuerysetMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = 'property_form.html'
    context_object_name = 'property'
    success_url = reverse_lazy('property_list')


class PropertyDeleteView(LoginRequiredMixin, OwnerQuerysetMixin, DeleteView):
    model = Property
    template_name = 'property_confirm_delete.html'
    context_object_name = 'property'
    success_url = reverse_lazy('property_list')




class PropertyImageListView(LoginRequiredMixin, ListView):
    model = Property_Image
    template_name = 'propertyimage_list.html'
    context_object_name = 'propertyimages'

    def get_queryset(self):
        qs = Property_Image.objects.filter(property__owner=self.request.user)
        query = self.request.GET.get('q')
        if isinstance(query, str) and query.strip():
            qs = qs.filter(property__title__icontains=query.strip())
        return qs


class PropertyImageFormMixin:
    
    model = Property_Image
    form_class = PropertyImageForm
    success_url = reverse_lazy('propertyimages_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['propertys'] = Property.objects.filter(owner=self.request.user)
        return context

    def form_valid(self, form):
        prop = get_object_or_404(Property, pk=form.cleaned_data['property'].pk, owner=self.request.user)
        form.instance.property = prop
        return super().form_valid(form)


class PropertyImageCreateView(LoginRequiredMixin, RoleRequiredMixin, PropertyImageFormMixin, CreateView):
    allowed_roles = ('landlord', 'admin')
    template_name = 'propertyimage_form.html'


class PropertyImageUpdateView(LoginRequiredMixin, PropertyImageFormMixin, UpdateView):
    template_name = 'update_propertyimages.html'

    def get_queryset(self):
        return Property_Image.objects.filter(property__owner=self.request.user)


class PropertyImageDeleteView(LoginRequiredMixin, DeleteView):
    model = Property_Image
    template_name = 'delete_propertyimages.html'
    success_url = reverse_lazy('propertyimages_list')

    def get_queryset(self):
        return Property_Image.objects.filter(property__owner=self.request.user)



class FavoriteListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Favorite
    allowed_roles = ('tenant', 'admin')
    template_name = 'favorites_list.html'

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related('property')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['favorite_properties'] = [fav.property for fav in self.object_list]
        return context


@login_required
def toggle_favorite(request, pk):
    if request.method == 'POST':
        property_obj = get_object_or_404(Property, pk=pk)
        favorite, created = Favorite.objects.get_or_create(user=request.user, property=property_obj)

        if not created:
            favorite.delete()
            status = 'removed'
        else:
            status = 'added'

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': status})

        return redirect(request.META.get('HTTP_REFERER', 'home'))

    return redirect('home')


class FavoriteDeleteView(LoginRequiredMixin, DeleteView):
    model = Favorite
    template_name = 'delete_favorites.html'
    success_url = reverse_lazy('favorite_list')

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)


class LandlordDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/landlord_dashboard.html'
