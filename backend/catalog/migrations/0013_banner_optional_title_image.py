from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0012_admin_field_labels"),
    ]

    operations = [
        migrations.AlterField(
            model_name="banner",
            name="image",
            field=models.ImageField(
                blank=True,
                upload_to="banners/",
                verbose_name="Картинка",
            ),
        ),
        migrations.AlterField(
            model_name="banner",
            name="title",
            field=models.CharField(
                blank=True,
                max_length=255,
                verbose_name="Заголовок",
            ),
        ),
    ]
