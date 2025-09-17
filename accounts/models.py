from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import random, string
from django.core.exceptions import ValidationError
# Create your models here.
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
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

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True)
    is_customer = models.BooleanField(default=True)
    is_vendor = models.BooleanField(default=False)
    is_client = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    role = models.CharField(max_length=100, choices=USER_TYPES, default="client")

    USERNAME_FIELD = "phone"       #  تسجيل الدخول بالـ phone
    REQUIRED_FIELDS = ["email"]

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.phone} - {self.email}"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} Profile"

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
        "free": 10,       # 10 منتجات في الشهر
        "basic": 100,     # 100 منتج في الشهر
        "premium": None,  # بدون حدود
    }

    name = models.CharField(max_length=255)
    tax_number = models.CharField(max_length=100, blank=True, null=True)
    logo = models.ImageField(upload_to="companies/logos/", blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    subscription_plan = models.CharField(
        max_length=50, choices=SUBSCRIPTION_CHOICES, default="free"
    )
    plan_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.subscription_plan})"

    def save(self, *args, **kwargs):
        # السعر يتحدد تلقائيًا من الخطة
        self.plan_price = self.PLAN_PRICES.get(self.subscription_plan, 0)
        super().save(*args, **kwargs)

    @property
    def plan_limit(self):
        """يرجع الحد الشهري المسموح به حسب الخطة"""
        return self.PLAN_LIMITS.get(self.subscription_plan)


class Vendor(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendor_requests"
    )
    company = models.ForeignKey("Company", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "company")  # يمنع إرسال طلب مكرر

    def __str__(self):
        return f"{self.user.email} -> {self.company.name} ({self.status})"



########derre
# OTP Model
class OTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=4, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta: 
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]


    def save(self, *args, **kwargs):
        if not self.code:
            # توليد كود OTP عشوائي مكون من 4 أرقام
            self.code = ''.join(random.choices(string.digits, k=4))
        super().save(*args, **kwargs)

    def clean(self):
        # تحقق إنه أرقام فقط وطوله 4 أرقام
        if not self.code.isdigit():
            raise ValidationError(_("الكود لازم يكون أرقام فقط."))
        if len(self.code) != 4:
            raise ValidationError(_("الكود لازم يكون مكون من 4 أرقام بالظبط."))
    
    def __str__(self):
        return f"{self.user.email} - {self.code}"
    
User = get_user_model()
class Notification(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    recipients = models.ManyToManyField(User, related_name="notifications")
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({self.created_at})"
    
    def send_global_notification(title, message):
        notification = Notification.objects.create(title=title, message=message)
        users = User.objects.all()  # كل المستخدمين
        notification.recipients.set(users)
        notification.save()
        return notification
    
    def send_user_notification(user, title, message):
        notification = Notification.objects.create(title=title, message=message)
        notification.recipients.add(user)
        notification.save()
        return notification


    