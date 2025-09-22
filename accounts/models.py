from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import random, string
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


class CustomUserManager(BaseUserManager):
    def create_user(self, phone, email, password=None, **extra_fields):
        if not phone:
            raise ValueError(_("The phone number must be set"))
        if not email:
            raise ValueError(_("The email must be set"))

        email = self.normalize_email(email)
        user = self.model(phone=phone, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(phone, email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None 

    USER_TYPES = (
        ("vendor", _("Vendor")),
        ("client", _("Client")),
        ("admin", _("Admin")),
    )

    email = models.EmailField(_("Email"), unique=True)
    phone = models.CharField(_("Phone"), max_length=20, unique=True)
    is_customer = models.BooleanField(_("Is Customer"), default=True)
    is_vendor = models.BooleanField(_("Is Vendor"), default=False)
    is_client = models.BooleanField(_("Is Client"), default=False)
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_staff = models.BooleanField(_("Is Staff"), default=False)
    role = models.CharField(_("Role"), max_length=100, choices=USER_TYPES, default="client")

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["email"]

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.phone} - {self.email}"

    class Meta:
        verbose_name = _("Custom User")
        verbose_name_plural = _("Custom Users")


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile', verbose_name=_("User"))
    full_name = models.CharField(_("Full Name"), max_length=255, blank=True, null=True)
    profile_image = models.ImageField(_("Profile Image"), upload_to='profiles/', blank=True, null=True)
    address = models.TextField(_("Address"), blank=True, null=True)
    bio = models.TextField(_("Bio"), blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} {_('Profile')}"

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")


class Company(models.Model):
    SUBSCRIPTION_CHOICES = [
        ("free", _("Free")),
        ("basic", _("Basic")),
        ("premium", _("Premium")),
    ]

    PLAN_PRICES = {
        "free": 0,
        "basic": 100,
        "premium": 300,
    }

    PLAN_LIMITS = {
        "free": 10,
        "basic": 100,
        "premium": None,
    }

    name = models.CharField(_("Company Name"), max_length=255)
    tax_number = models.CharField(_("Tax Number"), max_length=100, blank=True, null=True)
    logo = models.ImageField(_("Logo"), upload_to="companies/logos/", blank=True, null=True)
    address = models.TextField(_("Address"), blank=True, null=True)
    subscription_plan = models.CharField(
        _("Subscription Plan"), max_length=50, choices=SUBSCRIPTION_CHOICES, default="free"
    )
    plan_price = models.DecimalField(_("Plan Price"), max_digits=10, decimal_places=2, default=0)  
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.subscription_plan})"

    def save(self, *args, **kwargs):
        self.plan_price = self.PLAN_PRICES.get(self.subscription_plan, 0)
        super().save(*args, **kwargs)

    @property
    def plan_limit(self):
        """يرجع الحد الشهري المسموح به حسب الخطة"""
        return self.PLAN_LIMITS.get(self.subscription_plan)

    class Meta:
        verbose_name = _("Company")
        verbose_name_plural = _("Companies")


class Vendor(models.Model):
    STATUS_CHOICES = (
        ("pending", _("Pending")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendor_requests", verbose_name=_("User")
    )
    company = models.ForeignKey("Company", on_delete=models.CASCADE, verbose_name=_("Company"))
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    processed_at = models.DateTimeField(_("Processed At"), null=True, blank=True)

    class Meta:
        unique_together = ("user", "company")
        verbose_name = _("Vendor Request")
        verbose_name_plural = _("Vendor Requests")

    def __str__(self):
        return f"{self.user.email} -> {self.company.name} ({self.status})"


class OTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("User"))
    code = models.CharField(_("Code"), max_length=4, blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    is_used = models.BooleanField(_("Is Used"), default=False)

    class Meta: 
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]
        verbose_name = _("OTP")
        verbose_name_plural = _("OTPs")

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join(random.choices(string.digits, k=4))
        super().save(*args, **kwargs)

    def clean(self):
        if not self.code.isdigit():
            raise ValidationError(_("The code must be digits only."))
        if len(self.code) != 4:
            raise ValidationError(_("The code must be exactly 4 digits."))
    
    def __str__(self):
        return f"{self.user.email} - {self.code}"


User = get_user_model()
class Notification(models.Model):
    title = models.CharField(_("Title"), max_length=255)
    message = models.TextField(_("Message"))
    recipients = models.ManyToManyField(User, related_name="notifications", verbose_name=_("Recipients"))
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    read = models.BooleanField(_("Read"), default=False)

    def __str__(self):
        return f"{self.title} ({self.created_at})"

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
    
    def send_global_notification(title, message):
        notification = Notification.objects.create(title=title, message=message)
        users = User.objects.all()
        notification.recipients.set(users)
        notification.save()
        return notification
    
    def send_user_notification(user, title, message):
        notification = Notification.objects.create(title=title, message=message)
        notification.recipients.add(user)
        notification.save()
        return notification
