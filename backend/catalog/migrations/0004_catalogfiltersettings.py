from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_category_country_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="CatalogFilterSettings",
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
                (
                    "all_categories_image",
                    models.ImageField(blank=True, upload_to="filters/"),
                ),
                (
                    "all_countries_image",
                    models.ImageField(blank=True, upload_to="filters/"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Настройки фильтров",
                "verbose_name_plural": "Настройки фильтров",
            },
        ),
    ]
