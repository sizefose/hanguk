from django.core.exceptions import ValidationError
from django.db import models
from django.db.utils import OperationalError, ProgrammingError

from catalog.models import Banner, Product, delete_stored_file, unique_slugify

DEFAULT_YANDEX_MAP_SCRIPT_URL = (
    "https://api-maps.yandex.ru/services/constructor/1.0/js/"
    "?um=constructor%3Aa815bd444fdb2228bba51417b357d87edf3b9e0a011679d74b577597ed9fa029"
    "&width=1280&height=720&lang=ru_RU&scroll=true"
)
MAX_ABOUT_GENERIC_SECTIONS = 3


class AboutTabSection(models.Model):
    SECTION_GENERIC = "generic"
    SECTION_LOCATION = "location"
    SECTION_TYPE_CHOICES = (
        (SECTION_GENERIC, "Обычный"),
        (SECTION_LOCATION, "Расположение"),
    )

    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="about/", blank=True)
    section_type = models.CharField(
        max_length=20,
        choices=SECTION_TYPE_CHOICES,
        default=SECTION_GENERIC,
    )
    map_script_url = models.URLField(blank=True, default=DEFAULT_YANDEX_MAP_SCRIPT_URL)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Раздел «о Нас»"
        verbose_name_plural = "Раздел «о Нас»"
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        return self.title

    def clean(self):
        super().clean()
        if self.section_type == self.SECTION_LOCATION:
            qs = AboutTabSection.objects.filter(section_type=self.SECTION_LOCATION)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({"section_type": "Раздел 'Расположение' может быть только один."})
        else:
            qs = AboutTabSection.objects.filter(section_type=self.SECTION_GENERIC)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.count() >= MAX_ABOUT_GENERIC_SECTIONS:
                raise ValidationError(
                    {
                        "section_type": (
                            f"Можно создать не более {MAX_ABOUT_GENERIC_SECTIONS} дополнительных вкладок."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        old_image = None

        if self.pk:
            previous = AboutTabSection.objects.filter(pk=self.pk).only("image").first()
            if previous and previous.image:
                old_image = previous.image.name

        if not self.slug:
            self.slug = unique_slugify(
                self.title,
                AboutTabSection.objects.exclude(pk=self.pk),
            )

        if self.section_type == self.SECTION_LOCATION:
            self.title = "Расположение"
            self.slug = "location"
            self.image = None
            self.map_script_url = DEFAULT_YANDEX_MAP_SCRIPT_URL
            self.is_active = True
            self.sort_order = 999

        super().save(*args, **kwargs)

        current_image = self.image.name if self.image else None
        if old_image and old_image != current_image:
            delete_stored_file(self.image.storage, old_image)

    def delete(self, *args, **kwargs):
        image_name = self.image.name if self.image else None
        image_storage = self.image.storage if self.image else None
        super().delete(*args, **kwargs)
        delete_stored_file(image_storage, image_name)


class ContentBanner(Banner):
    class Meta:
        proxy = True
        app_label = "content"
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"


class HeroSection(models.Model):
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="hero/", blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hero блок"
        verbose_name_plural = "Hero блок"

    def save(self, *args, **kwargs):
        old_image = None

        if self.pk:
            previous = HeroSection.objects.filter(pk=self.pk).only("image").first()
            if previous and previous.image:
                old_image = previous.image.name

        self.pk = 1
        super().save(*args, **kwargs)

        current_image = self.image.name if self.image else None
        if old_image and old_image != current_image:
            delete_stored_file(self.image.storage, old_image)

    def delete(self, *args, **kwargs):
        image_name = self.image.name if self.image else None
        image_storage = self.image.storage if self.image else None
        super().delete(*args, **kwargs)
        delete_stored_file(image_storage, image_name)

    def __str__(self) -> str:
        return "Hero блок"


class SiteSettings(models.Model):
    header_action_label = models.CharField(max_length=80, blank=True, default="Войти")
    header_action_url = models.URLField(blank=True)

    telegram_button_label = models.CharField(max_length=80, blank=True, default="Наш Telegram")
    telegram_button_url = models.URLField(blank=True, default="https://t.me/hangukmarket161")

    order_phone_display = models.CharField(max_length=40, blank=True, default="+7 (919) 895-90-29")
    order_phone_link = models.CharField(max_length=20, blank=True, default="+79198959029")

    address_1_text = models.CharField(max_length=255, blank=True, default="просп. Маршала Жукова, 27/3")
    address_1_url = models.URLField(blank=True, default="https://yandex.ru/maps/-/CLVAqU8U")
    address_2_text = models.CharField(max_length=255, blank=True, default="ул. Стабильная, 15В")
    address_2_url = models.URLField(blank=True, default="https://yandex.ru/maps/-/CLVAiFMH")
    address_3_text = models.CharField(max_length=255, blank=True, default="ул. Зорге, 13В")
    address_3_url = models.URLField(blank=True, default="https://yandex.ru/maps/-/CLVAmT-R")

    contact_1_display = models.CharField(max_length=40, blank=True, default="+7 (928) 182-64-74")
    contact_1_link = models.CharField(max_length=20, blank=True, default="+79281826474")
    contact_2_display = models.CharField(max_length=40, blank=True, default="+7 (928) 602-62-82")
    contact_2_link = models.CharField(max_length=20, blank=True, default="+79286026282")
    contact_3_display = models.CharField(max_length=40, blank=True, default="+7 (919) 895-90-29")
    contact_3_link = models.CharField(max_length=20, blank=True, default="+79198959029")

    social_vk_url = models.URLField(blank=True, default="https://vk.com/hangukmarket161")
    social_whatsapp_url = models.URLField(blank=True, default="https://wa.me/79286026282")
    social_telegram_url = models.URLField(blank=True, default="https://t.me/hangukmarket161")

    maker_label = models.CharField(max_length=80, blank=True, default="sizeworks")
    maker_url = models.URLField(blank=True, default="https://t.me/+OODKdq0iQFsyMDky")

    legal_text = models.TextField(
        blank=True,
        default=(
            "ОГРН: 317619600223090, ИНН: 616813760570. "
            "Ростовская область, г. Ростов-на-Дону."
        ),
    )
    new_badge_days = models.PositiveSmallIntegerField(
        default=7,
        verbose_name="Время отображения статуса новинок",
        help_text="Количество дней для отображения товара как новинки.",
    )
    hide_prices = models.BooleanField(default=False, verbose_name="Скрытие цен")
    default_categories = models.ManyToManyField(
        "catalog.Category",
        blank=True,
        related_name="default_site_settings",
        verbose_name="Категории по умолчанию",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Настройки"
        verbose_name_plural = "Настройки"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

        try:
            has_store_contacts = self.store_contacts.exists()
        except (ProgrammingError, OperationalError):
            has_store_contacts = True

        if not has_store_contacts:
            defaults = [
                (self.address_1_text, self.contact_1_display),
                (self.address_2_text, self.contact_2_display),
                (self.address_3_text, self.contact_3_display),
            ]
            for index, (address, phone) in enumerate(defaults, start=1):
                if not (address or phone):
                    continue
                self.store_contacts.create(
                    name=f"Магазин {index}",
                    address=address or "",
                    phone=phone or "",
                    sort_order=index,
                    is_active=True,
                )

    def __str__(self) -> str:
        return "Настройки"


class FooterAddress(models.Model):
    settings = models.ForeignKey(
        SiteSettings,
        on_delete=models.CASCADE,
        related_name="footer_addresses",
    )
    title = models.CharField(max_length=255)
    url = models.URLField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Адрес футера"
        verbose_name_plural = "Адреса футера"
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        return self.title


class FooterPhone(models.Model):
    settings = models.ForeignKey(
        SiteSettings,
        on_delete=models.CASCADE,
        related_name="footer_phones",
    )
    title = models.CharField(max_length=80)
    phone_link = models.CharField(max_length=32, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Телефон футера"
        verbose_name_plural = "Телефоны футера"
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        return self.title


class StoreContact(models.Model):
    settings = models.ForeignKey(
        SiteSettings,
        on_delete=models.CASCADE,
        related_name="store_contacts",
    )
    name = models.CharField(max_length=120, blank=True, default="Магазин")
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=64, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Магазин"
        verbose_name_plural = "Магазины"
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        title = self.name.strip() or self.address
        return f"{title} — {self.phone}" if self.phone else title


class StoreDelivery(models.Model):
    SERVICE_CHIBBIS = "chibbis"
    SERVICE_YANDEX_FOOD = "yandex_food"
    SERVICE_PICKUP = "pickup"
    SERVICE_TYPE_CHOICES = (
        (SERVICE_CHIBBIS, "Чиббис"),
        (SERVICE_YANDEX_FOOD, "Яндекс.Еда"),
        (SERVICE_PICKUP, "Самовывоз"),
    )

    settings = models.ForeignKey(
        SiteSettings,
        on_delete=models.CASCADE,
        related_name="store_deliveries",
    )
    store = models.ForeignKey(
        StoreContact,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    service_type = models.CharField(max_length=32, choices=SERVICE_TYPE_CHOICES)
    service_url = models.URLField(blank=True)
    map_script_url = models.URLField(blank=True, default=DEFAULT_YANDEX_MAP_SCRIPT_URL)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Доставка магазина"
        verbose_name_plural = "Доставки магазинов"
        ordering = ("sort_order", "id")

    def clean(self):
        super().clean()
        if self.store_id and self.settings_id and self.store.settings_id != self.settings_id:
            raise ValidationError({"store": "Магазин должен принадлежать тем же настройкам сайта."})

    def save(self, *args, **kwargs):
        if self.store_id and not self.settings_id:
            self.settings_id = self.store.settings_id
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.get_service_type_display()} — {self.store}"


class PromoCard(models.Model):
    SCENARIO_LINK = "link"
    SCENARIO_LIST = "list"
    SCENARIO_NEW = "new"
    SCENARIO_CHOICES = (
        (SCENARIO_LINK, "Ссылка"),
        (SCENARIO_LIST, "Список"),
        (SCENARIO_NEW, "Новинки"),
    )

    image = models.ImageField(upload_to="promo_cards/")
    scenario = models.CharField(max_length=16, choices=SCENARIO_CHOICES, default=SCENARIO_LINK)
    link_url = models.URLField(blank=True)
    products = models.ManyToManyField(Product, blank=True, related_name="promo_cards")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Карточка предложения"
        verbose_name_plural = "Карточки предложений"
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        return f"Карточка #{self.pk or 'new'}"

    def clean(self):
        super().clean()

        if self.scenario == self.SCENARIO_LINK and not self.link_url:
            raise ValidationError({"link_url": "Укажите ссылку для сценария 'Ссылка'."})

        if self.scenario == self.SCENARIO_NEW:
            qs = PromoCard.objects.filter(scenario=self.SCENARIO_NEW)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"scenario": "Карточка со сценарием 'Новинки' может быть только одна."}
                )
