from django.db import migrations, models


def populate_banner_sort_order(apps, schema_editor):
    Banner = apps.get_model("catalog", "Banner")
    banners = Banner.objects.order_by("created_at", "id")
    for index, banner in enumerate(banners, start=1):
        banner.sort_order = index * 10
        banner.save(update_fields=["sort_order"])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0007_banner_background_opacity_percent"),
    ]

    operations = [
        migrations.AddField(
            model_name="banner",
            name="sort_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(populate_banner_sort_order, migrations.RunPython.noop),
    ]
