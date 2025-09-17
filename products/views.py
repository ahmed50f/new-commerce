from django.shortcuts import render
from .models import Product, Category, Review
from .serializers import ProductSerializer, CategorySerializer, ReviewSerializer
from rest_framework import viewsets, permissions
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets, permissions, serializers
from accounts.models import Vendor
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from rest_framework.exceptions import NotFound
# Create your views here.
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except NotFound:
            return Response(
                {"detail": _("التصنيف غير موجود.")},
                status=status.HTTP_404_NOT_FOUND
            )

        self.perform_destroy(instance)
        return Response(
            {"detail": _("تم حذف التصنيف بنجاح.")},
            status=status.HTTP_200_OK
        )

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name']

    def perform_create(self, serializer):
        user = self.request.user

        # تحقق إن الـ user عنده vendor
        if not hasattr(user, "vendor"):
            raise serializers.ValidationError(
                {"vendor": _("هذا المستخدم ليس Vendor ولا يمكنه إضافة منتجات.")}
            )

        vendor = user.vendor

        # تحقق إن الـ vendor مربوط بشركة
        if not vendor.company:
            raise serializers.ValidationError(
                {"company": _("الـ Vendor لازم يكون مرتبط بشركة قبل إضافة منتجات.")}
            )

        serializer.save(vendor=vendor, company=vendor.company)

    
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except NotFound:
            return Response(
                {"detail": _("المنتج غير موجود.")},
                status=status.HTTP_404_NOT_FOUND
            )

        self.perform_destroy(instance)
        return Response(
            {"detail": _("تم حذف المنتج بنجاح.")},
            status=status.HTTP_200_OK
        )
    # موجود مؤقت لاختبار ال post 
    # def perform_create(self, serializer):
    #     user = self.request.user
    #     vendor = getattr(user, "vendor", None)

    #     if not vendor:
    #     # مؤقتًا اربط المنتج بأول Vendor موجود
    #         vendor = Vendor.objects.first()

    #         serializer.save(vendor=vendor, company=vendor.company)

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except NotFound:
            return Response(
                {"detail": _("التقييم غير موجود.")},
                status=status.HTTP_404_NOT_FOUND
            )
        if instance.user != request.user:
            return Response(
                {"detail": _("مش مصرح لك تحذف التقييم ده.")},
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_destroy(instance)
        return Response(
            {"detail": _("تم حذف التقييم بنجاح.")},
            status=status.HTTP_200_OK
        )