from datetime import timedelta

from rest_framework import serializers
from django.utils import timezone
from django.db.utils import OperationalError, ProgrammingError

from content.models import AboutTabSection, HeroSection, PromoCard, SiteSettings

from .discounts import DiscountInfo

from .models import (
    Banner,
    CatalogFilterSettings,
    Category,
    Country,
    Product,
)


class ProductSerializer(serializers.ModelSerializer):
    category_title = serializers.CharField(source="category.title", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    category_image = serializers.ImageField(source="category.image", read_only=True)
    country_title = serializers.CharField(source="country.title", read_only=True)
    country_slug = serializers.CharField(source="country.slug", read_only=True)
    country_image = serializers.ImageField(source="country.image", read_only=True)

    original_price = serializers.DecimalField(source="price", max_digits=10, decimal_places=2, read_only=True)
    discounted_price = serializers.SerializerMethodField()
    has_discount = serializers.SerializerMethodField()
    discount_label = serializers.SerializerMethodField()
    is_new = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "ingredients",
            "preparation",
            "serving",
            "photo",
            "photo_thumb",
            "price",
            "original_price",
            "discounted_price",
            "has_discount",
            "discount_label",
            "spicy",
            "is_new",
            "category",
            "country",
            "category_title",
            "category_slug",
            "category_image",
            "country_title",
            "country_slug",
            "country_image",
        )

    def _discount_info(self, obj) -> DiscountInfo | None:
        discount_map = self.context.get("discount_map") or {}
        return discount_map.get(obj.id)

    def _hide_prices(self) -> bool:
        return bool(self.context.get("hide_prices"))

    def get_discounted_price(self, obj):
        if self._hide_prices():
            return None
        info = self._discount_info(obj)
        return info.discounted_price if info else None

    def get_has_discount(self, obj):
        if self._hide_prices():
            return False
        return self._discount_info(obj) is not None

    def get_discount_label(self, obj):
        if self._hide_prices():
            return None
        info = self._discount_info(obj)
        return info.label if info else None

    def get_is_new(self, obj):
        if not obj.is_new or not obj.new_marked_at:
            return False
        days = int(self.context.get("new_badge_days", 0) or 0)
        if days <= 0:
            return False
        cutoff = timezone.now() - timedelta(days=days)
        return obj.new_marked_at >= cutoff


class ProductListSerializer(ProductSerializer):
    """Lean payload for catalog cards and promo grids."""

    class Meta(ProductSerializer.Meta):
        fields = (
            "id",
            "title",
            "slug",
            "photo",
            "photo_thumb",
            "price",
            "original_price",
            "discounted_price",
            "has_discount",
            "discount_label",
            "spicy",
            "is_new",
            "category_title",
            "category_slug",
            "country_title",
            "country_slug",
        )


class ProductDetailSerializer(ProductSerializer):
    """Detail serializer split is explicit to simplify future divergence."""


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = (
            "id",
            "title",
            "description",
            "image",
            "image_thumb",
            "background_image",
            "background_color",
            "background_opacity",
            "link_url",
            "is_active",
        )


class PromoCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCard
        fields = (
            "id",
            "image",
            "scenario",
            "link_url",
            "sort_order",
        )


class FilterOptionSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    enabled = serializers.SerializerMethodField()
    selected = serializers.SerializerMethodField()
    discount_badge = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "title", "slug", "image", "enabled", "selected", "discount_badge")

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def get_enabled(self, obj):
        enabled_ids = self.context.get("enabled_ids", set())
        return obj.id in enabled_ids

    def get_selected(self, obj):
        selected_slugs = self.context.get("selected_slugs", set())
        return obj.slug in selected_slugs

    def get_discount_badge(self, obj):
        if self.context.get("hide_prices"):
            return None
        badges = self.context.get("discount_badges", {})
        return badges.get(obj.id)


class CountryFilterOptionSerializer(FilterOptionSerializer):
    class Meta:
        model = Country
        fields = ("id", "title", "slug", "image", "enabled", "selected", "discount_badge")


class CatalogFilterSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogFilterSettings
        fields = ("all_categories_image", "all_countries_image")


class AboutSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutTabSection
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "image",
            "section_type",
            "map_script_url",
            "sort_order",
            "is_active",
        )


class HeroSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroSection
        fields = (
            "description",
            "image",
        )


