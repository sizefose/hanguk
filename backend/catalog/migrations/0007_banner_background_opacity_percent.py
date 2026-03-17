from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_banner_background_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="banner",
            name="background_opacity",
            field=models.DecimalField(decimal_places=2, default=1, max_digits=5),
        ),
        migrations.RunSQL(
            sql=(
                "UPDATE catalog_banner "
                "SET background_opacity = "
                "CASE "
                "WHEN background_opacity <= 1 THEN LEAST(100, GREATEST(0, ROUND(background_opacity * 100))) "
                "ELSE LEAST(100, GREATEST(0, ROUND(background_opacity))) "
                "END"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name="banner",
            name="background_color",
            field=models.CharField(blank=True, default="#0B6BA7", max_length=20),
        ),
        migrations.AlterField(
            model_name="banner",
            name="background_opacity",
            field=models.PositiveSmallIntegerField(
                default=60,
                help_text="0-100",
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
    ]
