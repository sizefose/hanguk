from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0009_delete_recommendation"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="new_marked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
