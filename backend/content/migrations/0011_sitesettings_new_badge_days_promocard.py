from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0010_product_new_marked_at"),
        ("content", "0010_sitesettings_hide_prices"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="new_badge_days",
            field=models.PositiveSmallIntegerField(
                default=7,
                help_text="Количество дней для отображения товара как новинки.",
                verbose_name="Время отображения статуса новинок",
            ),
        ),
        migrations.CreateModel(
            name="PromoCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="promo_cards/")),
                (
                    "scenario",
                    models.CharField(
                        choices=[("link", "Ссылка"), ("list", "Список"), ("new", "Новинки")],
                        default="link",
                        max_length=16,
                    ),
                ),
                ("link_url", models.URLField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "products",
                    models.ManyToManyField(blank=True, related_name="promo_cards", to="catalog.product"),
                ),
            ],
            options={
                "verbose_name": "Карточка блока",
                "verbose_name_plural": "Карточки блока",
                "ordering": ("sort_order", "id"),
            },
        ),
    ]
