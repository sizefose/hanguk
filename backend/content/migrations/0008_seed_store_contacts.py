from django.db import migrations


def seed_store_contacts(apps, schema_editor):
    SiteSettings = apps.get_model("content", "SiteSettings")
    StoreContact = apps.get_model("content", "StoreContact")

    settings = SiteSettings.objects.order_by("pk").first()
    if not settings:
        settings = SiteSettings.objects.create(pk=1)

    if StoreContact.objects.filter(settings_id=settings.pk).exists():
        return

    defaults = [
        ("просп. Маршала Жукова, 27/3", "+7 (928) 182-64-74"),
        ("ул. Стабильная, 15В", "+7 (928) 602-62-82"),
        ("ул. Зорге, 13В", "+7 (919) 895-90-29"),
    ]
    for index, (address, phone) in enumerate(defaults, start=1):
        StoreContact.objects.create(
            settings_id=settings.pk,
            address=address,
            phone=phone,
            sort_order=index * 10,
            is_active=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0007_storecontact"),
    ]

    operations = [
        migrations.RunPython(seed_store_contacts, migrations.RunPython.noop),
    ]
