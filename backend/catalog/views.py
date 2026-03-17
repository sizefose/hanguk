from datetime import timedelta

from rest_framework import generics
from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone

from content.models import (
    AboutTabSection,
    DEFAULT_YANDEX_MAP_SCRIPT_URL,
    HeroSection,
    PromoCard,
    SiteSettings,
)

from .discounts import build_discount_map, choose_option_discount_badge
from .models import Banner, CatalogFilterSettings, Category, Country, Product
from .serializers import (
    AboutSectionSerializer,
    BannerSerializer,
    CatalogFilterSettingsSerializer,
    HeroSectionSerializer,
    SiteSettingsSerializer,
    CountryFilterOptionSerializer,
    FilterOptionSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    PromoCardSerializer,
)


def set_no_store_cache(response: Response) -> Response:
    response["Cache-Control"] = "no-store, no-cache, max-age=0"
    return response


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            return set_no_store_cache(Response({"status": "error", "db": "down"}, status=503))
        return set_no_store_cache(Response({"status": "ok", "db": "up"}))


class CatalogPagePagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 100
    limit_query_param = "limit"
    offset_query_param = "offset"
    default_limit = 20
    max_limit = 100
    _limit_offset_paginator: LimitOffsetPagination | None = None

    def paginate_queryset(self, queryset, request, view=None):
        self._limit_offset_paginator = None
        if (
            request.query_params.get(self.limit_query_param) is not None
            or request.query_params.get(self.offset_query_param) is not None
        ):
            paginator = LimitOffsetPagination()
            paginator.default_limit = self.default_limit
            paginator.max_limit = self.max_limit
            paginator.limit_query_param = self.limit_query_param
            paginator.offset_query_param = self.offset_query_param
            self._limit_offset_paginator = paginator
            return paginator.paginate_queryset(queryset, request, view=view)
        return super().paginate_queryset(queryset, request, view=view)

    def get_paginated_response(self, data):
        if self._limit_offset_paginator is not None:
            return self._limit_offset_paginator.get_paginated_response(data)
        return super().get_paginated_response(data)


def get_site_settings_snapshot() -> tuple[bool, int]:
    try:
        settings = SiteSettings.objects.only("hide_prices", "new_badge_days").first()
    except (ProgrammingError, OperationalError):
        return False, 0
    if not settings:
        return False, 0
    days = int(settings.new_badge_days or 0)
    return bool(settings.hide_prices), max(days, 0)


def get_effective_new_products_qs(new_badge_days: int):
    if new_badge_days <= 0:
        return Product.objects.none()
    cutoff = timezone.now() - timedelta(days=new_badge_days)
    return Product.objects.filter(is_new=True, new_marked_at__gte=cutoff)


class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    pagination_class = CatalogPagePagination

    def get_queryset(self):
        queryset = Product.objects.select_related("category", "country")
        hide_prices, new_badge_days = get_site_settings_snapshot()
        self.hide_prices = hide_prices
        self.new_badge_days = new_badge_days
        category = self.request.query_params.getlist("category")
        country = self.request.query_params.getlist("country")
        is_new = self.request.query_params.get("is_new")
        price_min = self.request.query_params.get("min_price")
        price_max = self.request.query_params.get("max_price")
        query = (self.request.query_params.get("q") or "").strip()

        if category:
            queryset = queryset.filter(category__slug__in=category)
        if country:
            queryset = queryset.filter(country__slug__in=country)
        if is_new in {"true", "1"}:
            queryset = queryset.filter(
                id__in=get_effective_new_products_qs(new_badge_days).values_list("id", flat=True)
            )
        if price_min and not hide_prices:
            queryset = queryset.filter(price__gte=price_min)
        if price_max and not hide_prices:
            queryset = queryset.filter(price__lte=price_max)
        if query:
            queryset = queryset.filter(title__icontains=query)

        sort = self.request.query_params.get("sort")
        if sort == "price_asc" and not hide_prices:
            queryset = queryset.order_by("price")
        elif sort == "price_desc" and not hide_prices:
            queryset = queryset.order_by("-price")
        elif sort == "new":
            queryset = queryset.order_by("-created_at")

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        hide_prices = bool(getattr(self, "hide_prices", False))
        new_badge_days = int(getattr(self, "new_badge_days", 0) or 0)

        page = self.paginate_queryset(queryset)
        if page is not None:
            discount_map = {} if hide_prices else build_discount_map(page)
            serializer = self.get_serializer(
                page,
                many=True,
                context={
                    **self.get_serializer_context(),
                    "discount_map": discount_map,
                    "hide_prices": hide_prices,
                    "new_badge_days": new_badge_days,
                },
            )
            return set_no_store_cache(self.get_paginated_response(serializer.data))

        products = list(queryset)
        discount_map = {} if hide_prices else build_discount_map(products)
        serializer = self.get_serializer(
            products,
            many=True,
            context={
                **self.get_serializer_context(),
                "discount_map": discount_map,
                "hide_prices": hide_prices,
                "new_badge_days": new_badge_days,
            },
        )
        return set_no_store_cache(Response(serializer.data))


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"
    queryset = Product.objects.select_related("category", "country")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        hide_prices, new_badge_days = get_site_settings_snapshot()
        discount_map = {} if hide_prices else build_discount_map([instance])
        serializer = self.get_serializer(
            instance,
            context={
                **self.get_serializer_context(),
                "discount_map": discount_map,
                "hide_prices": hide_prices,
                "new_badge_days": new_badge_days,
            },
        )
        return set_no_store_cache(Response(serializer.data))


class BannerListView(generics.ListAPIView):
    serializer_class = BannerSerializer
    pagination_class = None
    queryset = Banner.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        return set_no_store_cache(super().list(request, *args, **kwargs))