class SiteSettingsSerializer(serializers.ModelSerializer):
    order_phone_display = serializers.SerializerMethodField()
    order_phone_link = serializers.SerializerMethodField()
    addresses = serializers.SerializerMethodField()
    contacts = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()
    stores = serializers.SerializerMethodField()
    default_category_slugs = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = (
            "header_action_label",
            "header_action_url",
            "telegram_button_label",
            "telegram_button_url",
            "order_phone_display",
            "order_phone_link",
            "addresses",
            "contacts",
            "social_links",
            "stores",
            "maker_label",
            "maker_url",
            "legal_text",
            "new_badge_days",
            "hide_prices",
            "default_category_slugs",
        )

    def get_default_category_slugs(self, obj):
        try:
            if not obj.pk:
                return []
            return list(
                obj.default_categories.order_by("title").values_list("slug", flat=True)
            )
        except (ProgrammingError, OperationalError, ValueError):
            return []

    def _store_rows(self, obj):
        try:
            dynamic_items = (
                list(
                    obj.store_contacts.filter(is_active=True)
                    .order_by("sort_order", "id")
                    .values("address", "phone")
                )
                if obj.pk
                else []
            )
        except (ProgrammingError, OperationalError, ValueError):
            dynamic_items = []

        if dynamic_items:
            return dynamic_items

        try:
            legacy_addresses = (
                list(
                    obj.footer_addresses.filter(is_active=True)
                    .order_by("sort_order", "id")
                    .values_list("title", flat=True)
                )
                if obj.pk
                else []
            )
            legacy_phones = (
                list(
                    obj.footer_phones.filter(is_active=True)
                    .order_by("sort_order", "id")
                    .values_list("title", "phone_link")
                )
                if obj.pk
                else []
            )
        except (ProgrammingError, OperationalError, ValueError):
            legacy_addresses = []
            legacy_phones = []

        if legacy_addresses or legacy_phones:
            rows = []
            max_len = max(len(legacy_addresses), len(legacy_phones))
            for index in range(max_len):
                address = legacy_addresses[index] if index < len(legacy_addresses) else ""
                phone_title, phone_link = legacy_phones[index] if index < len(legacy_phones) else ("", "")
                phone = phone_title or phone_link
                if address or phone:
                    rows.append({"address": address, "phone": phone})
            if rows:
                return rows

        return [
            {"address": obj.address_1_text, "phone": obj.contact_1_display},
            {"address": obj.address_2_text, "phone": obj.contact_2_display},
            {"address": obj.address_3_text, "phone": obj.contact_3_display},
        ]

    def get_order_phone_display(self, obj):
        rows = self._store_rows(obj)
        for row in rows:
            phone = (row.get("phone") or "").strip()
            if phone:
                return phone
        return obj.order_phone_display

    def get_order_phone_link(self, obj):
        display = self.get_order_phone_display(obj)
        return display or obj.order_phone_link

    def get_addresses(self, obj):
        return [
            {"text": row["address"], "url": ""}
            for row in self._store_rows(obj)
            if (row.get("address") or "").strip()
        ]

    def get_contacts(self, obj):
        return [
            {"text": row["phone"], "href": row["phone"]}
            for row in self._store_rows(obj)
            if (row.get("phone") or "").strip()
        ]

    def get_social_links(self, obj):
        items = [
            {"platform": "vk", "url": obj.social_vk_url},
            {"platform": "whatsapp", "url": obj.social_whatsapp_url},
            {"platform": "telegram", "url": obj.social_telegram_url},
        ]
        return [item for item in items if item["url"]]

    def get_stores(self, obj):
        try:
            stores = (
                obj.store_contacts.filter(is_active=True)
                .order_by("sort_order", "id")
            )
        except (ProgrammingError, OperationalError, ValueError):
            stores = []

        items = []
        for store in stores:
            deliveries = [
                {
                    "id": delivery.id,
                    "service_type": delivery.service_type,
                    "service_url": delivery.service_url,
                    "map_script_url": delivery.map_script_url,
                }
                for delivery in store.deliveries.filter(is_active=True).order_by("sort_order", "id")
            ]
            items.append(
                {
                    "id": store.id,
                    "name": store.name,
                    "address": store.address,
                    "phone": store.phone,
                    "deliveries": deliveries,
                }
            )
        if items:
            return items

        fallback_rows = self._store_rows(obj)
        result = []
        for index, row in enumerate(fallback_rows, start=1):
            address = (row.get("address") or "").strip()
            phone = (row.get("phone") or "").strip()
            if not (address or phone):
                continue
            result.append(
                {
                    "id": -index,
                    "name": f"Магазин {index}",
                    "address": address,
                    "phone": phone,
                    "deliveries": [],
                }
            )
        return result
