from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0004_about_location_and_limit"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("header_action_label", models.CharField(blank=True, default="Войти", max_length=80)),
                ("header_action_url", models.URLField(blank=True)),
                ("telegram_button_label", models.CharField(blank=True, default="Наш Telegram", max_length=80)),
                ("telegram_button_url", models.URLField(blank=True, default="https://t.me/hangukmarket161")),
                ("order_phone_display", models.CharField(blank=True, default="+7 (919) 895-90-29", max_length=40)),
                ("order_phone_link", models.CharField(blank=True, default="+79198959029", max_length=20)),
                ("address_1_text", models.CharField(blank=True, default="просп. Маршала Жукова, 27/3", max_length=255)),
                ("address_1_url", models.URLField(blank=True, default="https://yandex.ru/maps/-/CLVAqU8U")),
                ("address_2_text", models.CharField(blank=True, default="ул. Стабильная, 15В", max_length=255)),
                ("address_2_url", models.URLField(blank=True, default="https://yandex.ru/maps/-/CLVAiFMH")),
                ("address_3_text", models.CharField(blank=True, default="ул. Зорге, 13В", max_length=255)),
                ("address_3_url", models.URLField(blank=True, default="https://yandex.ru/maps/-/CLVAmT-R")),
                ("contact_1_display", models.CharField(blank=True, default="+7 (928) 182-64-74", max_length=40)),
                ("contact_1_link", models.CharField(blank=True, default="+79281826474", max_length=20)),
                ("contact_2_display", models.CharField(blank=True, default="+7 (928) 602-62-82", max_length=40)),
                ("contact_2_link", models.CharField(blank=True, default="+79286026282", max_length=20)),
                ("contact_3_display", models.CharField(blank=True, default="+7 (919) 895-90-29", max_length=40)),
                ("contact_3_link", models.CharField(blank=True, default="+79198959029", max_length=20)),
                ("social_vk_url", models.URLField(blank=True, default="https://vk.com/hangukmarket161")),
                ("social_whatsapp_url", models.URLField(blank=True, default="https://wa.me/79286026282")),
                ("social_telegram_url", models.URLField(blank=True, default="https://t.me/hangukmarket161")),
                ("maker_label", models.CharField(blank=True, default="sizeworks", max_length=80)),
                ("maker_url", models.URLField(blank=True, default="https://t.me/+OODKdq0iQFsyMDky")),
                (
                    "legal_text",
                    models.TextField(
                        blank=True,
                        default=(
                            "ОГРН: 317619600223090, ИНН: 616813760570. "
                            "Ростовская область, г. Ростов-на-Дону."
                        ),
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Настройки сайта",
                "verbose_name_plural": "Настройки сайта",
            },
        ),
    ]
