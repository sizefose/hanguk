from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0011_sitesettings_new_badge_days_promocard"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="sitesettings",
            options={"verbose_name": "Настройки", "verbose_name_plural": "Настройки"},
        ),
        migrations.AlterModelOptions(
            name="promocard",
            options={"ordering": ("sort_order", "id"), "verbose_name": "Карточка предложения", "verbose_name_plural": "Карточки предложений"},
        ),
    ]
