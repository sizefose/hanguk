from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0013_sitesettings_default_categories"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="herosection",
            options={"verbose_name": "Hero", "verbose_name_plural": "Hero"},
        ),
        migrations.AlterModelOptions(
            name="promocard",
            options={"ordering": ("sort_order", "id"), "verbose_name": "Карточка", "verbose_name_plural": "Карточки"},
        ),
        migrations.AlterField(
            model_name="abouttabsection",
            name="description",
            field=models.TextField(blank=True, verbose_name="Описание"),
        ),
        migrations.AlterField(
            model_name="abouttabsection",
            name="image",
            field=models.ImageField(blank=True, upload_to="about/", verbose_name="Изображение"),
        ),
        migrations.AlterField(
            model_name="abouttabsection",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Активность"),
        ),
        migrations.AlterField(
            model_name="abouttabsection",
            name="map_script_url",
            field=models.URLField(
                blank=True,
                default="https://api-maps.yandex.ru/services/constructor/1.0/js/?um=constructor%3Aa815bd444fdb2228bba51417b357d87edf3b9e0a011679d74b577597ed9fa029&width=1280&height=720&lang=ru_RU&scroll=true",
                verbose_name="Скрипт карты",
            ),
        ),
        migrations.AlterField(
            model_name="abouttabsection",
            name="section_type",
            field=models.CharField(
                choices=[("generic", "Обычный"), ("location", "Расположение")],
                default="generic",
                max_length=20,
                verbose_name="Тип раздела",
            ),
        ),
        migrations.AlterField(
            model_name="abouttabsection",
            name="slug",
            field=models.SlugField(
                blank=True,
                max_length=160,
                unique=True,
                verbose_name="Slug (служебный идентификатор вкладки)",
            ),
        ),
        migrations.AlterField(
            model_name="abouttabsection",
            name="sort_order",
            field=models.PositiveIntegerField(default=0, verbose_name="Позиция"),
        ),
        migrations.AlterField(
            model_name="abouttabsection",
            name="title",
            field=models.CharField(max_length=120, verbose_name="Заголовок"),
        ),
        migrations.AlterField(
            model_name="herosection",
            name="description",
            field=models.TextField(blank=True, verbose_name="Описание"),
        ),
        migrations.AlterField(
            model_name="herosection",
            name="image",
            field=models.ImageField(blank=True, upload_to="hero/", verbose_name="Изображение"),
        ),
        migrations.AlterField(
            model_name="promocard",
            name="image",
            field=models.ImageField(upload_to="promo_cards/", verbose_name="Изображение"),
        ),
        migrations.AlterField(
            model_name="promocard",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Активность карточки"),
        ),
        migrations.AlterField(
            model_name="promocard",
            name="link_url",
            field=models.URLField(blank=True, verbose_name="Ссылка для перехода"),
        ),
        migrations.AlterField(
            model_name="promocard",
            name="products",
            field=models.ManyToManyField(
                blank=True,
                related_name="promo_cards",
                to="catalog.product",
                verbose_name="Товары (Список)",
            ),
        ),
        migrations.AlterField(
            model_name="promocard",
            name="scenario",
            field=models.CharField(
                choices=[("link", "Ссылка"), ("list", "Список"), ("new", "Новинки")],
                default="link",
                max_length=16,
                verbose_name="Сценарий",
            ),
        ),
        migrations.AlterField(
            model_name="promocard",
            name="sort_order",
            field=models.PositiveIntegerField(default=0, verbose_name="Позиция карточки"),
        ),
        migrations.AlterField(
            model_name="storecontact",
            name="address",
            field=models.CharField(max_length=255, verbose_name="Адрес"),
        ),
        migrations.AlterField(
            model_name="storecontact",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Активность"),
        ),
        migrations.AlterField(
            model_name="storecontact",
            name="name",
            field=models.CharField(
                blank=True,
                default="Магазин",
                max_length=120,
                verbose_name="Имя магазина",
            ),
        ),
        migrations.AlterField(
            model_name="storecontact",
            name="phone",
            field=models.CharField(blank=True, max_length=64, verbose_name="Номер телефона"),
        ),
    ]
