from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0009_store_delivery"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="hide_prices",
            field=models.BooleanField(default=False, verbose_name="Скрытие цен"),
        ),
    ]
