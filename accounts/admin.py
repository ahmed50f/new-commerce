
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, UserProfile, Company, Vendor, OTP, Notification



class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("id", "phone", "email", "role", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "role")
    search_fields = ("phone", "email")
    ordering = ("id",)

    fieldsets = (
        (None, {"fields": ("phone", "email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (_("Roles & Permissions"), {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "email", "password1", "password2", "role", "is_active", "is_staff"),
        }),
    )



@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "full_name")
    search_fields = ("full_name", "user__email", "user__phone")



@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "subscription_plan", "plan_price", "plan_limit", "created_at")
    list_filter = ("subscription_plan", "created_at")
    search_fields = ("name", "tax_number")
    readonly_fields = ("plan_price", "created_at")

    def plan_limit(self, obj):
        """عرض الحد الشهري في الجدول"""
        return obj.plan_limit if obj.plan_limit is not None else "Unlimited"
    plan_limit.short_description = "Monthly Limit"


@admin.register(Vendor)
class VendorRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "company", "status", "created_at", "processed_at")
    list_filter = ("status", "company", "created_at")
    search_fields = ("user__username", "user__email", "company__name")
    readonly_fields = ("created_at", "processed_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    # الأعمدة اللي هتظهر في اللائحة
    list_display = ("id", "title", "get_recipients", "created_at", "read")
    
    # الفلاتر الجانبية
    list_filter = ("read", "created_at")
    
    # البحث
    search_fields = ("title", "message", "recipients__email")

    actions = ['send_to_all']

    # طريقة عرض المستلمين
    def get_recipients(self, obj):
        return ", ".join([user.email for user in obj.recipients.all()])
    get_recipients.short_description = "Recipients"

    # اجعل بعض الحقول readonly
    readonly_fields = ("created_at",)


    def send_to_all(self, request, queryset):
        for notification in queryset:
            notification.recipients.settings.AUTH_USER_MODEL.objects.all()
        self.message_user(request, "تم تعيين المستلمين إلى الجميع.")
    send_to_all.short_description = "إرسال المحدد للجميع"


# Register Custom User
admin.site.register(CustomUser, CustomUserAdmin)
