from rest_framework import serializers
from .models import CustomUser,Vendor, UserProfile, Notification, Company
from django.utils.translation import gettext_lazy as _
from .models import OTP
from django.contrib.auth import get_user_model



class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'phone', 'is_customer', 'is_vendor', 'is_client','is_active', 'is_staff', 'role']
        read_only_fields = ['id', 'is_active', 'is_staff']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = CustomUser(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
class CompanySerializer(serializers.ModelSerializer):
    plan_limit = serializers.ReadOnlyField()  # خاصية (property) مش field في DB

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "tax_number",
            "logo",
            "address",
            "subscription_plan",
            "plan_price",
            "plan_limit",
            "created_at",
        ]
        read_only_fields = ["plan_price", "plan_limit", "created_at"]

class VendorSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Vendor
        fields = "__all__"
        read_only_fields = ("status", "created_at", "processed_at")

    def validate(self, attrs):
        user = self.context["request"].user
        company = attrs.get("company")

        # لو المستخدم عنده Vendor بالفعل للشركة دي
        from .models import Vendor
        if hasattr(user, "vendor_profile") and user.vendor_profile.company == company:
            raise serializers.ValidationError(
                {"detail": _("You are already a vendor for this company.")}
            )
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'full_name', 'address', 'profile_image']
        read_only_fields = ['id', 'user']

# REGISTER SERIALIZER

class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = CustomUser
        fields = ['email', 'phone', 'role', 'password', 'password2', 'name']

    def validate(self, attrs):
        # تحقق من طول الباسورد
        if not (6 <= len(attrs['password']) <= 16):
            raise serializers.ValidationError({"detail": _("كلمة المرور لازم تكون بين 6 و 16 حرف.")})

        # تحقق من تطابق الباسورد
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": _("كلمتا المرور مش متطابقتين.")})

        # تحقق من تكرار الهاتف
        if CustomUser.objects.filter(phone=attrs['phone']).exists():
            raise serializers.ValidationError({"phone": _("رقم الهاتف مستخدم بالفعل.")})

        # تحقق من تكرار الايميل
        if CustomUser.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": _("البريد الإلكتروني مستخدم بالفعل.")})

        return attrs

    def create(self, validated_data):
        name = validated_data.pop('name', None)   # ناخد الاسم من البيانات
        validated_data.pop('password2')
        password = validated_data.pop('password')

    # إنشاء المستخدم باستخدام المانجر
        user = CustomUser.objects.create_user(password=password, **validated_data)
        user.is_active = True  # الحساب مش بيتفعل إلا بعد OTP/تأكيد
        user.save()
   
   
        UserProfile.objects.create(user=user, full_name=name)

        return user

# Login

class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def validate(self, attrs):
        phone = attrs.get('phone')
        password = attrs.get('password')

        if phone and password:
            try:
                user = CustomUser.objects.get(phone=phone)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({"detail": _("رقم الهاتف أو كلمة المرور غير صحيحة.")})

            if not user.check_password(password):
                raise serializers.ValidationError({"detail": _("رقم الهاتف أو كلمة المرور غير صحيحة.")})

            if not user.is_active:
                raise serializers.ValidationError({"detail": _("الحساب غير مفعل. يرجى التحقق من OTP.")})

            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError({"detail": _("يجب تقديم رقم الهاتف وكلمة المرور.")})


# Reset Password Serializer 
class ResetPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=4, min_length=4)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        phone_number = data.get('phone_number')
        otp = data.get('otp')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not phone_number or not otp or not new_password or not confirm_password:
            raise serializers.ValidationError({"detail" : _("All fields are required.")})

        if len(otp) != 4 or not otp.isdigit():
            raise serializers.ValidationError({"detail" : _("Invalid OTP format.")})

        if new_password != confirm_password:
            raise serializers.ValidationError({"detail" : _("Passwords do not match.")})

        return data


# OTP Verification Serializer
class OTPVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=4, min_length=4)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(_("الكود لازم يكون 4 أرقام فقط."))
        if len(value) != 4:
            raise serializers.ValidationError(_("الكود لازم يكون مكون من 4 أرقام بالظبط."))
        return value

    def validate(self, attrs):
        code = attrs.get("code")
        user = self.context.get("user")

        try:
            otp = OTP.objects.filter(user=user, is_used=False).latest("created_at")
        except OTP.DoesNotExist:
            raise serializers.ValidationError(_("لا يوجد كود OTP صالح."))

        # تحقق من صلاحية الكود
        if otp.code != code:
            raise serializers.ValidationError(_("الكود غير صحيح."))

        # تحقق من انتهاء الصلاحية (5 دقايق مثلاً)
        from django.utils import timezone
        import datetime
        if timezone.now() - otp.created_at > datetime.timedelta(minutes=5):
            raise serializers.ValidationError(_("الكود منتهي الصلاحية."))

    
        otp.is_used = True
        otp.save()
        user.is_active = True
        user.save()

        attrs["otp"] = otp
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context['request'].user

        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({"old_password": _("Old password is incorrect.")})

        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": _("New passwords do not match.")})

        if len(data['new_password']) < 6 or len(data['new_password']) > 16:
            raise serializers.ValidationError({"new_password": _("Password must be between 6 and 16 characters.")})

        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


# Notifications Serializers

User = get_user_model()


class NotificationSerializer(serializers.ModelSerializer):
    recipients = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'recipients', 'created_at', 'read']


class NotificationCreateSerializer(serializers.ModelSerializer):
    recipient_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True  # ⬅️ هنا عشان [] تعتبر اختيار "الكل"
    )

    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'recipient_ids', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        recipient_ids = validated_data.pop('recipient_ids', None)
        notification = Notification.objects.create(**validated_data)

        if recipient_ids is None or recipient_ids == []:
            # ⬅️ لو مبعتش IDs أو بعت [] → يختار كل المستخدمين
            users = User.objects.all()
        else:
            users = User.objects.filter(id__in=recipient_ids)

        notification.recipients.set(users)
        return notification