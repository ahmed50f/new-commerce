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
        (_("Personal Information"), {"fields": ("first_name", "last_name")}),
        (_("Roles & Permissions"), {
            "fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")
        }),
        (_("Important Dates"), {"fields": ("last_login", "date_joined")}),
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

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "subscription_plan", "plan_price", "plan_limit_display", "created_at")
    list_filter = ("subscription_plan", "created_at")
    search_fields = ("name", "tax_number")
    readonly_fields = ("plan_price", "created_at")

    def plan_limit_display(self, obj):
        return obj.plan_limit if obj.plan_limit is not None else _("Unlimited")
    plan_limit_display.short_description = _("Monthly Limit")

    class Meta:
        verbose_name = _("Company")
        verbose_name_plural = _("Companies")


@admin.register(Vendor)
class VendorRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "company", "status", "created_at", "processed_at")
    list_filter = ("status", "company", "created_at")
    search_fields = ("user__email", "user__phone", "company__name")
    readonly_fields = ("created_at", "processed_at")

    class Meta:
        verbose_name = _("Vendor Request")
        verbose_name_plural = _("Vendor Requests")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "get_recipients", "created_at", "read")
    list_filter = ("read", "created_at")
    search_fields = ("title", "message", "recipients__email")
    actions = ["send_to_all"]
    readonly_fields = ("created_at",)

    def get_recipients(self, obj):
        return ", ".join([user.email for user in obj.recipients.all()])
    get_recipients.short_description = _("Recipients")

    def send_to_all(self, request, queryset):
        for notification in queryset:
            notification.recipients.set(CustomUser.objects.all())
        self.message_user(request, _("Recipients set to all users."))
    send_to_all.short_description = _("Send selected notifications to all users")

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")


# Register Custom User
admin.site.register(CustomUser, CustomUserAdmin)
