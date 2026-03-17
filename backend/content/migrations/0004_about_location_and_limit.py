from django.db import migrations


DEFAULT_MAP_SCRIPT_URL = (
    "https://api-maps.yandex.ru/services/constructor/1.0/js/"
    "?um=constructor%3Aa815bd444fdb2228bba51417b357d87edf3b9e0a011679d74b577597ed9fa029"
    "&width=1280&height=720&lang=ru_RU&scroll=true"
)


def ensure_location_and_limit_generic(apps, schema_editor):
    AboutTabSection = apps.get_model("content", "AboutTabSection")

    for conflict in AboutTabSection.objects.filter(section_type="generic", slug="location"):
        conflict.slug = f"location-{conflict.pk}"
        conflict.save(update_fields=["slug"])

    location = (
        AboutTabSection.objects.filter(section_type="location").order_by("id").first()
    )
    if location is None:
        location = AboutTabSection.objects.create(
            title="Расположение",
            slug="location",
            description="",
            section_type="location",
            map_script_url=DEFAULT_MAP_SCRIPT_URL,
            sort_order=999,
            is_active=True,
        )
    else:
        location.title = "Расположение"
        location.slug = "location"
        location.image = ""
        location.map_script_url = DEFAULT_MAP_SCRIPT_URL
        location.sort_order = 999
        location.is_active = True
        location.save(
            update_fields=[
                "title",
                "slug",
                "image",
                "map_script_url",
                "sort_order",
                "is_active",
            ]
        )

    for duplicate in (
        AboutTabSection.objects.filter(section_type="location").exclude(pk=location.pk)
    ):
        duplicate.delete()

    generic_sections = list(
        AboutTabSection.objects.filter(section_type="generic").order_by("sort_order", "id")
    )
    for extra in generic_sections[3:]:
        extra.delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0003_herosection"),
    ]

    operations = [
        migrations.RunPython(ensure_location_and_limit_generic, noop_reverse),
    ]
