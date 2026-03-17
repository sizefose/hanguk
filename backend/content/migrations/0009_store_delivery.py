from django.db import migrations, models

import content.models


def seed_store_names(apps, schema_editor):
    StoreContact = apps.get_model("content", "StoreContact")
    for index, store in enumerate(StoreContact.objects.order_by("settings_id", "sort_order", "id"), start=1):
        if not (store.name or "").strip():
            store.name = f"Магазин {index}"
            store.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0008_seed_store_contacts"),
    ]

    operations = [
        migrations.AddField(
            model_name="storecontact",
            name="name",
            field=models.CharField(blank=True, default="Магазин", max_length=120),
        ),
        migrations.CreateModel(
            name="StoreDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "service_type",
                    models.CharField(
                        choices=[
                            ("chibbis", "Чиббис"),
                            ("yandex_food", "Яндекс.Еда"),
                            ("pickup", "Самовывоз"),
                        ],
                        max_length=32,
                    ),
                ),
                ("service_url", models.URLField(blank=True)),
                (
                    "map_script_url",
                    models.URLField(
                        blank=True,
                        default=content.models.DEFAULT_YANDEX_MAP_SCRIPT_URL,
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "settings",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="store_deliveries",
                        to="content.sitesettings",
                    ),
                ),
                (
                    "store",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="deliveries",
                        to="content.storecontact",
                    ),
                ),
            ],
            options={
                "verbose_name": "Доставка магазина",
                "verbose_name_plural": "Доставки магазинов",
                "ordering": ("sort_order", "id"),
            },
        ),
        migrations.RunPython(seed_store_names, migrations.RunPython.noop),
    ]
