
from .views import ProductViewSet, CategoryViewSet, ReviewViewSet
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'Products', ProductViewSet, basename='products')
router.register(r'Category', CategoryViewSet, basename='categories')
router.register(r'reviews', ReviewViewSet, basename='reviews')
urlpatterns = [
    path('', include(router.urls)),
]
