from django import forms
from django.contrib import admin, messages
from django.db import connection
from django.db.models import Max
from django.db.utils import OperationalError, ProgrammingError
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join

from catalog.models import Category

from .models import (
    MAX_ABOUT_GENERIC_SECTIONS,
    AboutTabSection,
    ContentBanner,
    HeroSection,
    PromoCard,
    SiteSettings,
    StoreContact,
    StoreDelivery,
)


def _fallback_changelist_url(request: HttpRequest, admin_name: str) -> str:
    return request.META.get("HTTP_REFERER") or reverse(admin_name)


def _swap_sort_order(first_obj, second_obj, direction: str):
    first_order = first_obj.sort_order
    second_order = second_obj.sort_order

    if first_order == second_order:
        if direction == "up":
            first_obj.sort_order = second_order if second_order == 0 else second_order - 1
            second_obj.sort_order = second_order + 1
        else:
            first_obj.sort_order = second_order + 1
            second_obj.sort_order = second_order if second_order == 0 else second_order - 1
    else:
        first_obj.sort_order = second_order
        second_obj.sort_order = first_order

    first_obj.save(update_fields=["sort_order"])
    second_obj.save(update_fields=["sort_order"])


def _normalize_store_order(settings: SiteSettings):
    stores = list(settings.store_contacts.order_by("sort_order", "id"))
    for index, store in enumerate(stores, start=1):
        if store.sort_order == index:
            continue
        store.sort_order = index
        store.save(update_fields=["sort_order"])


def _default_categories_field_available() -> bool:
    try:
        through_table = SiteSettings.default_categories.through._meta.db_table
        return through_table in connection.introspection.table_names()
    except (ProgrammingError, OperationalError):
        return False


class StoreDeliveryInline(admin.TabularInline):
    model = StoreDelivery
    extra = 0
    fields = (
        "service_type",
        "service_url",
        "map_script_url",
        "sort_order",
        "is_active",
    )
    ordering = ("sort_order", "id")


class SiteSettingsAdminForm(forms.ModelForm):
    new_store_name = forms.CharField(
        required=False,
        label="Добавить магазин",
        help_text="Введите внутреннее название и сохраните настройки.",
    )

    class Meta:
        model = SiteSettings
        fields = "__all__"
        widgets = {
            "social_vk_url": forms.URLInput(attrs={"class": "vURLField"}),
            "social_whatsapp_url": forms.URLInput(attrs={"class": "vURLField"}),
            "social_telegram_url": forms.URLInput(attrs={"class": "vURLField"}),
        }
        labels = {
            "social_vk_url": "VK",
            "social_whatsapp_url": "Номер WhatsApp",
            "social_telegram_url": "Telegram канал",
            "legal_text": "",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["legal_text"].help_text = ""
        self.fields["new_store_name"].widget.attrs["placeholder"] = "Например: Северный"
        if "default_categories" not in self.fields:
            return
        if _default_categories_field_available():
            self.fields["default_categories"].queryset = Category.objects.order_by("title")
            self.fields["default_categories"].label = "Категории по умолчанию"
            self.fields["default_categories"].help_text = (
                "Выбираются автоматически при первом посещении каталога."
            )
            self.fields["default_categories"].required = False
            checkbox_widget = forms.CheckboxSelectMultiple()
            checkbox_widget.choices = self.fields["default_categories"].choices
            self.fields["default_categories"].widget = checkbox_widget
        else:
            self.fields.pop("default_categories", None)


@admin.register(ContentBanner)
class ContentBannerAdmin(admin.ModelAdmin):
    list_display = ("title", "sort_order", "link_url", "is_active", "move_controls")
    list_editable = ("sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "description")
    ordering = ("sort_order", "id")
    exclude = ("image_thumb",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "description",
                    "sort_order",
                    "image",
                    "background_image",
                    ("background_color", "background_opacity"),
                    "link_url",
                    "is_active",
                )
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/move/<str:direction>/",
                self.admin_site.admin_view(self.move_banner),
                name="content_contentbanner_move",
            ),
        ]
        return custom_urls + urls

    def move_banner(self, request: HttpRequest, object_id: int, direction: str):
        changelist_url = _fallback_changelist_url(
            request,
            "admin:content_contentbanner_changelist",
        )
        banner = self.get_object(request, object_id)
        if not banner:
            self.message_user(request, "Баннер не найден.", level=messages.ERROR)
            return HttpResponseRedirect(changelist_url)

        queryset = ContentBanner.objects.order_by("sort_order", "id")
        if direction == "up":
            target = (
                queryset.filter(sort_order__lt=banner.sort_order)
                .order_by("-sort_order", "-id")
                .first()
            )
            if not target:
                target = queryset.filter(sort_order=banner.sort_order, id__lt=banner.id).order_by("-id").first()
        else:
            target = queryset.filter(sort_order__gt=banner.sort_order).order_by("sort_order", "id").first()
            if not target:
                target = queryset.filter(sort_order=banner.sort_order, id__gt=banner.id).order_by("id").first()

        if not target:
            self.message_user(request, "Элемент уже на крайней позиции.", level=messages.INFO)
            return HttpResponseRedirect(changelist_url)

        _swap_sort_order(banner, target, direction)
        self.message_user(request, "Порядок баннеров обновлен.", level=messages.SUCCESS)
        return HttpResponseRedirect(changelist_url)

    @admin.display(description="Позиция")
    def move_controls(self, obj: ContentBanner):
        up_url = reverse("admin:content_contentbanner_move", args=[obj.pk, "up"])
        down_url = reverse("admin:content_contentbanner_move", args=[obj.pk, "down"])
        return format_html(
            '<a href="{}" style="padding-right:8px;">↑ выше</a>'
            '<a href="{}">↓ ниже</a>',
            up_url,
            down_url,
        )


