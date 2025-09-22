from rest_framework import serializers
from .models import Order, OrderItem, Transaction
from products.serializers import ProductSerializer
from products.models import Product
from django.utils.translation import gettext_lazy as _


class OrderItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(
        source="product",
        read_only=True,
        label=_("Product Details")
    )

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_detail", "quantity"]
        read_only_fields = ["id", "product_detail"]
        extra_kwargs = {
            "product": {"label": _("Product")},
            "quantity": {"label": _("Quantity")},
        }


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, label=_("Order Items"))

    class Meta:
        model = Order
        fields = [
            "id", "company", "governorate", "address",
            "shipping_cost", "items", "items_total",
            "total_amount", "discount_amount", "total_after_discount",
            "status", "created_at",
        ]
        read_only_fields = [
            "id", "created_at", "customer",
            "items_total", "total_amount",
        ]
        extra_kwargs = {
            "company": {"label": _("Company")},
            "governorate": {"label": _("Governorate")},
            "address": {"label": _("Address")},
            "shipping_cost": {"label": _("Shipping Cost")},
            "items_total": {"label": _("Items Total")},
            "total_amount": {"label": _("Total Amount")},
            "discount_amount": {"label": _("Discount Amount")},
            "total_after_discount": {"label": _("Total After Discount")},
            "status": {"label": _("Status")},
            "created_at": {"label": _("Created At")},
        }

    def validate_items(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError(
                _("Order must contain at least one product.")
            )
        return value

    def validate(self, attrs):
        """تأكد أن كل المنتجات من نفس الشركة المحددة في الأوردر"""
        company = attrs.get("company")
        items = self.initial_data.get("items", [])

        if company and items:
            for item in items:
                product = Product.objects.get(pk=item["product"])
                if product.company != company:
                    raise serializers.ValidationError(
                        _("Product '{product}' does not belong to company '{company}'.").format(
                            product=product.name,
                            company=company.name,
                        )
                    )
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        validated_data.pop("customer", None)
        user = self.context["request"].user
        order = Order.objects.create(customer=user, **validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        order.update_totals()  # تحديث التوتال مع حساب الشحن
        return order

    def update(self, instance, validated_data):
        instance.governorate = validated_data.get("governorate", instance.governorate)
        instance.status = validated_data.get("status", instance.status)
        instance.address = validated_data.get("address", instance.address)
        # لا تحدث shipping_cost من هنا لأنه محسوب تلقائيًا
        instance.save()
        instance.update_totals()
        return instance


class TransactionSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True, label=_("Order"))
    order_id = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.all(),
        source="order",
        write_only=True,
        label=_("Order ID"),
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "order",
            "order_id",
            "user",
            "amount",
            "method",
            "status",
            "reference_id",
            "created_at",
        ]
        read_only_fields = ["id", "user", "reference_id", "created_at"]
        extra_kwargs = {
            "user": {"label": _("User")},
            "amount": {"label": _("Amount")},
            "method": {"label": _("Payment Method")},
            "status": {"label": _("Status")},
            "reference_id": {"label": _("Reference ID")},
            "created_at": {"label": _("Created At")},
        }
