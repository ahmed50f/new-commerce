from django.shortcuts import render
from .models import CustomUser, Vendor, UserProfile, Company, Notification
from .serializers import (
    CustomUserSerializer, VendorSerializer, RegisterSerializer,
    UserProfileSerializer, LoginSerializer, ChangePasswordSerializer, CompanySerializer, NotificationSerializer, NotificationCreateSerializer
)
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.conf import settings
from django.utils.crypto import get_random_string
from django.db import transaction
import time
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from .models import Vendor
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework import permissions

# ✅ Register View
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        try:
            with transaction.atomic():
                user = serializer.save()

                # ضبط الصلاحيات حسب الدور
                if user.role == 'vendor':
                    # إنشاء Vendor بدون أي حقول إضافية
                    Vendor.objects.create(user=user)
                    user.is_vendor = True
                    user.is_client = False
                    user.is_customer = False
                    user.save()
                elif user.role == 'client':
                    user.is_client = True
                    user.is_vendor = False
                    user.is_customer = False
                    user.save()
                else:  # Staff أو أي دور آخر
                    user.is_staff = True
                    user.is_active = True
                    user.save()

                data = {
                    'user': serializer.data,
                    'message': _('User registered successfully.'),
                }
                return Response(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                "detail": _("Registration failed."),
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ✅ Login View
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    phone = request.data.get("phone")
    password = request.data.get("password")
        
    try:
        user = CustomUser.objects.get(phone=phone)
        
        if not user.is_active:
            return Response({"detail": _("Account is not active. Please verify your phone number.")}, status=status.HTTP_400_BAD_REQUEST)

        if user.check_password(password):
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': _('Login Successfully'),
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_id': user.id,
                'phone': user.phone,
            }, status=status.HTTP_200_OK)
        else:
            return Response({"detail": _("Invalid credentials.")}, status=status.HTTP_401_UNAUTHORIZED)
    except CustomUser.DoesNotExist:
        return Response({"detail": _("User not found.")}, status=status.HTTP_404_NOT_FOUND)


# ✅ Logout View
@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": _("Refresh token is required.")}, status=status.HTTP_400_BAD_REQUEST)

        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"detail": _("Logged out successfully.")}, status=status.HTTP_200_OK)
    except Exception:
        return Response({"detail": _("Invalid token or already blacklisted.")}, status=status.HTTP_400_BAD_REQUEST)


