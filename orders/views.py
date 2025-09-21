from rest_framework import viewsets, permissions, serializers, status
from rest_framework.response import Response
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from .models import Order, OrderItem, Transaction
from .serializers import OrderSerializer, OrderItemSerializer, TransactionSerializer
from accounts.models import Notification
from products.models import Product
import uuid
from .utils import calculate_shipping
from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.exceptions import NotFound
from orders.models import Transaction

# سعر الشحن لكل محافظة (تقريبًا حسب المسافة من القاهرة)
GOVERNORATE_SHIPPING_COST = {
    "Cairo": 20,
    "Giza": 25,
    "Alexandria": 35,
    "Dakahlia": 30,
    "Red_Sea": 50,
    "Beheira": 30,
    "Fayoum": 28,
    "Gharbia": 30,
    "Ismailia": 40,
    "Menofia": 28,
    "Minya": 32,
    "Qalyubia": 25,
    "New_Valley": 55,
    "Suez": 45,
    "Aswan": 60,
    "Assiut": 50,
    "Beni_Suef": 35,
    "Port_Said": 40,
    "Damietta": 40,
    "Sharkia": 35,
    "South_Sinai": 65,
    "Kafr_El_Sheikh": 30,
    "Matrouh": 70,
    "Luxor": 55,
    "Qena": 50,
    "North_Sinai": 60,
    "Sohag": 50,
}

def calculate_shipping(order):
    """
    تحسب سعر الشحن حسب المحافظة الموجودة في الطلب
    """
    if not order.governorate:
        return 50  # سعر افتراضي
    return GOVERNORATE_SHIPPING_COST.get(order.governorate, 50)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['customer', 'status']
    search_fields = ['customer__phone', 'status']

    def get_queryset(self):
        user = self.request.user
        # لو Vendor يشوف بس أوردرات شركته
        if getattr(user, "role", None) == "vendor":
            company = getattr(user, "company", None)
            if company is None:
                raise PermissionDenied(_("Vendors must be linked to a company."))
            return Order.objects.filter(company=company)

        # لو Client يشوف أوردراته بس
        return Order.objects.filter(customer=user)

    def perform_create(self, serializer):
        with transaction.atomic():
            user = self.request.user
            company = getattr(user, "company", None)
            order = serializer.save(customer=user, company=company)
            items_data = self.request.data.get("items", [])
            if not items_data:
                raise serializers.ValidationError({"items": _("You must provide at least one product.")})
            for item in items_data:
                product = Product.objects.get(id=item["product"])
                quantity = int(item.get("quantity", 1))
                OrderItem.objects.create(order=order, product=product, quantity=quantity)
            order.update_totals()  # حساب التوتال والشحن والإحداثيات



    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except NotFound:
            return Response(
                {"detail": _("الطلب غير موجود.")},
                status=status.HTTP_404_NOT_FOUND
            )

        # تحقق إن العميل أو الـ vendor يقدر يحذف الطلب
        user = request.user
        if getattr(user, "role", None) == "vendor":
            if instance.company != getattr(user, "company", None):
                raise PermissionDenied(_("مش مصرح لك بحذف هذا الطلب."))
        else:  # العميل
            if instance.customer != user:
                raise PermissionDenied(_("مش مصرح لك بحذف هذا الطلب."))

        self.perform_destroy(instance)
        return Response(
            {"detail": _("تم حذف الطلب بنجاح.")},
            status=status.HTTP_200_OK
        )

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]  # كل الناس لازم يكونوا مسجلين دخول
    filterset_fields = ["order", "product"]
    search_fields = ["order__id", "product__name"]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset().select_related("order", "product")

        if user.is_staff:
            return qs  # admin/staff يشوف الكل

        if getattr(user, "role", None) == "vendor":
            company = getattr(user, "company", None)
            return qs.filter(order__company=company) if company else qs.none()

        # client يشوف أوردراته بس
        return qs.filter(order__customer=user)

    def perform_create(self, serializer):
        order = serializer.validated_data.get("order")
        user = self.request.user

        # تأكد إن العميل مش بيضيف في أوردر مش بتاعه
        if not user.is_staff and order.customer != user:
            raise serializers.ValidationError("لا يمكنك إضافة منتجات لأوردر ليس ملكك.")

        serializer.save()
        

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # كل مستخدم يشوف المعاملات الخاصة بيه فقط
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        order = serializer.validated_data.get("order")

        if not order:
            raise serializers.ValidationError({"order_id": _("Order not found or invalid.")})

        # التحقق إن الـ order تابع للمستخدم الحالي
        if order.customer != self.request.user:
            raise serializers.ValidationError({"order_id": _("This order does not belong to you.")})

        # توليد reference_id فريد
        reference_id = str(uuid.uuid4()).replace("-", "")[:12]

        # إنشاء transaction
        transaction_obj = serializer.save(
            user=self.request.user,
            order=order,
            reference_id=reference_id
        )

        # إنشاء إشعارات حسب حالة الدفع
        if transaction_obj.status == "success":
            Notification.objects.create(
                user=self.request.user,
                sender=self.request.user,
                title=_("Payment Successful"),
                message=_("Your payment for Order #{} was successful.").format(order.id)
            )
        elif transaction_obj.status == "failed":
            Notification.objects.create(
                user=self.request.user,
                sender=self.request.user,
                title=_("Payment Failed"),
                message=_("Your payment for Order #{} has failed. Please try again.").format(order.id)
            )
    
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except NotFound:
            return Response(
                {"detail": _("المعاملة غير موجودة.")},
                status=status.HTTP_404_NOT_FOUND
            )
        # تحقق إن المعاملة تخص المستخدم الحالي
        if instance.user != request.user:
            raise PermissionDenied(_("مش مصرح لك بحذف هذه المعاملة."))
        self.perform_destroy(instance)
        return Response(
            {"detail": _("تم حذف المعاملة بنجاح.")},
            status=status.HTTP_200_OK
        )
    

def handle_payment_response(payment_gateway_response, transaction_id):
    try:
        transaction = Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        return {"error": "Transaction not found"}

    if payment_gateway_response['status'] == 'success':
        transaction.status = 'success'
    else:
        transaction.status = 'failed'

    transaction.save()
    return {"success": True, "status": transaction.status}