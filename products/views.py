from django.shortcuts import render
from django.http import Http404
from rest_framework import viewsets, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django.utils.translation import gettext_lazy as _

from .models import Product, Category, Review
from .serializers import ProductSerializer, CategorySerializer, ReviewSerializer
from accounts.models import Vendor


class CategoryViewSet(viewsets.ModelViewSet):
    """Manage categories (CRUD)"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except NotFound:
            return Response(
                {"detail": _("Category not found.")},
                status=status.HTTP_404_NOT_FOUND
            )

        self.perform_destroy(instance)
        return Response(
            {"detail": _("Category deleted successfully.")},
            status=status.HTTP_200_OK
        )


class ProductViewSet(viewsets.ModelViewSet):
    """Manage products (CRUD)"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name']

    def perform_create(self, serializer):
        user = self.request.user

        if not hasattr(user, "vendor"):
            raise serializers.ValidationError(
                {"vendor": _("This user is not a Vendor and cannot add products.")}
            )

        vendor = user.vendor

        if not vendor.company:
            raise serializers.ValidationError(
                {"company": _("Vendor must be linked to a company before adding products.")}
            )

        serializer.save(vendor=vendor, company=vendor.company)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except NotFound:
            return Response(
                {"detail": _("Product not found.")},
                status=status.HTTP_404_NOT_FOUND
            )

        self.perform_destroy(instance)
        return Response(
            {"detail": _("Product deleted successfully.")},
            status=status.HTTP_200_OK
        )


class ReviewViewSet(viewsets.ModelViewSet):
    """Manage reviews (CRUD)"""
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
                {"detail": _("Review not found.")},
                status=status.HTTP_404_NOT_FOUND
            )

        if instance.user != request.user:
            return Response(
                {"detail": _("You are not allowed to delete this review.")},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_destroy(instance)
        return Response(
            {"detail": _("Review deleted successfully.")},
            status=status.HTTP_200_OK
        )
