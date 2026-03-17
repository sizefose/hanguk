from django.db import migrations, models


def migrate_legacy_footer_data(apps, schema_editor):
    SiteSettings = apps.get_model("content", "SiteSettings")
    FooterAddress = apps.get_model("content", "FooterAddress")
    FooterPhone = apps.get_model("content", "FooterPhone")

    settings = SiteSettings.objects.order_by("pk").first()
    if not settings:
        return

    addresses = [
        (settings.address_1_text, settings.address_1_url),
        (settings.address_2_text, settings.address_2_url),
        (settings.address_3_text, settings.address_3_url),
    ]
    phones = [
        (settings.contact_1_display, settings.contact_1_link),
        (settings.contact_2_display, settings.contact_2_link),
        (settings.contact_3_display, settings.contact_3_link),
    ]

    for index, (title, url) in enumerate(addresses, start=1):
        if not title:
            continue
        FooterAddress.objects.create(
            settings_id=settings.pk,
            title=title,
            url=url or "",
            sort_order=index * 10,
            is_active=True,
        )

    for index, (title, phone_link) in enumerate(phones, start=1):
        if not title:
            continue
        FooterPhone.objects.create(
            settings_id=settings.pk,
            title=title,
            phone_link=phone_link or "",
            sort_order=index * 10,
            is_active=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0005_sitesettings"),
    ]

    operations = [
        migrations.CreateModel(
            name="FooterAddress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("url", models.URLField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "settings",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="footer_addresses",
                        to="content.sitesettings",
                    ),
                ),
            ],
            options={
                "verbose_name": "Адрес футера",
                "verbose_name_plural": "Адреса футера",
                "ordering": ("sort_order", "id"),
            },
        ),
        migrations.CreateModel(
            name="FooterPhone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=80)),
                ("phone_link", models.CharField(blank=True, max_length=32)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "settings",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="footer_phones",
                        to="content.sitesettings",
                    ),
                ),
            ],
            options={
                "verbose_name": "Телефон футера",
                "verbose_name_plural": "Телефоны футера",
                "ordering": ("sort_order", "id"),
            },
        ),
        migrations.RunPython(migrate_legacy_footer_data, migrations.RunPython.noop),
    ]
