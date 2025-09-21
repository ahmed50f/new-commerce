from django.db import models
from django.conf import settings                                                               
import uuid
from .utils import calculate_shipping
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError   

# Create your models here.


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("shipped", "Shipped"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    GOVERNORATE_CHOICES = [
        ("Cairo", "Cairo"),
        ("Giza", "Giza"),
        ("Alexandria", "Alexandria"),
        ("Dakahlia", "Dakahlia"),
        ("Red_Sea", "Red Sea"),
        ("Beheira", "Beheira"),
        ("Fayoum", "Fayoum"),
        ("Gharbia", "Gharbia"),
        ("Ismailia", "Ismailia"),
        ("Menofia", "Menofia"),
        ("Minya", "Minya"),
        ("Qalyubia", "Qalyubia"),
        ("New_Valley", "New Valley"),
        ("Suez", "Suez"),
        ("Aswan", "Aswan"),
        ("Assiut", "Assiut"),
        ("Beni_Suef", "Beni Suef"),
        ("Port_Said", "Port Said"),
        ("Damietta", "Damietta"),
        ("Sharkia", "Sharkia"),
        ("South_Sinai", "South Sinai"),
        ("Kafr_El_Sheikh", "Kafr El Sheikh"),
        ("Matrouh", "Matrouh"),
        ("Luxor", "Luxor"),
        ("Qena", "Qena"),
        ("North_Sinai", "North Sinai"),
        ("Sohag", "Sohag"),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_orders",
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="orders",
        null=True,
        blank=True
    )
    governorate = models.CharField(max_length=50, choices=GOVERNORATE_CHOICES, default="Cairo")
    address = models.TextField(blank=True, null=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    items_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    total_after_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def update_totals(self, include_shipping=True):
        # اجمع كل الأسعار قبل الخصم
        items_total = sum(item.price for item in self.items.all())

        # اجمع كل الخصومات
        total_discount = sum(item.discount_amount for item in self.items.all())

        # السعر بعد الخصم
        total_after_discount = items_total - total_discount

        self.items_total = items_total
        self.total_discount = total_discount
        self.total_after_discount = total_after_discount

        # حساب الشحن لو مطلوب
        if include_shipping:
            self.shipping_cost = calculate_shipping(self)

        # المجموع النهائي مع الشحن
        self.total_amount = total_after_discount + self.shipping_cost

        self.save()


    def __str__(self):
        if self.customer:
            customer_info = f"{self.customer.phone} - {self.customer.email}"
        else:
            customer_info = "No Customer"
        return f"Order #{self.id} - {customer_info}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)  # السعر قبل الخصم
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    total_after_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    def clean(self):
        # التحقق من الكمية قبل الحفظ
        if self.product and self.product.stock < self.quantity:
            raise ValidationError("الكمية المطلوبة غير متوفرة في المخزون")

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # لو أول مرة بيتسجل

        # حساب السعر قبل الخصم
        self.price = self.product.price * self.quantity

        # حساب الخصم
        if self.product.discount > 0:
            self.discount_amount = (self.price * self.product.discount) / 100
        else:
            self.discount_amount = 0

        # السعر بعد الخصم
        self.total_after_discount = self.price - self.discount_amount

        super().save(*args, **kwargs)

        # تحديث الـ stock لو أول مرة
        if is_new:
            self.product.stock -= self.quantity
            self.product.save()

        # تحديث المجموع في الـ Order
        self.order.update_totals()

    def get_total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product}"


# Signal لتحديث التوتال بعد إضافة/تعديل OrderItem
@receiver(post_save, sender=OrderItem)
def update_order_totals(sender, instance, **kwargs):
    instance.order.update_totals()


class Transaction(models.Model):
    PAYMENT_METHODS = [
        ("visa", "Visa / Mastercard"),
        ("paypal", "PayPal"),
        ("fawry", "Fawry"),
        ("wallet", "Wallet"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name="transactions")
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name="transactions", blank=True, null=True)  
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=False)  
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reference_id = models.CharField(max_length=100, blank=True, null=True)  
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # لو ال amount مش محدد و فيه order
        if self.order and (self.amount is None):
            self.amount = self.order.total_amount  # غير total_amount لو الحقل عندك اسمه مختلف
        super().save(*args, **kwargs)

    def __str__(self):
        order_customer = self.order.customer if self.order and self.order.customer else None
        customer_info = order_customer.phone if order_customer else "No Customer"
        return f"{customer_info} - Order {self.order.id} - {self.amount} ({self.status})"

    

    reference_id = models.CharField(max_length=100, blank=True, null=True, unique=True)

    def save(self, *args, **kwargs):
        if self.order and (self.amount is None):
            self.amount = self.order.total_amount

        # توليد reference_id تلقائي لو مش موجود
        if not self.reference_id:
            self.reference_id = str(uuid.uuid4()).replace("-", "").upper()[:12]  # مثال: 12 حرف فريد
        super().save(*args, **kwargs)