@admin.register(AboutTabSection)
class AboutTabSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "section_type", "sort_order", "is_active", "move_controls")
    list_filter = ("section_type", "is_active")
    search_fields = ("title", "description")
    ordering = ("sort_order", "id")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/move/<str:direction>/",
                self.admin_site.admin_view(self.move_section),
                name="content_abouttabsection_move",
            ),
        ]
        return custom_urls + urls

    def move_section(self, request: HttpRequest, object_id: int, direction: str):
        changelist_url = _fallback_changelist_url(
            request,
            "admin:content_abouttabsection_changelist",
        )
        section = self.get_object(request, object_id)
        if not section:
            self.message_user(request, "Раздел не найден.", level=messages.ERROR)
            return HttpResponseRedirect(changelist_url)

        if section.section_type == AboutTabSection.SECTION_LOCATION:
            self.message_user(
                request,
                "Раздел 'Расположение' зафиксирован и не перемещается.",
                level=messages.INFO,
            )
            return HttpResponseRedirect(changelist_url)

        queryset = AboutTabSection.objects.filter(
            section_type=AboutTabSection.SECTION_GENERIC
        ).order_by("sort_order", "id")
        if direction == "up":
            target = (
                queryset.filter(sort_order__lt=section.sort_order)
                .order_by("-sort_order", "-id")
                .first()
            )
            if not target:
                target = queryset.filter(sort_order=section.sort_order, id__lt=section.id).order_by("-id").first()
        else:
            target = queryset.filter(sort_order__gt=section.sort_order).order_by("sort_order", "id").first()
            if not target:
                target = queryset.filter(sort_order=section.sort_order, id__gt=section.id).order_by("id").first()

        if not target:
            self.message_user(request, "Элемент уже на крайней позиции.", level=messages.INFO)
            return HttpResponseRedirect(changelist_url)

        _swap_sort_order(section, target, direction)
        self.message_user(request, "Порядок разделов обновлен.", level=messages.SUCCESS)
        return HttpResponseRedirect(changelist_url)

    @admin.display(description="Позиция")
    def move_controls(self, obj: AboutTabSection):
        if obj.section_type == AboutTabSection.SECTION_LOCATION:
            return "Не выбрано"
        up_url = reverse("admin:content_abouttabsection_move", args=[obj.pk, "up"])
        down_url = reverse("admin:content_abouttabsection_move", args=[obj.pk, "down"])
        return format_html(
            '<a href="{}" style="padding-right:8px;">↑ выше</a>'
            '<a href="{}">↓ ниже</a>',
            up_url,
            down_url,
        )

    def has_add_permission(self, request):
        if not super().has_add_permission(request):
            return False
        try:
            generic_count = AboutTabSection.objects.filter(
                section_type=AboutTabSection.SECTION_GENERIC
            ).count()
        except (ProgrammingError, OperationalError):
            # Table can be absent before migrations are applied.
            return True
        return generic_count < MAX_ABOUT_GENERIC_SECTIONS

    def get_fields(self, request, obj=None):
        if obj and obj.section_type == AboutTabSection.SECTION_LOCATION:
            return ["description"]

        fields = [
            "title",
            "slug",
            "section_type",
            "description",
            "image",
            "map_script_url",
            "sort_order",
            "is_active",
        ]
        if obj and obj.section_type == AboutTabSection.SECTION_LOCATION:
            fields.remove("image")
        return fields

    def get_prepopulated_fields(self, request, obj=None):
        if obj and obj.section_type == AboutTabSection.SECTION_LOCATION:
            return {}
        return {"slug": ("title",)}

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.section_type == AboutTabSection.SECTION_LOCATION:
            return (
                "title",
                "slug",
                "section_type",
                "image",
                "map_script_url",
                "sort_order",
                "is_active",
            )
        return ()

    def has_delete_permission(self, request, obj=None):
        if obj and obj.section_type == AboutTabSection.SECTION_LOCATION:
            return False
        return super().has_delete_permission(request, obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(HeroSection)
class HeroSectionAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "description",
                    "image",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        try:
            return not HeroSection.objects.exists()
        except (ProgrammingError, OperationalError):
            # Table can be absent before migrations are applied.
            return True

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        try:
            hero = HeroSection.objects.only("pk").first()
        except (ProgrammingError, OperationalError):
            hero = None

        if hero is not None:
            change_url = reverse("admin:content_herosection_change", args=[hero.pk])
            return HttpResponseRedirect(change_url)

        return super().changelist_view(request, extra_context=extra_context)


@admin.register(StoreContact)
class StoreContactAdmin(admin.ModelAdmin):
    inlines = (StoreDeliveryInline,)
    list_display = ("name", "address", "phone", "is_active")
    list_editable = ("is_active",)
    search_fields = ("name", "address", "phone")
    ordering = ("sort_order", "id")
    fields = ("name", "address", "phone", "is_active")

    def get_model_perms(self, request):
        # Навигация к магазинам идет из страницы настроек.
        return {}


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    form = SiteSettingsAdminForm
    readonly_fields = ("stores_links", "default_categories_status")
    fieldsets = (
        (
            "Каталог",
            {
                "fields": ("hide_prices", "new_badge_days", "default_categories"),
            },
        ),
        ("Ссылки", {"fields": (("social_vk_url", "social_whatsapp_url", "social_telegram_url"),)}),
        (
            "Legal",
            {
                "fields": ("legal_text",),
            },
        ),
        (
            "Магазины",
            {
                "fields": ("stores_links", "new_store_name"),
            },
        ),
    )
    exclude = (
        "address_1_text",
        "address_1_url",
        "address_2_text",
        "address_2_url",
        "address_3_text",
        "address_3_url",
        "contact_1_display",
        "contact_1_link",
        "contact_2_display",
        "contact_2_link",
        "contact_3_display",
        "contact_3_link",
        "maker_label",
        "maker_url",
        "header_action_label",
        "header_action_url",
        "telegram_button_label",
        "telegram_button_url",
        "order_phone_display",
        "order_phone_link",
    )

    def has_add_permission(self, request):
        try:
            return not SiteSettings.objects.exists()
        except (ProgrammingError, OperationalError):
            return True

    def has_delete_permission(self, request, obj=None):
        return False

    def get_form(self, request, obj=None, change=False, **kwargs):
        exclude = list(kwargs.get("exclude") or ())
        exclude.extend(self.get_readonly_fields(request, obj))
        if not _default_categories_field_available() and "default_categories" not in exclude:
            exclude.append("default_categories")
        kwargs["exclude"] = tuple(dict.fromkeys(exclude))
        return super().get_form(request, obj=obj, change=change, **kwargs)

    def get_fieldsets(self, request, obj=None):
        base_fieldsets = list(super().get_fieldsets(request, obj))
        if _default_categories_field_available():
            return base_fieldsets

        normalized: list[tuple[str, dict]] = []
        for title, options in base_fieldsets:
            fields = list(options.get("fields", ()))
            replaced_fields = tuple(
                "default_categories_status" if field == "default_categories" else field
                for field in fields
            )
            normalized.append((title, {**options, "fields": replaced_fields}))
        return normalized

    @admin.display(description="Категории по умолчанию")
    def default_categories_status(self, obj: SiteSettings):
        return (
            "Недоступно: не применена миграция для связи категорий по умолчанию. "
            "Примените миграции backend и обновите страницу."
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/store/<int:store_id>/move/<str:direction>/",
                self.admin_site.admin_view(self.move_store),
                name="content_sitesettings_store_move",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        try:
            settings = SiteSettings.objects.only("pk").first()
        except (ProgrammingError, OperationalError):
            settings = None

        if settings is not None:
            change_url = reverse("admin:content_sitesettings_change", args=[settings.pk])
            return HttpResponseRedirect(change_url)

        return super().changelist_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)
        if obj is not None and not obj.store_contacts.exists():
            obj.save()
        if obj is not None:
            _normalize_store_order(obj)
        return super().change_view(request, object_id, form_url, extra_context)

    def move_store(self, request: HttpRequest, object_id: int, store_id: int, direction: str):
        change_url = reverse("admin:content_sitesettings_change", args=[object_id])
        settings = self.get_object(request, object_id)
        if not settings:
            self.message_user(request, "Настройки не найдены.", level=messages.ERROR)
            return HttpResponseRedirect(change_url)

        queryset = settings.store_contacts.order_by("sort_order", "id")
        store = queryset.filter(pk=store_id).first()
        if not store:
            self.message_user(request, "Магазин не найден.", level=messages.ERROR)
            return HttpResponseRedirect(change_url)

        if direction == "up":
            target = queryset.filter(sort_order__lt=store.sort_order).order_by("-sort_order", "-id").first()
            if not target:
                target = queryset.filter(sort_order=store.sort_order, id__lt=store.id).order_by("-id").first()
        else:
            target = queryset.filter(sort_order__gt=store.sort_order).order_by("sort_order", "id").first()
            if not target:
                target = queryset.filter(sort_order=store.sort_order, id__gt=store.id).order_by("id").first()

        if not target:
            self.message_user(request, "Элемент уже на крайней позиции.", level=messages.INFO)
            return HttpResponseRedirect(change_url)

        _swap_sort_order(store, target, direction)
        _normalize_store_order(settings)
        self.message_user(request, "Порядок магазинов обновлен.", level=messages.SUCCESS)
        return HttpResponseRedirect(change_url)

    @admin.display(description="Список магазинов")
    def stores_links(self, obj: SiteSettings):
        stores = obj.store_contacts.order_by("sort_order", "id")
        if not stores.exists():
            return "Не выбрано"

        return format_html_join(
            format_html("<br>"),
            '<a href="{}">{}</a> <a href="{}" style="padding-left:8px;">↑ выше</a> <a href="{}">↓ ниже</a>',
            (
                (
                    reverse("admin:content_storecontact_change", args=[store.pk]),
                    store.name or f"Магазин #{store.pk}",
                    reverse("admin:content_sitesettings_store_move", args=[obj.pk, store.pk, "up"]),
                    reverse("admin:content_sitesettings_store_move", args=[obj.pk, store.pk, "down"]),
                )
                for store in stores
            ),
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        new_store_name = (form.cleaned_data.get("new_store_name") or "").strip()
        if not new_store_name:
            return

        max_sort = obj.store_contacts.aggregate(max_sort=Max("sort_order"))["max_sort"] or 0
        obj.store_contacts.create(
            name=new_store_name,
            address="",
            phone="",
            sort_order=max_sort + 1,
            is_active=True,
        )
        _normalize_store_order(obj)


class PromoCardAdminForm(forms.ModelForm):
    class Meta:
        model = PromoCard
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        scenario = cleaned.get("scenario")
        link_url = (cleaned.get("link_url") or "").strip()
        products = cleaned.get("products")

        if scenario == PromoCard.SCENARIO_LINK and not link_url:
            self.add_error("link_url", "Укажите ссылку для сценария 'Ссылка'.")

        if scenario == PromoCard.SCENARIO_LIST and (products is None or not products.exists()):
            self.add_error("products", "Выберите хотя бы один товар для сценария 'Список'.")

        return cleaned


@admin.register(PromoCard)
class PromoCardAdmin(admin.ModelAdmin):
    form = PromoCardAdminForm
    list_display = ("id", "scenario", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    list_filter = ("scenario", "is_active")
    ordering = ("sort_order", "id")
    autocomplete_fields = ("products",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "image",
                    "scenario",
                    "link_url",
                    "products",
                    "sort_order",
                    "is_active",
                )
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if obj.scenario != PromoCard.SCENARIO_LINK:
            obj.link_url = ""
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        if obj.scenario != PromoCard.SCENARIO_LIST:
            obj.products.clear()
