from django.db import models
from django.conf import settings
from accounts.models import Company                                                                 
import uuid
from .utils import calculate_shipping
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
    governorate = models.CharField(max_length=50, choices=GOVERNORATE_CHOICES, null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    items_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def update_totals(self):
        items_total = sum(item.product.price * item.quantity for item in self.items.all())
        self.items_total = items_total
        self.total_amount = items_total + self.shipping_cost
        self.save()

    def __str__(self):
        return f"Order #{self.id} - {self.customer}"

    


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

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
        order_id = self.order.id if self.order else "N/A"
        return f"{self.user.username} - Order {order_id} - {self.amount} ({self.status})"
    

    reference_id = models.CharField(max_length=100, blank=True, null=True, unique=True)

    def save(self, *args, **kwargs):
        if self.order and (self.amount is None):
            self.amount = self.order.total_amount

        # توليد reference_id تلقائي لو مش موجود
        if not self.reference_id:
            self.reference_id = str(uuid.uuid4()).replace("-", "").upper()[:12]  # مثال: 12 حرف فريد
        super().save(*args, **kwargs)

    