from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models

import catalog.validators


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0011_product_category_country_index"),
    ]

    operations = [
        migrations.AlterField(
            model_name="banner",
            name="background_color",
            field=models.CharField(
                blank=True,
                default="#0B6BA7",
                max_length=20,
                verbose_name="Цвет фона",
            ),
        ),
        migrations.AlterField(
            model_name="banner",
            name="background_image",
            field=models.ImageField(
                blank=True,
                upload_to="banners/backgrounds/",
                verbose_name="Фон баннера",
            ),
        ),
        migrations.AlterField(
            model_name="banner",
            name="background_opacity",
            field=models.PositiveSmallIntegerField(
                default=60,
                help_text="0-100",
                validators=[MinValueValidator(0), MaxValueValidator(100)],
                verbose_name="Непрозрачность фона",
            ),
        ),
        migrations.AlterField(
            model_name="banner",
            name="description",
            field=models.TextField(blank=True, verbose_name="Описание"),
        ),
        migrations.AlterField(
            model_name="banner",
            name="image",
            field=models.ImageField(upload_to="banners/", verbose_name="Картинка"),
        ),
        migrations.AlterField(
            model_name="banner",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Активность баннера"),
        ),
        migrations.AlterField(
            model_name="banner",
            name="link_url",
            field=models.URLField(blank=True, verbose_name="Ссылка для перехода"),
        ),
        migrations.AlterField(
            model_name="banner",
            name="sort_order",
            field=models.PositiveIntegerField(default=0, verbose_name="Позиция в карусели"),
        ),
        migrations.AlterField(
            model_name="banner",
            name="title",
            field=models.CharField(max_length=255, verbose_name="Заголовок"),
        ),
        migrations.AlterField(
            model_name="category",
            name="image",
            field=models.ImageField(blank=True, upload_to="categories/", verbose_name="Иконка"),
        ),
        migrations.AlterField(
            model_name="category",
            name="slug",
            field=models.SlugField(max_length=160, unique=True, verbose_name="Адрес"),
        ),
        migrations.AlterField(
            model_name="category",
            name="title",
            field=models.CharField(max_length=120, unique=True, verbose_name="Название категории"),
        ),
        migrations.AlterField(
            model_name="country",
            name="image",
            field=models.ImageField(blank=True, upload_to="countries/", verbose_name="Иконка"),
        ),
        migrations.AlterField(
            model_name="country",
            name="slug",
            field=models.SlugField(max_length=160, unique=True, verbose_name="Адрес"),
        ),
        migrations.AlterField(
            model_name="country",
            name="title",
            field=models.CharField(max_length=120, unique=True, verbose_name="Название страны"),
        ),
        migrations.AlterField(
            model_name="discountgroup",
            name="categories",
            field=models.ManyToManyField(
                blank=True,
                related_name="discount_groups",
                to="catalog.category",
                verbose_name="Категории",
            ),
        ),
        migrations.AlterField(
            model_name="discountgroup",
            name="countries",
            field=models.ManyToManyField(
                blank=True,
                related_name="discount_groups",
                to="catalog.country",
                verbose_name="Страны",
            ),
        ),
        migrations.AlterField(
            model_name="discountgroup",
            name="discount_type",
            field=models.CharField(
                choices=[("percent", "Процент"), ("fixed", "Рубли")],
                max_length=10,
                verbose_name="Тип скидки (%/₽)",
            ),
        ),
        migrations.AlterField(
            model_name="discountgroup",
            name="discount_value",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                verbose_name="Размер скидки",
            ),
        ),
        migrations.AlterField(
            model_name="discountgroup",
            name="excluded_products",
            field=models.ManyToManyField(
                blank=True,
                related_name="excluded_discount_groups",
                to="catalog.product",
                verbose_name="Исключенные товары",
            ),
        ),
        migrations.AlterField(
            model_name="discountgroup",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Активность группы"),
        ),
        migrations.AlterField(
            model_name="discountgroup",
            name="manual_products",
            field=models.ManyToManyField(
                blank=True,
                related_name="manual_discount_groups",
                to="catalog.product",
                verbose_name="Включенные товары",
            ),
        ),
        migrations.AlterField(
            model_name="discountgroup",
            name="name",
            field=models.CharField(max_length=140, unique=True, verbose_name="Название группы"),
        ),
        migrations.AlterField(
            model_name="product",
            name="category",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                to="catalog.category",
                verbose_name="Категория",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="country",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                to="catalog.country",
                verbose_name="Страна",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="description",
            field=models.TextField(blank=True, verbose_name="Описание"),
        ),
        migrations.AlterField(
            model_name="product",
            name="ingredients",
            field=models.TextField(blank=True, verbose_name="Состав"),
        ),
        migrations.AlterField(
            model_name="product",
            name="is_new",
            field=models.BooleanField(default=False, verbose_name="Маркер новинки"),
        ),
        migrations.AlterField(
            model_name="product",
            name="photo",
            field=models.ImageField(blank=True, upload_to="products/", verbose_name="Фото"),
        ),
        migrations.AlterField(
            model_name="product",
            name="preparation",
            field=models.TextField(blank=True, verbose_name="Приготовление"),
        ),
        migrations.AlterField(
            model_name="product",
            name="price",
            field=models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Цена"),
        ),
        migrations.AlterField(
            model_name="product",
            name="serving",
            field=models.TextField(blank=True, verbose_name="Подача"),
        ),
        migrations.AlterField(
            model_name="product",
            name="slug",
            field=models.SlugField(blank=True, max_length=255, unique=True, verbose_name="Адрес"),
        ),
        migrations.AlterField(
            model_name="product",
            name="spicy",
            field=models.PositiveSmallIntegerField(
                default=0,
                validators=[catalog.validators.validate_spicy],
                verbose_name="Острота (0-5)",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="title",
            field=models.CharField(max_length=255, verbose_name="Название товара"),
        ),
    ]