class PromoCardListView(APIView):
    def get(self, request):
        hide_prices, new_badge_days = get_site_settings_snapshot()
        cards = list(
            PromoCard.objects.filter(is_active=True)
            .order_by("sort_order", "id")
            .prefetch_related("products__category", "products__country")
        )
        new_products_cache = list(
            get_effective_new_products_qs(new_badge_days).select_related("category", "country")
        )
        response_data = []

        for card in cards:
            base = PromoCardSerializer(card).data
            scenario = base.get("scenario")
            products = []

            if scenario == PromoCard.SCENARIO_LIST:
                products = list(card.products.all())
            elif scenario == PromoCard.SCENARIO_NEW:
                products = new_products_cache

            if scenario in {PromoCard.SCENARIO_LIST, PromoCard.SCENARIO_NEW} and not products:
                continue

            if products:
                discount_map = {} if hide_prices else build_discount_map(products)
                base["products"] = ProductListSerializer(
                    products,
                    many=True,
                    context={
                        "discount_map": discount_map,
                        "hide_prices": hide_prices,
                        "new_badge_days": new_badge_days,
                    },
                ).data
            else:
                base["products"] = []

            response_data.append(base)

        return set_no_store_cache(Response(response_data))


class AboutSectionView(APIView):
    def get(self, request):
        generic_sections = list(
            AboutTabSection.objects.filter(
                section_type=AboutTabSection.SECTION_GENERIC,
                is_active=True,
            )
            .order_by("sort_order", "id")[:3]
        )
        location_section = (
            AboutTabSection.objects.filter(section_type=AboutTabSection.SECTION_LOCATION)
            .order_by("id")
            .first()
        )

        if location_section:
            sections = [*generic_sections, location_section]
            return set_no_store_cache(
                Response({"sections": AboutSectionSerializer(sections, many=True).data})
            )

        if generic_sections:
            return set_no_store_cache(
                Response({"sections": AboutSectionSerializer(generic_sections, many=True).data})
            )

        return set_no_store_cache(
            Response(
                {
                    "sections": [
                        {
                            "id": 0,
                            "title": "Расположение",
                            "slug": "location",
                            "description": "",
                            "image": None,
                            "section_type": "location",
                            "map_script_url": DEFAULT_YANDEX_MAP_SCRIPT_URL,
                            "sort_order": 0,
                            "is_active": True,
                        }
                    ]
                }
            )
        )


class HeroSectionView(APIView):
    def get(self, request):
        hero = HeroSection.objects.first()
        if not hero:
            return set_no_store_cache(Response({"description": "", "image": None}))
        return set_no_store_cache(Response(HeroSectionSerializer(hero).data))


class SiteSettingsView(APIView):
    def get(self, request):
        try:
            settings = SiteSettings.objects.first() or SiteSettings()
        except (ProgrammingError, OperationalError):
            settings = SiteSettings()
        return set_no_store_cache(Response(SiteSettingsSerializer(settings).data))


class FilterOptionsView(APIView):
    def get(self, request):
        hide_prices, _ = get_site_settings_snapshot()
        selected_categories = set(request.query_params.getlist("category"))
        selected_countries = set(request.query_params.getlist("country"))

        categories_qs = Category.objects.order_by("title")
        countries_qs = Country.objects.order_by("title")

        products_for_categories = Product.objects.all()
        if selected_countries:
            products_for_categories = products_for_categories.filter(country__slug__in=selected_countries)
        enabled_category_ids = set(products_for_categories.values_list("category_id", flat=True).distinct())

        products_for_countries = Product.objects.all()
        if selected_categories:
            products_for_countries = products_for_countries.filter(category__slug__in=selected_categories)
        enabled_country_ids = set(products_for_countries.values_list("country_id", flat=True).distinct())

        products_for_category_badges = list(products_for_categories.select_related("category", "country"))
        products_for_country_badges = list(products_for_countries.select_related("category", "country"))

        category_discount_map = {} if hide_prices else build_discount_map(products_for_category_badges)
        country_discount_map = {} if hide_prices else build_discount_map(products_for_country_badges)

        category_product_ids: dict[int, list[int]] = {}
        for product in products_for_category_badges:
            category_product_ids.setdefault(product.category_id, []).append(product.id)

        country_product_ids: dict[int, list[int]] = {}
        for product in products_for_country_badges:
            country_product_ids.setdefault(product.country_id, []).append(product.id)

        category_badges = {
            category_id: choose_option_discount_badge(ids, category_discount_map)
            for category_id, ids in category_product_ids.items()
        }
        country_badges = {
            country_id: choose_option_discount_badge(ids, country_discount_map)
            for country_id, ids in country_product_ids.items()
        }

        categories_data = FilterOptionSerializer(
            categories_qs,
            many=True,
            context={
                "enabled_ids": enabled_category_ids,
                "selected_slugs": selected_categories,
                "discount_badges": category_badges,
                "hide_prices": hide_prices,
            },
        ).data

        countries_data = CountryFilterOptionSerializer(
            countries_qs,
            many=True,
            context={
                "enabled_ids": enabled_country_ids,
                "selected_slugs": selected_countries,
                "discount_badges": country_badges,
                "hide_prices": hide_prices,
            },
        ).data

        settings = CatalogFilterSettings.objects.first()
        settings_data = CatalogFilterSettingsSerializer(settings).data if settings else {
            "all_categories_image": None,
            "all_countries_image": None,
        }

        response = Response(
            {
                "categories": categories_data,
                "countries": countries_data,
                "all_categories_image": settings_data["all_categories_image"],
                "all_countries_image": settings_data["all_countries_image"],
            }
        )
        return set_no_store_cache(response)
