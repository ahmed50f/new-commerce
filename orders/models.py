from django.db import models
from django.conf import settings
import uuid
from .utils import calculate_shipping
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("paid", _("Paid")),
        ("shipped", _("Shipped")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
    ]

    GOVERNORATE_CHOICES = [
        ("Cairo", _("Cairo")),
        ("Giza", _("Giza")),
        ("Alexandria", _("Alexandria")),
        ("Dakahlia", _("Dakahlia")),
        ("Red_Sea", _("Red Sea")),
        ("Beheira", _("Beheira")),
        ("Fayoum", _("Fayoum")),
        ("Gharbia", _("Gharbia")),
        ("Ismailia", _("Ismailia")),
        ("Menofia", _("Menofia")),
        ("Minya", _("Minya")),
        ("Qalyubia", _("Qalyubia")),
        ("New_Valley", _("New Valley")),
        ("Suez", _("Suez")),
        ("Aswan", _("Aswan")),
        ("Assiut", _("Assiut")),
        ("Beni_Suef", _("Beni Suef")),
        ("Port_Said", _("Port Said")),
        ("Damietta", _("Damietta")),
        ("Sharkia", _("Sharkia")),
        ("South_Sinai", _("South Sinai")),
        ("Kafr_El_Sheikh", _("Kafr El Sheikh")),
        ("Matrouh", _("Matrouh")),
        ("Luxor", _("Luxor")),
        ("Qena", _("Qena")),
        ("North_Sinai", _("North Sinai")),
        ("Sohag", _("Sohag")),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_orders",
        null=True,
        blank=True,
        verbose_name=_("Customer")
    )
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="orders",
        null=True,
        blank=True,
        verbose_name=_("Company")
    )
    governorate = models.CharField(
        max_length=50,
        choices=GOVERNORATE_CHOICES,
        default="Cairo",
        verbose_name=_("Governorate")
    )
    address = models.TextField(blank=True, null=True, verbose_name=_("Address"))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Shipping Cost"))
    items_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Items Total"))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Total Amount"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False, verbose_name=_("Discount Amount"))
    total_after_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False, verbose_name=_("Total After Discount"))
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_("Latitude"))
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_("Longitude"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name=_("Status"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def update_totals(self, include_shipping=True):
        items_total = sum(item.price for item in self.items.all())
        total_discount = sum(item.discount_amount for item in self.items.all())
        total_after_discount = items_total - total_discount

        self.items_total = items_total
        self.discount_amount = total_discount
        self.total_after_discount = total_after_discount

        if include_shipping:
            self.shipping_cost = calculate_shipping(self)

        self.total_amount = total_after_discount + self.shipping_cost
        self.save()

    def __str__(self):
        customer_info = f"{self.customer.phone} - {self.customer.email}" if self.customer else _("No Customer")
        return _("Order #{id} - {customer}").format(id=self.id, customer=customer_info)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE, verbose_name=_("Order"))
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, verbose_name=_("Product"))
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False, verbose_name=_("Price"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False, verbose_name=_("Discount Amount"))
    total_after_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False, verbose_name=_("Total After Discount"))

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")

    def clean(self):
        if self.product and self.product.stock < self.quantity:
            raise ValidationError(
                _("Requested quantity (%(qty)d) is not available in stock. Available: %(stock)d") %
                {"qty": self.quantity, "stock": self.product.stock}
            )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.price = self.product.price * self.quantity
        self.discount_amount = (self.price * self.product.discount) / 100 if self.product.discount > 0 else 0
        self.total_after_discount = self.price - self.discount_amount
        super().save(*args, **kwargs)

        if is_new:
            self.product.stock -= self.quantity
            self.product.save()

        self.order.update_totals()

    def get_total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return _("{qty} x {product}").format(qty=self.quantity, product=self.product)


@receiver(post_save, sender=OrderItem)
def update_order_totals(sender, instance, **kwargs):
    instance.order.update_totals()


class Transaction(models.Model):
    PAYMENT_METHODS = [
        ("visa", _("Visa / Mastercard")),
        ("paypal", _("PayPal")),
        ("fawry", _("Fawry")),
        ("wallet", _("Wallet")),
        ("cash_on_delivery", _("Cash on Delivery")),
        ("apple_pay", _("Apple Pay")),
    ]

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("success", _("Success")),
        ("failed", _("Failed")),
    ]

    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name="transactions", verbose_name=_("User"))
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name="transactions", blank=True, null=True, verbose_name=_("Order"))
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=False, verbose_name=_("Amount"))
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS, verbose_name=_("Payment Method"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name=_("Status"))
    reference_id = models.CharField(max_length=100, blank=True, null=True, unique=True, verbose_name=_("Reference ID"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")

    def save(self, *args, **kwargs):
        if self.order and (self.amount is None):
            self.amount = self.order.total_amount

        if not self.reference_id:
            self.reference_id = str(uuid.uuid4()).replace("-", "").upper()[:12]

        super().save(*args, **kwargs)

    def __str__(self):
        order_customer = self.order.customer if self.order and self.order.customer else None
        customer_info = order_customer.phone if order_customer else _("No Customer")
        status_display = dict(self.STATUS_CHOICES).get(self.status, self.status)
        return _("{customer} - Order {order} - {amount} ({status})").format(
            customer=customer_info,
            order=self.order.id if self.order else _("N/A"),
            amount=self.amount,
            status=status_display,
        )
