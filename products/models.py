from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from accounts.models import Vendor, Company
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(_("Name"), max_length=100)
    slug = models.SlugField(_("Slug"), unique=True)
    description = models.TextField(_("Description"), blank=True, null=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='subcategories',
        verbose_name=_("Parent Category")
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return str(self.name)


class Product(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name=_("Company")
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name=_("Vendor")
    )
    name = models.CharField(_("Name"), max_length=255)
    image = models.ImageField(_("Image"), upload_to='products/', blank=True, null=True)
    slug = models.SlugField(_("Slug"), unique=True, max_length=255)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
        null=True,
        blank=True,
        verbose_name=_("Category")
    )
    description = models.TextField(_("Description"), blank=True, null=True)
    price = models.DecimalField(_("Price"), max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(_("Stock"), default=0)
    discount = models.DecimalField(_("Discount (%)"), max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def clean(self):
        """تحقق من الحد الشهري للمنتجات حسب خطة الشركة"""
        limit = getattr(self.company, "plan_limit", None)
        if limit is not None:  # لو الخطة مش unlimited
            now = timezone.now()
            monthly_count = Product.objects.filter(
                company=self.company,
                created_at__year=now.year,
                created_at__month=now.month,
            ).exclude(pk=self.pk).count()

            if self.pk is None and monthly_count >= limit:
                raise ValidationError(
                    _("You have reached the monthly limit ({limit}) for {plan} plan.").format(
                        limit=limit,
                        plan=_(self.company.subscription_plan)
                    )
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
        return (self.name)


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("User")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name=_("Product")
    )
    comment = models.TextField(_("Comment"), blank=True, null=True)
    rating = models.FloatField(
        _("Rating"),
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)]
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")

    def __str__(self):
        return _("{user} - {product} - {rating}").format(
            user=self.user.username,
            product=self.product.name,
            rating=self.rating
        )
