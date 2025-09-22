from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from accounts.models import Vendor
from accounts.models import Company
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _



# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='subcategories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    


class Product(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="products")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    slug = models.SlugField(unique=True, max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products", null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """تحقق من الحد الشهري للمنتجات حسب خطة الشركة"""
        limit = getattr(self.company, "plan_limit", None)
        if limit is not None:  # لو الخطة مش unlimited
            now = timezone.now()
            monthly_count = Product.objects.filter(
                company=self.company,
                created_at__year=now.year,
                created_at__month=now.month,
            ).exclude(pk=self.pk).count()  # استبعاد المنتج الحالي

            if self.pk is None and monthly_count >= limit:
                raise ValidationError(
                    _(f"You have reached the monthly limit ({limit}) for {self.company.subscription_plan} plan.")
                )

    def save(self, *args, **kwargs):
        self.full_clean()  # يتأكد من الـ validation
        super().save(*args, **kwargs)

   
    def discounted_price(self):
        if self.price and self.discount:
            discount_amount = (self.price * self.discount) / 100
            return self.price - discount_amount
        return self.price
    def __str__(self):
        return self.name


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    comment = models.TextField(blank=True, null=True)
    rating = models.FloatField(validators=[MinValueValidator(1.0), MaxValueValidator(5.0)])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating}"