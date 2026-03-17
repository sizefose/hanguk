from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AboutSection",
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
                ("about_title", models.CharField(default="О нас", max_length=120)),
                ("about_text", models.TextField(blank=True)),
                ("about_image", models.ImageField(blank=True, upload_to="about/")),
                ("kitchen_title", models.CharField(default="Кухня", max_length=120)),
                ("kitchen_text", models.TextField(blank=True)),
                ("kitchen_image", models.ImageField(blank=True, upload_to="about/")),
                (
                    "location_title",
                    models.CharField(default="Расположение", max_length=120),
                ),
                ("location_text", models.TextField(blank=True)),
                ("location_image", models.ImageField(blank=True, upload_to="about/")),
                (
                    "yandex_map_script_url",
                    models.URLField(
                        blank=True,
                        default=(
                            "https://api-maps.yandex.ru/services/constructor/1.0/js/"
                            "?um=constructor%3Aa815bd444fdb2228bba51417b357d87edf3b9e0a011679d74b577597ed9fa029"
                            "&width=1280&height=720&lang=ru_RU&scroll=true"
                        ),
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Раздел о Нас",
                "verbose_name_plural": "Раздел о Нас",
            },
        ),
    ]
