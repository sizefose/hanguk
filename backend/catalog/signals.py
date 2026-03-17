from django.db.models.signals import m2m_changed, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Banner, CatalogFilterSettings, Category, Country, DiscountGroup, Product


def _safe_delete_file(field_file):
    if not field_file:
        return
    file_name = field_file.name
    if not file_name:
        return
    try:
        field_file.storage.delete(file_name)
    except Exception:
        # Ignore missing files and storage-specific delete errors.
        pass


def _delete_replaced_file(model_cls, instance, field_name: str):
    if not instance.pk:
        return
    previous = model_cls.objects.filter(pk=instance.pk).only(field_name).first()
    if not previous:
        return

    previous_file = getattr(previous, field_name)
    current_file = getattr(instance, field_name)
    previous_name = previous_file.name if previous_file else None
    current_name = current_file.name if current_file else None

    if previous_name and previous_name != current_name:
        _safe_delete_file(previous_file)


@receiver(pre_save, sender=Product)
def delete_replaced_product_photo(sender, instance, **kwargs):
    _delete_replaced_file(Product, instance, "photo")


@receiver(pre_save, sender=Banner)
def delete_replaced_banner_image(sender, instance, **kwargs):
    _delete_replaced_file(Banner, instance, "image")


@receiver(pre_save, sender=Category)
def delete_replaced_category_image(sender, instance, **kwargs):
    _delete_replaced_file(Category, instance, "image")


@receiver(pre_save, sender=Country)
def delete_replaced_country_image(sender, instance, **kwargs):
    _delete_replaced_file(Country, instance, "image")


@receiver(pre_save, sender=CatalogFilterSettings)
def delete_replaced_all_categories_image(sender, instance, **kwargs):
    _delete_replaced_file(CatalogFilterSettings, instance, "all_categories_image")


@receiver(pre_save, sender=CatalogFilterSettings)
def delete_replaced_all_countries_image(sender, instance, **kwargs):
    _delete_replaced_file(CatalogFilterSettings, instance, "all_countries_image")


@receiver(post_delete, sender=Product)
def delete_product_media_files(sender, instance, **kwargs):
    _safe_delete_file(instance.photo)
    _safe_delete_file(instance.photo_thumb)


@receiver(post_delete, sender=Banner)
def delete_banner_media_files(sender, instance, **kwargs):
    _safe_delete_file(instance.image)
    _safe_delete_file(instance.image_thumb)


@receiver(post_delete, sender=Category)
def delete_category_media_files(sender, instance, **kwargs):
    _safe_delete_file(instance.image)


@receiver(post_delete, sender=Country)
def delete_country_media_files(sender, instance, **kwargs):
    _safe_delete_file(instance.image)


@receiver(post_delete, sender=CatalogFilterSettings)
def delete_filter_settings_media_files(sender, instance, **kwargs):
    _safe_delete_file(instance.all_categories_image)
    _safe_delete_file(instance.all_countries_image)


@receiver(m2m_changed, sender=DiscountGroup.categories.through)
@receiver(m2m_changed, sender=DiscountGroup.countries.through)
@receiver(m2m_changed, sender=DiscountGroup.manual_products.through)
@receiver(m2m_changed, sender=DiscountGroup.excluded_products.through)
def touch_discount_group_on_targeting_change(sender, instance, action, **kwargs):
    if action not in {"post_add", "post_remove", "post_clear"}:
        return

    DiscountGroup.objects.filter(pk=instance.pk).update(updated_at=timezone.now())
