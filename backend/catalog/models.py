from io import BytesIO

from django.core.files.base import ContentFile
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from PIL import Image
from slugify import slugify

from .validators import validate_spicy


def unique_slugify(base: str, queryset: models.QuerySet, slug_field: str = "slug") -> str:
    slug = slugify(base)
    if not queryset.filter(**{slug_field: slug}).exists():
        return slug
    counter = 2
    while True:
        candidate = f"{slug}-{counter}"
        if not queryset.filter(**{slug_field: candidate}).exists():
            return candidate
        counter += 1


def build_thumb_name(image_name: str) -> str:
    stem = image_name.rsplit(".", 1)[0]
    return f"{stem}_thumb.png"


def make_thumbnail(image_field, size=(300, 300)):
    image_field.open()
    with Image.open(image_field) as image:
        image = image.convert("RGBA")
        image.thumbnail(size, Image.LANCZOS)
        thumb_io = BytesIO()
        image.save(thumb_io, format="PNG", optimize=True)
        return ContentFile(thumb_io.getvalue())


def make_square_thumbnail(image_field, size=300):
    image_field.open()
    with Image.open(image_field) as image:
        image = image.convert("RGBA")
        width, height = image.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        square = image.crop((left, top, left + side, top + side))
        square = square.resize((size, size), Image.LANCZOS)
        thumb_io = BytesIO()
        square.save(thumb_io, format="PNG", optimize=True)
        return ContentFile(thumb_io.getvalue())


def delete_stored_file(storage, file_name: str | None):
    if not storage or not file_name:
        return
    try:
        storage.delete(file_name)
    except Exception:
        # Storage backends can raise if file is already missing.
        pass


class Category(models.Model):
    title = models.CharField(max_length=120, unique=True, verbose_name="Название категории")
    slug = models.SlugField(max_length=160, unique=True, verbose_name="Адрес")
    image = models.ImageField(upload_to="categories/", blank=True, verbose_name="Иконка")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self) -> str:
        return self.title


class Country(models.Model):
    title = models.CharField(max_length=120, unique=True, verbose_name="Название страны")
    slug = models.SlugField(max_length=160, unique=True, verbose_name="Адрес")
    image = models.ImageField(upload_to="countries/", blank=True, verbose_name="Иконка")

    class Meta:
        verbose_name = "Страна"
        verbose_name_plural = "Страны"

    def __str__(self) -> str:
        return self.title


