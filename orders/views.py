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
from rest_framework.exceptions import NotFound

# سعر الشحن لكل محافظة (تقريبًا حسب المسافة من القاهرة)
GOVERNORATE_SHIPPING_COST = {
    _("Cairo"): 20,
    _("Giza"): 25,
    _("Alexandria"): 35,
    _("Dakahlia"): 30,
    _("Red Sea"): 50,
    _("Beheira"): 30,
    _("Fayoum"): 28,
    _("Gharbia"): 30,
    _("Ismailia"): 40,
    _("Menofia"): 28,
    _("Minya"): 32,
    _("Qalyubia"): 25,
    _("New Valley"): 55,
    _("Suez"): 45,
    _("Aswan"): 60,
    _("Assiut"): 50,
    _("Beni Suef"): 35,
    _("Port Said"): 40,
    _("Damietta"): 40,
    _("Sharkia"): 35,
    _("South Sinai"): 65,
    _("Kafr El Sheikh"): 30,
    _("Matrouh"): 70,
    _("Luxor"): 55,
    _("Qena"): 50,
    _("North Sinai"): 60,
    _("Sohag"): 50,
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
        if getattr(user, "role", None) == "vendor":
            company = getattr(user, "company", None)
            if company is None:
                raise PermissionDenied(_("Vendors must be linked to a company."))
            return Order.objects.filter(company=company)

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
            order.update_totals()


    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except NotFound:
            return Response(
                {"detail": _("Order not found.")},
                status=status.HTTP_404_NOT_FOUND
            )

        user = request.user
        if getattr(user, "role", None) == "vendor":
            if instance.company != getattr(user, "company", None):
                raise PermissionDenied(_("You are not authorized to delete this order."))
        else:
            if instance.customer != user:
                raise PermissionDenied(_("You are not authorized to delete this order."))

        self.perform_destroy(instance)
        return Response(
            {"detail": _("Order deleted successfully.")},
            status=status.HTTP_200_OK
        )


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["order", "product"]
    search_fields = ["order__id", "product__name"]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset().select_related("order", "product")

        if user.is_staff:
            return qs

        if getattr(user, "role", None) == "vendor":
            company = getattr(user, "company", None)
            return qs.filter(order__company=company) if company else qs.none()

        return qs.filter(order__customer=user)

    def perform_create(self, serializer):
        order = serializer.validated_data.get("order")
        user = self.request.user

        if not user.is_staff and order.customer != user:
            raise serializers.ValidationError(_("You cannot add items to an order that is not yours."))

        serializer.save()
        

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        order = serializer.validated_data.get("order")

        if not order:
            raise serializers.ValidationError({"order_id": _("Order not found or invalid.")})

        if order.customer != self.request.user:
            raise serializers.ValidationError({"order_id": _("This order does not belong to you.")})

        reference_id = str(uuid.uuid4()).replace("-", "")[:12]

        transaction_obj = serializer.save(
            user=self.request.user,
            order=order,
            reference_id=reference_id
        )

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
                {"detail": _("Transaction not found.")},
                status=status.HTTP_404_NOT_FOUND
            )
        if instance.user != request.user:
            raise PermissionDenied(_("You are not authorized to delete this transaction."))
        self.perform_destroy(instance)
        return Response(
            {"detail": _("Transaction deleted successfully.")},
            status=status.HTTP_200_OK
        )
    

def handle_payment_response(payment_gateway_response, transaction_id):
    try:
        transaction = Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        return {"error": _("Transaction not found")}

    if payment_gateway_response['status'] == 'success':
        transaction.status = 'success'
    else:
        transaction.status = 'failed'

    transaction.save()
    return {"success": True, "status": transaction.status}
