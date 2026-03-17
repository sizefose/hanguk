from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0008_banner_sort_order"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Recommendation",
        ),
    ]
