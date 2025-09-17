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


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "customer", "company", "status",
        "items_total", "shipping_cost", "total_amount", "created_at"
    )
    list_filter = ("status", "company", "created_at")
    search_fields = ("customer__phone", "company__name")
    inlines = [OrderItemInline]
    readonly_fields = ("items_total", "shipping_cost", "total_amount")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # بعد ما يتحفظوا الـ items نعمل update totals
        form.instance.update_totals()



class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'order', 'amount', 'method', 'status', 'reference_id', 'created_at']
    list_filter = ['status', 'method', 'created_at']
    search_fields = ['user__phone', 'reference_id']

admin.site.register(Transaction, TransactionAdmin)