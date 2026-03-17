from django.urls import path

from .views import (
    AboutSectionView,
    BannerListView,
    FilterOptionsView,
    HealthView,
    HeroSectionView,
    ProductDetailView,
    ProductListView,
    PromoCardListView,
    SiteSettingsView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path("banners/", BannerListView.as_view(), name="banner-list"),
    path("promo-cards/", PromoCardListView.as_view(), name="promo-card-list"),
    path("about-section/", AboutSectionView.as_view(), name="about-section"),
    path("hero/", HeroSectionView.as_view(), name="hero-section"),
    path("site-settings/", SiteSettingsView.as_view(), name="site-settings"),
    path("filter-options/", FilterOptionsView.as_view(), name="filter-options"),
]
