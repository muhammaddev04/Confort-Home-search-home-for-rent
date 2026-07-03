"""
Mixin-ҳои такроршавандаи CBV — сохта шудаанд то мантиқи такрории view-ҳои
Property/Property_Image/Favorite (санҷиши нақш, маҳдудияти соҳиб, таъини
соҳиб ҳангоми сохтан) дар ҷои ягона бошад.
"""
from django.shortcuts import redirect


class RoleRequiredMixin:
    """
    Танҳо ба корбароне иҷозат медиҳад, ки нақшашон дар `allowed_roles` бошад
    (масалан landlord/admin); дигарон ба `redirect_url_name` равона мешаванд.
    Бояд ҳамеша ҳамроҳи LoginRequiredMixin истифода шавад (аввал он меояд),
    то `request.user` аллакай воридшуда бошад.
    """
    allowed_roles = ()
    redirect_url_name = 'home'

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in self.allowed_roles:
            return redirect(self.redirect_url_name)
        return super().dispatch(request, *args, **kwargs)


class OwnerQuerysetMixin:
    """Queryset-ро танҳо ба объектҳои соҳиби ҷории воридшуда маҳдуд мекунад."""
    owner_field = 'owner'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(**{self.owner_field: self.request.user})


class SetOwnerOnCreateMixin:
    """Ҳангоми сохтани объекти нав (CreateView), соҳибро ба корбари ҷорӣ таъин мекунад."""
    owner_field = 'owner'

    def form_valid(self, form):
        setattr(form.instance, self.owner_field, self.request.user)
        return super().form_valid(form)