class CatalogFilterSettings(models.Model):
    all_categories_image = models.ImageField(upload_to="filters/", blank=True)
    all_countries_image = models.ImageField(upload_to="filters/", blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Настройки фильтров"
        verbose_name_plural = "Настройки фильтров"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return "Настройки фильтров"


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="Категория")
    country = models.ForeignKey(Country, on_delete=models.PROTECT, verbose_name="Страна")
    title = models.CharField(max_length=255, verbose_name="Название товара")
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name="Адрес")
    description = models.TextField(blank=True, verbose_name="Описание")
    ingredients = models.TextField(blank=True, verbose_name="Состав")
    preparation = models.TextField(blank=True, verbose_name="Приготовление")
    serving = models.TextField(blank=True, verbose_name="Подача")
    photo = models.ImageField(upload_to="products/", blank=True, verbose_name="Фото")
    photo_thumb = models.ImageField(upload_to="products/thumbs/", blank=True, editable=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    spicy = models.PositiveSmallIntegerField(
        default=0,
        validators=[validate_spicy],
        verbose_name="Острота (0-5)",
    )
    is_new = models.BooleanField(default=False, verbose_name="Маркер новинки")
    new_marked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        indexes = [
            # Most common catalog filter path is category+country pair.
            models.Index(fields=["category", "country"]),
        ]

    def save(self, *args, **kwargs):
        previous_photo_name = None
        previous_is_new = None
        previous_new_marked_at = None

        if self.pk:
            previous = Product.objects.filter(pk=self.pk).only(
                "photo",
                "is_new",
                "new_marked_at",
            ).first()
            if previous:
                previous_photo_name = previous.photo.name if previous.photo else None
                previous_is_new = previous.is_new
                previous_new_marked_at = previous.new_marked_at

        if not self.slug:
            self.slug = unique_slugify(self.title, Product.objects.all())

        if self.is_new:
            if previous_is_new is False:
                self.new_marked_at = timezone.now()
            elif previous_is_new is True:
                if not self.new_marked_at:
                    self.new_marked_at = previous_new_marked_at
            elif not self.new_marked_at:
                self.new_marked_at = timezone.now()
        else:
            self.new_marked_at = None

        super().save(*args, **kwargs)

        current_photo_name = self.photo.name if self.photo else None
        photo_changed = previous_photo_name != current_photo_name

        if previous_photo_name and photo_changed:
            delete_stored_file(self.photo.storage, previous_photo_name)

        if self.photo and (photo_changed or not self.photo_thumb):
            current_thumb_name = self.photo_thumb.name if self.photo_thumb else None
            thumb = make_square_thumbnail(self.photo, size=300)
            self.photo_thumb.save(build_thumb_name(self.photo.name), thumb, save=False)
            super().save(update_fields=["photo_thumb"])
            if current_thumb_name and current_thumb_name != self.photo_thumb.name:
                delete_stored_file(self.photo_thumb.storage, current_thumb_name)

        if not self.photo and self.photo_thumb:
            thumb_name = self.photo_thumb.name
            self.photo_thumb = None
            super().save(update_fields=["photo_thumb"])
            delete_stored_file(self.photo_thumb.storage, thumb_name)

    def delete(self, *args, **kwargs):
        photo_name = self.photo.name if self.photo else None
        thumb_name = self.photo_thumb.name if self.photo_thumb else None
        photo_storage = self.photo.storage if self.photo else None
        thumb_storage = self.photo_thumb.storage if self.photo_thumb else None
        super().delete(*args, **kwargs)
        delete_stored_file(photo_storage, photo_name)
        delete_stored_file(thumb_storage, thumb_name)

    def __str__(self) -> str:
        return self.title


class DiscountGroup(models.Model):
    DISCOUNT_PERCENT = "percent"
    DISCOUNT_FIXED = "fixed"
    DISCOUNT_TYPE_CHOICES = (
        (DISCOUNT_PERCENT, "Процент"),
        (DISCOUNT_FIXED, "Рубли"),
    )

    name = models.CharField(max_length=140, unique=True, verbose_name="Название группы")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    is_active = models.BooleanField(default=True, verbose_name="Активность группы")
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        verbose_name="Тип скидки (%/₽)",
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Размер скидки",
    )

    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="discount_groups",
        verbose_name="Категории",
    )
    countries = models.ManyToManyField(
        Country,
        blank=True,
        related_name="discount_groups",
        verbose_name="Страны",
    )
    manual_products = models.ManyToManyField(
        Product,
        blank=True,
        related_name="manual_discount_groups",
        verbose_name="Включенные товары",
    )
    excluded_products = models.ManyToManyField(
        Product,
        blank=True,
        related_name="excluded_discount_groups",
        verbose_name="Исключенные товары",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Скидочная группа"
        verbose_name_plural = "Скидочные группы"
        ordering = ("-updated_at", "-id")
        indexes = [
            models.Index(fields=["is_active", "start_at", "end_at"]),
        ]

    def __str__(self) -> str:
        return self.name

    def get_effective_products_qs(self):
        category_ids = list(self.categories.values_list("id", flat=True))
        country_ids = list(self.countries.values_list("id", flat=True))

        if category_ids and country_ids:
            base_qs = Product.objects.filter(category_id__in=category_ids, country_id__in=country_ids)
        elif category_ids:
            base_qs = Product.objects.filter(category_id__in=category_ids)
        elif country_ids:
            base_qs = Product.objects.filter(country_id__in=country_ids)
        else:
            base_qs = Product.objects.none()

        if self.manual_products.exists():
            base_qs = base_qs | self.manual_products.all()

        if self.excluded_products.exists():
            base_qs = base_qs.exclude(pk__in=self.excluded_products.values_list("pk", flat=True))

        return base_qs.distinct()

    def get_effective_product_ids(self) -> set[int]:
        return set(self.get_effective_products_qs().values_list("id", flat=True))


class Banner(models.Model):
    title = models.CharField(max_length=255, blank=True, verbose_name="Заголовок")
    description = models.TextField(blank=True, verbose_name="Описание")
    image = models.ImageField(upload_to="banners/", blank=True, verbose_name="Картинка")
    image_thumb = models.ImageField(upload_to="banners/thumbs/", blank=True, editable=False)
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Позиция в карусели")
    background_image = models.ImageField(
        upload_to="banners/backgrounds/",
        blank=True,
        verbose_name="Фон баннера",
    )
    background_color = models.CharField(
        max_length=20,
        blank=True,
        default="#0B6BA7",
        verbose_name="Цвет фона",
    )
    background_opacity = models.PositiveSmallIntegerField(
        default=60,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="0-100",
        verbose_name="Непрозрачность фона",
    )
    link_url = models.URLField(blank=True, verbose_name="Ссылка для перехода")
    is_active = models.BooleanField(default=True, verbose_name="Активность баннера")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"
        ordering = ("sort_order", "id")

    def save(self, *args, **kwargs):
        previous_image_name = None
        previous_background_name = None

        if not self.background_color:
            self.background_color = "#0B6BA7"
        try:
            self.background_opacity = max(0, min(100, int(self.background_opacity)))
        except (TypeError, ValueError):
            self.background_opacity = 60

        if self.pk:
            previous = Banner.objects.filter(pk=self.pk).only("image", "background_image").first()
            if previous:
                previous_image_name = previous.image.name if previous.image else None
                previous_background_name = (
                    previous.background_image.name if previous.background_image else None
                )
        elif not self.sort_order:
            max_sort_order = (
                Banner.objects.exclude(pk=self.pk).aggregate(models.Max("sort_order"))[
                    "sort_order__max"
                ]
                or 0
            )
            self.sort_order = max_sort_order + 10

        super().save(*args, **kwargs)

        current_image_name = self.image.name if self.image else None
        current_background_name = self.background_image.name if self.background_image else None
        image_changed = previous_image_name != current_image_name
        background_changed = previous_background_name != current_background_name

        if previous_image_name and image_changed:
            delete_stored_file(self.image.storage, previous_image_name)
        if previous_background_name and background_changed:
            delete_stored_file(self.background_image.storage, previous_background_name)

        if self.image and (image_changed or not self.image_thumb):
            current_thumb_name = self.image_thumb.name if self.image_thumb else None
            thumb = make_thumbnail(self.image, size=(600, 600))
            self.image_thumb.save(build_thumb_name(self.image.name), thumb, save=False)
            super().save(update_fields=["image_thumb"])
            if current_thumb_name and current_thumb_name != self.image_thumb.name:
                delete_stored_file(self.image_thumb.storage, current_thumb_name)

    def delete(self, *args, **kwargs):
        image_name = self.image.name if self.image else None
        thumb_name = self.image_thumb.name if self.image_thumb else None
        background_name = self.background_image.name if self.background_image else None
        image_storage = self.image.storage if self.image else None
        thumb_storage = self.image_thumb.storage if self.image_thumb else None
        background_storage = self.background_image.storage if self.background_image else None
        super().delete(*args, **kwargs)
        delete_stored_file(image_storage, image_name)
        delete_stored_file(thumb_storage, thumb_name)
        delete_stored_file(background_storage, background_name)

    def __str__(self) -> str:
        return self.title or f"Баннер #{self.pk or 'new'}"
