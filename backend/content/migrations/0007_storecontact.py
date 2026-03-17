from django.db import migrations, models


def migrate_store_contacts(apps, schema_editor):
    SiteSettings = apps.get_model("content", "SiteSettings")
    FooterAddress = apps.get_model("content", "FooterAddress")
    FooterPhone = apps.get_model("content", "FooterPhone")
    StoreContact = apps.get_model("content", "StoreContact")

    settings = SiteSettings.objects.order_by("pk").first()
    if not settings:
        return

    addresses = list(
        FooterAddress.objects.filter(settings_id=settings.pk, is_active=True)
        .order_by("sort_order", "id")
        .values_list("title", flat=True)
    )
    phones = list(
        FooterPhone.objects.filter(settings_id=settings.pk, is_active=True)
        .order_by("sort_order", "id")
        .values_list("title", flat=True)
    )

    if not addresses and not phones:
        addresses = [settings.address_1_text, settings.address_2_text, settings.address_3_text]
        phones = [settings.contact_1_display, settings.contact_2_display, settings.contact_3_display]

    max_len = max(len(addresses), len(phones))
    for index in range(max_len):
        address = addresses[index] if index < len(addresses) else ""
        phone = phones[index] if index < len(phones) else ""
        if not address and not phone:
            continue
        StoreContact.objects.create(
            settings_id=settings.pk,
            address=address or "",
            phone=phone or "",
            sort_order=(index + 1) * 10,
            is_active=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0006_footer_entries"),
    ]

    operations = [
        migrations.CreateModel(
            name="StoreContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("address", models.CharField(max_length=255)),
                ("phone", models.CharField(blank=True, max_length=64)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "settings",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="store_contacts",
                        to="content.sitesettings",
                    ),
                ),
            ],
            options={
                "verbose_name": "Магазин",
                "verbose_name_plural": "Магазины",
                "ordering": ("sort_order", "id"),
            },
        ),
        migrations.RunPython(migrate_store_contacts, migrations.RunPython.noop),
    ]
