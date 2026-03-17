from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0002_about_tab_section"),
    ]

    operations = [
        migrations.CreateModel(
            name="HeroSection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("image", models.ImageField(blank=True, upload_to="hero/")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Hero блок",
                "verbose_name_plural": "Hero блок",
            },
        ),
    ]
