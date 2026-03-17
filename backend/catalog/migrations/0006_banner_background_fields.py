from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0005_discountgroup"),
    ]

    operations = [
        migrations.AddField(
            model_name="banner",
            name="background_color",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="banner",
            name="background_image",
            field=models.ImageField(blank=True, upload_to="banners/backgrounds/"),
        ),
        migrations.AddField(
            model_name="banner",
            name="background_opacity",
            field=models.DecimalField(decimal_places=2, default=1, max_digits=3),
        ),
    ]
