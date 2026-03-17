from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_banner_image_thumb_product_photo_thumb"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="image",
            field=models.ImageField(blank=True, upload_to="categories/"),
        ),
        migrations.AddField(
            model_name="country",
            name="image",
            field=models.ImageField(blank=True, upload_to="countries/"),
        ),
    ]
