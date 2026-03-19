import os
import re
import uuid

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.utils import OperationalError, ProgrammingError
from django.http import HttpResponseRedirect
from django.utils import timezone

from .discounts import apply_discount, format_discount_label
from .models import CatalogFilterSettings, Category, Country, DiscountGroup, Product

admin.site.site_header = "Управление Hanguk.market"
admin.site.site_title = "Управление Hanguk.market"
admin.site.index_title = "Управление Hanguk.market"
admin.site.empty_value_display = "Не выбрано"

_original_get_app_list = admin.site.get_app_list


class DiscountGroupAdminForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Категории",
    )
    countries = forms.ModelMultipleChoiceField(
        queryset=Country.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Страны",
    )

    start_at_local = forms.DateTimeField(
        required=False,
        input_formats=["%d:%m:%Y %H:%M"],
        help_text="Формат: ДД:ММ:ГГГГ ЧЧ:ММ",
        label="Начало скидки",
    )
    end_at_local = forms.DateTimeField(
        required=False,
        input_formats=["%d:%m:%Y %H:%M"],
        help_text="Формат: ДД:ММ:ГГГГ ЧЧ:ММ",
        label="Конец скидки",
    )

    class Meta:
        model = DiscountGroup
        fields = (
            "name",
            "is_active",
            "discount_type",
            "discount_value",
            "categories",
            "countries",
            "manual_products",
            "excluded_products",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["categories"].queryset = Category.objects.order_by("title")
        self.fields["countries"].queryset = Country.objects.order_by("title")

        self.fields["categories"].widget.attrs["class"] = "discount-checkboxes"
        self.fields["countries"].widget.attrs["class"] = "discount-checkboxes"

        if self.instance and self.instance.pk:
            local_start = timezone.localtime(self.instance.start_at)
            local_end = timezone.localtime(self.instance.end_at)
            self.initial["start_at_local"] = local_start.strftime("%d:%m:%Y %H:%M")
            self.initial["end_at_local"] = local_end.strftime("%d:%m:%Y %H:%M")

    def clean(self):
        cleaned = super().clean()

        start_local = cleaned.get("start_at_local")
        end_local = cleaned.get("end_at_local")

        if start_local:
            cleaned["start_at"] = (
                timezone.make_aware(start_local)
                if timezone.is_naive(start_local)
                else start_local
            )
        if end_local:
            cleaned["end_at"] = (
                timezone.make_aware(end_local)
                if timezone.is_naive(end_local)
                else end_local
            )

        start_at = cleaned.get("start_at")
        end_at = cleaned.get("end_at")
        discount_type = cleaned.get("discount_type")
        discount_value = cleaned.get("discount_value")

        if not start_at or not end_at:
            raise ValidationError("Нужно заполнить начало и конец действия скидки.")

        if end_at <= start_at:
            raise ValidationError("Конец скидки должен быть позже начала.")

        if discount_value is None or discount_value <= 0:
            raise ValidationError("Размер скидки должен быть больше 0.")

        if discount_type == DiscountGroup.DISCOUNT_PERCENT and discount_value > 100:
            raise ValidationError("Процент скидки не может быть больше 100%.")

        categories = cleaned.get("categories")
        countries = cleaned.get("countries")
        manual_products = cleaned.get("manual_products")
        excluded_products = cleaned.get("excluded_products")

        has_categories = categories is not None and categories.exists()
        has_countries = countries is not None and countries.exists()

        if has_categories and has_countries:
            target_qs = Product.objects.filter(category__in=categories, country__in=countries)
        elif has_categories:
            target_qs = Product.objects.filter(category__in=categories)
        elif has_countries:
            target_qs = Product.objects.filter(country__in=countries)
        else:
            target_qs = Product.objects.none()

        if manual_products is not None and manual_products.exists():
            target_qs = target_qs | manual_products

        target_qs = target_qs.distinct()

        if excluded_products is not None and excluded_products.exists():
            target_qs = target_qs.exclude(pk__in=excluded_products.values_list("pk", flat=True))

        target_qs = target_qs.select_related("category", "country")

        if not target_qs.exists():
            raise ValidationError(
                "После применения фильтров нет товаров в группе. Добавьте товары или снимите исключения."
            )

        if discount_type == DiscountGroup.DISCOUNT_FIXED:
            too_low = [
                product.title
                for product in target_qs
                if apply_discount(product.price, discount_type, discount_value) == 0
                and product.price < discount_value
            ]
            if too_low:
                sample = ", ".join(too_low[:5])
                more = "" if len(too_low) <= 5 else f" и еще {len(too_low) - 5}"
                raise ValidationError(
                    f"Скидка в рублях слишком большая для товаров: {sample}{more}. "
                    "Исключите эти товары или задайте для них меньшую скидку."
                )

        target_ids = set(target_qs.values_list("id", flat=True))

        overlap_groups = DiscountGroup.objects.filter(is_active=True).exclude(pk=self.instance.pk)
        overlap_groups = overlap_groups.filter(start_at__lt=end_at, end_at__gt=start_at)
        overlap_groups = overlap_groups.prefetch_related(
            "categories", "countries", "manual_products", "excluded_products"
        )

        for group in overlap_groups:
            other_ids = group.get_effective_product_ids()
            conflicts = target_ids & other_ids
            if not conflicts:
                continue

            conflict_titles = list(
                Product.objects.filter(id__in=conflicts).values_list("title", flat=True)[:5]
            )
            sample = ", ".join(conflict_titles)
            more_count = len(conflicts) - len(conflict_titles)
            more = "" if more_count <= 0 else f" и еще {more_count}"
            raise ValidationError(
                f"Невозможно создать скидочную группу: товары ({sample}{more}) уже включены в "
                f"другую группу '{group.name}'."
            )

        return cleaned


def _next_clone_title(base_title: str) -> str:
    pattern = re.compile(rf"^{re.escape(base_title)} \((\d+)\)$")
    max_index = 0

    for title in Product.objects.filter(title__startswith=base_title).values_list("title", flat=True):
        match = pattern.match(title)
        if match:
            max_index = max(max_index, int(match.group(1)))

    return f"{base_title} ({max_index + 1})"


def _clone_photo(source_photo):
    if not source_photo:
        return None

    source_photo.open("rb")
    data = source_photo.read()
    source_photo.close()

    base_name = os.path.basename(source_photo.name)
    stem, ext = os.path.splitext(base_name)
    return f"{stem}-clone-{uuid.uuid4().hex[:8]}{ext}", ContentFile(data)


def clone_products(modeladmin, request, queryset):
    created_count = 0

    for product in queryset.select_related("category", "country"):
        clone = Product(
            category=product.category,
            country=product.country,
            title=_next_clone_title(product.title),
            slug="",
            description=product.description,
            ingredients=product.ingredients,
            preparation=product.preparation,
            serving=product.serving,
            price=product.price,
            spicy=product.spicy,
            is_new=product.is_new,
        )

        photo_payload = _clone_photo(product.photo)
        if photo_payload:
            file_name, content = photo_payload
            clone.photo.save(file_name, content, save=False)

        clone.save()
        created_count += 1

    modeladmin.message_user(request, f"Создано копий товаров: {created_count}")


clone_products.short_description = "Клонировать выбранные товары"



def _ordered_get_app_list(request, app_label=None):
    app_list = _original_get_app_list(request, app_label)

    for app in app_list:
        app_label_value = app.get("app_label")
        if app_label_value == "catalog":
            model_order = {
                "Category": 10,
                "Country": 20,
                "Product": 30,
                "DiscountGroup": 40,
            }
            app["models"].sort(
                key=lambda model: (
                    model_order.get(model.get("object_name"), 999),
                    model.get("name", ""),
                )
            )
            continue

        if app_label_value == "content":
            model_order = {
                "HeroSection": 10,
                "ContentBanner": 20,
                "PromoCard": 30,
                "AboutTabSection": 40,
                "SiteSettings": 50,
            }
            display_names = {
                "HeroSection": "Hero",
                "PromoCard": "Карточки",
            }
            for model in app["models"]:
                object_name = model.get("object_name")
                if object_name in display_names:
                    model["name"] = display_names[object_name]
            app["models"].sort(
                key=lambda model: (
                    model_order.get(model.get("object_name"), 999),
                    model.get("name", ""),
                )
            )

    return app_list


admin.site.get_app_list = _ordered_get_app_list


def _load_filter_settings() -> CatalogFilterSettings | None:
    try:
        return CatalogFilterSettings.objects.first()
    except (ProgrammingError, OperationalError):
        return None


def _save_filter_settings_field(*, field_name: str, image):
    settings = _load_filter_settings() or CatalogFilterSettings(pk=1)
    setattr(settings, field_name, image)
    if settings._state.adding:
        settings.save()
    else:
        settings.save(update_fields=[field_name])


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    change_list_template = "admin/catalog/category/change_list.html"
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title",)

    def changelist_view(self, request, extra_context=None):
        if request.method == "POST" and "_set_reset_filter_icon" in request.POST:
            if request.POST.get("clear_reset_filter_icon") == "1":
                _save_filter_settings_field(field_name="all_categories_image", image=None)
                self.message_user(request, "Иконка сброса категорий очищена.")
            else:
                image = request.FILES.get("reset_filter_icon")
                if image is None:
                    self.message_user(request, "Выберите файл иконки.")
                else:
                    _save_filter_settings_field(
                        field_name="all_categories_image",
                        image=image,
                    )
                    self.message_user(request, "Иконка сброса категорий сохранена.")
            return HttpResponseRedirect(request.path)

        settings = _load_filter_settings()
        extra_context = {
            **(extra_context or {}),
            "reset_filter_icon_label": "Иконка для пункта «Все категории»",
            "reset_filter_icon_help": "Иконка для пункта «Все категории».",
            "reset_filter_icon_value": settings.all_categories_image if settings else None,
            "reset_filter_icon_action": request.path,
            "reset_filter_icon_submit": "Сохранить иконку",
            "add_button_label": "Добавить категорию",
        }
        return super().changelist_view(request, extra_context=extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = {**(extra_context or {}), "title": "Добавить категорию"}
        return super().add_view(request, form_url, extra_context)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    change_list_template = "admin/catalog/country/change_list.html"
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title",)

    def changelist_view(self, request, extra_context=None):
        if request.method == "POST" and "_set_reset_filter_icon" in request.POST:
            if request.POST.get("clear_reset_filter_icon") == "1":
                _save_filter_settings_field(field_name="all_countries_image", image=None)
                self.message_user(request, "Иконка сброса стран очищена.")
            else:
                image = request.FILES.get("reset_filter_icon")
                if image is None:
                    self.message_user(request, "Выберите файл иконки.")
                else:
                    _save_filter_settings_field(
                        field_name="all_countries_image",
                        image=image,
                    )
                    self.message_user(request, "Иконка сброса стран сохранена.")
            return HttpResponseRedirect(request.path)

        settings = _load_filter_settings()
        extra_context = {
            **(extra_context or {}),
            "reset_filter_icon_label": "Иконка для пункта «Все страны»",
            "reset_filter_icon_help": "Иконка для пункта «Все страны».",
            "reset_filter_icon_value": settings.all_countries_image if settings else None,
            "reset_filter_icon_action": request.path,
            "reset_filter_icon_submit": "Сохранить иконку",
            "add_button_label": "Добавить страну",
        }
        return super().changelist_view(request, extra_context=extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = {**(extra_context or {}), "title": "Добавить страну"}
        return super().add_view(request, form_url, extra_context)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    actions = (clone_products,)
    list_display = (
        "title",
        "category",
        "country",
        "price",
        "spicy",
        "is_new",
    )
    list_filter = ("category", "country", "is_new")
    search_fields = ("title", "description", "ingredients")
    prepopulated_fields = {"slug": ("title",)}
    exclude = ("photo_thumb", "new_marked_at")


@admin.register(DiscountGroup)
class DiscountGroupAdmin(admin.ModelAdmin):
    form = DiscountGroupAdminForm
    class Media:
        css = {
            "all": ("catalog/admin/discountgroup.css",),
        }

    list_display = (
        "name",
        "discount_preview",
        "start_at",
        "end_at",
        "is_active",
    )
    list_filter = ("is_active", "discount_type")
    search_fields = ("name",)
    autocomplete_fields = ("manual_products", "excluded_products")

    fieldsets = (
        (
            "Группа",
            {
                "fields": (
                    "name",
                    "is_active",
                    ("start_at_local", "end_at_local"),
                    ("discount_type", "discount_value"),
                )
            },
        ),
        (
            "Таргетинг",
            {
                "description": (
                    "Сначала выберите категории/страны. Затем вручную добавьте/уберите товары."
                ),
                "fields": (
                    "categories",
                    "countries",
                    "manual_products",
                    "excluded_products",
                ),
            },
        ),
    )


    def save_model(self, request, obj, form, change):
        obj.start_at = form.cleaned_data["start_at"]
        obj.end_at = form.cleaned_data["end_at"]
        super().save_model(request, obj, form, change)

    @admin.display(description="Скидка")
    def discount_preview(self, obj: DiscountGroup):
        return format_discount_label(obj.discount_type, obj.discount_value)


@admin.register(CatalogFilterSettings)
class CatalogFilterSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "all_categories_image",
                    "all_countries_image",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        try:
            return not CatalogFilterSettings.objects.exists()
        except (ProgrammingError, OperationalError):
            return True

    def has_delete_permission(self, request, obj=None):
        return False

    def get_model_perms(self, request):
        return {}
