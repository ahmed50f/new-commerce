from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Product, Category, Review


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'parent', 'is_active']
        read_only_fields = ['id']
        extra_kwargs = {
            'name': {'error_messages': {'required': _("Name is required.")}},
            'slug': {'error_messages': {'required': _("Slug is required.")}},
        }


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        error_messages={
            "required": _("Category is required."),
            "does_not_exist": _("Invalid category."),
            "incorrect_type": _("Category ID must be an integer."),
        },
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'stock', 
            'is_active', 'category', 'category_id', 'image', 
            'created_at', 'updated_at', 'discount', 'discounted_price'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_discounted_price(self, obj):
        return obj.discounted_price()


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    product = serializers.StringRelatedField(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True,
        error_messages={
            "required": _("Product is required."),
            "does_not_exist": _("Invalid product."),
            "incorrect_type": _("Product ID must be an integer."),
        },
    )

    class Meta:
        model = Review
        fields = ['id', 'product', 'product_id', 'user', 'rating', 'comment', 'created_at']  
        read_only_fields = ['id', 'created_at', 'user', 'product']
        extra_kwargs = {
            'rating': {'error_messages': {'required': _("Rating is required.")}},
            'comment': {'error_messages': {'required': _("Comment is required.")}},
        }
