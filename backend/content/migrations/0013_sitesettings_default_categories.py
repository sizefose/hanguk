from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0010_product_new_marked_at"),
        ("content", "0012_rename_admin_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="default_categories",
            field=models.ManyToManyField(
                blank=True,
                related_name="default_site_settings",
                to="catalog.category",
                verbose_name="Категории по умолчанию",
            ),
        ),
    ]
