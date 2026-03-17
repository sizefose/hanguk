from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from django.utils import timezone

from .models import DiscountGroup, Product


TWOPLACES = Decimal("0.01")


def _normalize_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f").rstrip("0").rstrip(".")


def format_discount_label(discount_type: str, discount_value: Decimal) -> str:
    if discount_type == DiscountGroup.DISCOUNT_PERCENT:
        return f"-{_normalize_decimal(discount_value)}%"
    return f"-{_normalize_decimal(discount_value)}\u20bd"


def apply_discount(price: Decimal, discount_type: str, discount_value: Decimal) -> Decimal:
    price = Decimal(str(price))
    discount_value = Decimal(str(discount_value))

    if discount_type == DiscountGroup.DISCOUNT_PERCENT:
        discounted = price * (Decimal("1") - (discount_value / Decimal("100")))
    else:
        discounted = price - discount_value

    if discounted < Decimal("0"):
        discounted = Decimal("0")

    return discounted.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass
class DiscountInfo:
    group_id: int
    label: str
    discounted_price: Decimal


def _active_groups(at: datetime | None = None):
    when = at or timezone.now()
    return (
        DiscountGroup.objects.filter(
            is_active=True,
            start_at__lte=when,
            end_at__gte=when,
        )
        .order_by("-updated_at", "-id")
        .prefetch_related("categories", "countries", "manual_products", "excluded_products")
    )


def build_discount_map(products: Iterable[Product], at: datetime | None = None) -> dict[int, DiscountInfo]:
    product_list = list(products)
    if not product_list:
        return {}

    product_by_id = {product.id: product for product in product_list}
    product_ids = set(product_by_id)

    discount_map: dict[int, DiscountInfo] = {}

    for group in _active_groups(at=at):
        category_ids = set(group.categories.values_list("id", flat=True))
        country_ids = set(group.countries.values_list("id", flat=True))
        manual_ids = set(group.manual_products.values_list("id", flat=True))
        excluded_ids = set(group.excluded_products.values_list("id", flat=True))

        target_ids = set()

        if category_ids and country_ids:
            for product in product_list:
                if product.category_id in category_ids and product.country_id in country_ids:
                    target_ids.add(product.id)
        elif category_ids:
            for product in product_list:
                if product.category_id in category_ids:
                    target_ids.add(product.id)
        elif country_ids:
            for product in product_list:
                if product.country_id in country_ids:
                    target_ids.add(product.id)

        target_ids.update(manual_ids & product_ids)
        target_ids.difference_update(excluded_ids)

        for product_id in target_ids:
            if product_id in discount_map:
                continue
            product = product_by_id.get(product_id)
            if not product:
                continue

            discounted = apply_discount(product.price, group.discount_type, group.discount_value)
            discount_map[product_id] = DiscountInfo(
                group_id=group.id,
                label=format_discount_label(group.discount_type, group.discount_value),
                discounted_price=discounted,
            )

    return discount_map


def choose_option_discount_badge(product_ids: list[int], discount_map: dict[int, DiscountInfo]) -> str | None:
    total = len(product_ids)
    if total == 0:
        return None

    labels = [discount_map[pid].label for pid in product_ids if pid in discount_map]
    if not labels:
        return None

    share = len(labels) / total
    if share <= 0.4:
        return None

    return Counter(labels).most_common(1)[0][0]
