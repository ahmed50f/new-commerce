from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Category, Product, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'slug', 'parent', 'is_active',
        'created_at', 'updated_at'
    )
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)

    # Labels (قابلة للترجمة)
    def get_field_queryset(self, db, db_field, request):
        return super().get_field_queryset(db, db_field, request)

    name = _('Name')
    slug = _('Slug')
    parent = _('Parent Category')
    is_active = _('Active')
    created_at = _('Created at')
    updated_at = _('Updated at')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'slug', 'company', 'vendor', 'category',
        'price', 'stock', 'is_active', 'created_at', 'updated_at'
    )
    list_filter = ('is_active', 'company', 'vendor')
    search_fields = ('name', 'description', 'company__name', 'vendor__name')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')

    # Labels
    name = _('Name')
    slug = _('Slug')
    company = _('Company')
    vendor = _('Vendor')
    category = _('Category')
    price = _('Price')
    stock = _('Stock')
    is_active = _('Active')
    created_at = _('Created at')
    updated_at = _('Updated at')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'product__name', 'comment')

    # Labels
    user = _('User')
    product = _('Product')
    rating = _('Rating')
    created_at = _('Created at')
