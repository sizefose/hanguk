from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0010_product_new_marked_at"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["category", "country"],
                name="catalog_prod_cat_country_idx",
            ),
        ),
    ]