# ✅ User Profile ViewSet
class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ✅ Company ViewSet
class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Company.objects.all()
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()   # هنا بيتحفظ
        data = self.get_serializer(instance).data   # هنا بيتعمل serialize للـ instance اللي اتحفظ
        return Response(data, status=status.HTTP_201_CREATED)
    
    
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except NotFound:
            return Response(
                {"detail": _("الشركة غير موجودة.")},
                status=status.HTTP_404_NOT_FOUND
            )

        # السماح بالمسح فقط للـ superuser أو staff (أو أي شرط تاني تحبه)
        if not request.user.is_staff:
            return Response(
                {"detail": _("مش مصرح لك بحذف الشركة دي.")},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_destroy(instance)
        return Response(
            {"detail": _("تم حذف الشركة بنجاح.")},
            status=status.HTTP_200_OK
        )
    

# Vendor ViewSet
class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # المستخدم العادي يشوف طلباته فقط
        if not user.is_staff:
            return Vendor.objects.filter(user=user)
        # الـ staff أو owner يشوف كل الطلبات
        return Vendor.objects.all()

    def perform_create(self, serializer):
        serializer.save(status="pending")

    # الموافقة على الطلب
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        request_obj = self.get_object()
        user = request.user

        if not user.is_staff:
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        # إنشاء Vendor بعد الموافقة
        Vendor.objects.create(
            user=request_obj.user,
            company=request_obj.company,
            role="staff"  # أو owner حسب المنطق
        )

        request_obj.status = "approved"
        request_obj.processed_at = timezone.now()
        request_obj.save()

        return Response({"detail": "Vendor request approved."})

    # رفض الطلب
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        request_obj = self.get_object()
        user = request.user

        if not user.is_staff:
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        request_obj.status = "rejected"
        request_obj.processed_at = timezone.now()
        request_obj.save()

        return Response({"detail": "Vendor request rejected."})
    
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except NotFound:
            return Response(
                {"detail": _("طلب الـ Vendor غير موجود.")},
                status=status.HTTP_404_NOT_FOUND
            )

        # السماح بالمسح فقط للـ superuser أو staff (أو أي شرط تاني تحبه)
        if not request.user.is_staff:
            return Response(
                {"detail": _("مش مصرح لك بحذف طلب الـ Vendor ده.")},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_destroy(instance)
        return Response(
            {"detail": _("تم حذف طلب الـ Vendor بنجاح.")},
            status=status.HTTP_200_OK
        )
    


# ✅ Custom User ViewSet
class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return CustomUser.objects.all()
        return CustomUser.objects.filter(id=user.id)

    def perform_create(self, serializer):   
        serializer.save()


# ✅ Forgot Password
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    phone = request.data.get("phone")

    if not phone:
        return Response({"detail": _("Phone number is required.")}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.get(phone=phone)
    except CustomUser.DoesNotExist:
        return Response({"detail": _("User not found.")}, status=status.HTTP_404_NOT_FOUND)

    reset_attempts = cache.get(f"forgot_password_attempts_{phone}", 0)
    wait_time = settings.WAIT_TIMES[min(reset_attempts, len(settings.WAIT_TIMES) - 1)]

    last_sent_time = cache.get(f"forgot_password_last_sent_{phone}")
    current_time = time.time()

    if last_sent_time and (current_time - last_sent_time) < wait_time:
        remaining_time = int(wait_time - (current_time - last_sent_time))
        return Response({
            "detail": _(f"Please wait {remaining_time} seconds before requesting a new OTP."),
            "wait_time": remaining_time
        }, status=429)

    new_otp = get_random_string(length=4, allowed_chars='0123456789')
    cache.set(f"forgot_password_otp_{phone}", new_otp, timeout=settings.OTP_TIMEOUT)
    cache.set(f"forgot_password_last_sent_{phone}", current_time, timeout=wait_time)
    cache.set(f"forgot_password_attempts_{phone}", reset_attempts + 1, timeout=86400)

    return Response({
        "message": _("OTP generated for password reset."),
        #"otp": new_otp,  # In production, send this via SMS instead of returning it
        "wait_time": wait_time
    }, status=status.HTTP_200_OK)


# ✅ Reset Password
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    phone = request.data.get("phone")
    otp = request.data.get("otp")
    new_password = request.data.get("new_password")

    if not phone or not otp or not new_password:
        return Response({"detail": _("Phone number, OTP, and new password are required.")}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.get(phone=phone)
    except CustomUser.DoesNotExist:
        return Response({"detail": _("User not found.")}, status=status.HTTP_404_NOT_FOUND)

    cached_otp = cache.get(f"forgot_password_otp_{phone}")
    if cached_otp != otp:
        return Response({"detail": _("Invalid or expired OTP.")}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()

    cache.delete(f"forgot_password_otp_{phone}")
    cache.delete(f"forgot_password_attempts_{phone}")
    cache.delete(f"forgot_password_last_sent_{phone}")

    return Response({"detail": _("Password reset successfully.")}, status=status.HTTP_200_OK)


# ✅ Change Password
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({"message": _("Password changed successfully.")}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Notification View
class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer

    def get_permissions(self):
        # كل المستخدمين مسموح لهم يشوفوا بس notifications الخاصة بيهم
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        # ارسال Notification فقط للمسؤولين / admin
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        # لو user عادي، يشوف بس notifications الخاصة بيه
        user = self.request.user
        if user.is_staff:
            return Notification.objects.all().order_by('-created_at')
        return user.notifications.all().order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return NotificationCreateSerializer
        return NotificationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification = serializer.save()
        return Response(NotificationSerializer(notification).data, status=status.HTTP_201_CREATED)
