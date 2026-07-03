"""
Сигналҳои Property — рафтори "паҳлӯӣ" (side effect: логкунӣ) аз view/model
дур карда шудааст, то мантиқ ҳар ҷое ки объект сохта/нест мешавад (аз view,
admin, шелл ё скрипт) якхела кор кунад.
"""
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Property

logger = logging.getLogger('property')


@receiver(post_save, sender=Property)
def log_property_saved(sender, instance, created, **kwargs):
    action = 'сохта шуд' if created else 'нав карда шуд'
    logger.info('Амвол #%s "%s" (соҳиб: %s) %s.', instance.pk, instance.title, instance.owner_id, action)


@receiver(post_delete, sender=Property)
def log_property_deleted(sender, instance, **kwargs):
    logger.info('Амвол #%s "%s" (соҳиб: %s) нест карда шуд.', instance.pk, instance.title, instance.owner_id)
