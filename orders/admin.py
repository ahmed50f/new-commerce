from django.contrib import admin
from .models import Order, OrderItem, Transaction
from django.core.exceptions import ValidationError
from django import forms


class OrderItemInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        has_items = any(
            form.cleaned_data and not form.cleaned_data.get("DELETE", False)
            for form in self.forms
        )
        if not has_items:
            raise ValidationError("Order must contain at least one product.")

        # تحقق أن كل المنتجات من نفس الشركة
        order_company = self.instance.company
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                product = form.cleaned_data.get("product")
                if product and product.company != order_company:
                    raise ValidationError(
                        f"Product '{product.name}' does not belong to company '{order_company.name}'."
                    )



class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    formset = OrderItemInlineFormSet


class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "customer", "company", "status",
        "items_total", "shipping_cost", 
        "discount_percentage", "total_amount", "created_at"
    )
    list_filter = ("status", "company", "created_at")
    search_fields = ("customer__phone", "company__name")
    inlines = [OrderItemInline]
    readonly_fields = ("items_total", "shipping_cost", "discount_amount", "total_after_discount", "total_amount")

    # دالة لحساب نسبة الخصم مباشرة من OrderItem
    def discount_percentage(self, obj):
        items_total = sum(item.price for item in obj.items.all())
        total_discount = sum(item.discount_amount for item in obj.items.all())
        if items_total > 0:
            return round((total_discount / items_total) * 100, 2)
        return 0
    discount_percentage.short_description = "Discount (%)"

    # بعد حفظ الـ items نحدث التوتال
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.update_totals()
admin.site.register(Order, OrderAdmin)



class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'order', 'amount', 'method', 'status', 'reference_id', 'created_at']
    list_filter = ['status', 'method', 'created_at']
    search_fields = ['user__phone', 'reference_id']

admin.site.register(Transaction, TransactionAdmin)