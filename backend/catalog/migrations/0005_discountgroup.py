from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_catalogfiltersettings"),
    ]

    operations = [
        migrations.CreateModel(
            name="DiscountGroup",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=140, unique=True)),
                ("start_at", models.DateTimeField()),
                ("end_at", models.DateTimeField()),
                ("is_active", models.BooleanField(default=True)),
                (
                    "discount_type",
                    models.CharField(
                        choices=[("percent", "Процент"), ("fixed", "Рубли")],
                        max_length=10,
                    ),
                ),
                ("discount_value", models.DecimalField(decimal_places=2, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "categories",
                    models.ManyToManyField(blank=True, related_name="discount_groups", to="catalog.category"),
                ),
                (
                    "countries",
                    models.ManyToManyField(blank=True, related_name="discount_groups", to="catalog.country"),
                ),
                (
                    "excluded_products",
                    models.ManyToManyField(
                        blank=True,
                        related_name="excluded_discount_groups",
                        to="catalog.product",
                    ),
                ),
                (
                    "manual_products",
                    models.ManyToManyField(
                        blank=True,
                        related_name="manual_discount_groups",
                        to="catalog.product",
                    ),
                ),
            ],
            options={
                "verbose_name": "Скидочная группа",
                "verbose_name_plural": "Скидочные группы",
                "ordering": ("-updated_at", "-id"),
                "indexes": [models.Index(fields=["is_active", "start_at", "end_at"], name="catalog_disc_is_acti_3c2f9f_idx")],
            },
        ),
    ]
