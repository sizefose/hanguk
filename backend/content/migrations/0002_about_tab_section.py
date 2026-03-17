from django.db import migrations, models

DEFAULT_YANDEX_MAP_SCRIPT_URL = (
    "https://api-maps.yandex.ru/services/constructor/1.0/js/"
    "?um=constructor%3Aa815bd444fdb2228bba51417b357d87edf3b9e0a011679d74b577597ed9fa029"
    "&width=1280&height=720&lang=ru_RU&scroll=true"
)


def seed_default_location(apps, schema_editor):
    AboutTabSection = apps.get_model("content", "AboutTabSection")

    if AboutTabSection.objects.exists():
        return

    AboutTabSection.objects.create(
        title="Расположение",
        slug="location",
        description="",
        section_type="location",
        map_script_url=DEFAULT_YANDEX_MAP_SCRIPT_URL,
        sort_order=0,
        is_active=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AboutTabSection",
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
                ("title", models.CharField(max_length=120)),
                ("slug", models.SlugField(blank=True, max_length=160, unique=True)),
                ("description", models.TextField(blank=True)),
                ("image", models.ImageField(blank=True, upload_to="about/")),
                (
                    "section_type",
                    models.CharField(
                        choices=[("generic", "Обычный"), ("location", "Расположение")],
                        default="generic",
                        max_length=20,
                    ),
                ),
                (
                    "map_script_url",
                    models.URLField(blank=True, default=DEFAULT_YANDEX_MAP_SCRIPT_URL),
                ),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Раздел «о Нас»",
                "verbose_name_plural": "Раздел «о Нас»",
                "ordering": ("sort_order", "id"),
            },
        ),
        migrations.RunPython(seed_default_location, migrations.RunPython.noop),
        migrations.DeleteModel(name="AboutSection"),
    ]
