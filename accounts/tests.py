from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import Company, Vendor, OTP, Notification
User = get_user_model()

class CustomUserTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            phone="01000000000",
            email="test@gmail.com",
            password="pass123",
            role="vendor"
        )
        self.assertEqual(user.phone, "01000000000")
        self.assertEqual(user.email, "test@gmail.com")
        self.assertTrue(user.check_password("pass123"))
        self.assertEqual(user.role, "vendor")

    def test_create_superuser(self):
        superuser = User.objects.create_superuser(
            phone="01111111111",
            email="admin@gmail.com",
            password="admin123"
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)



class CompanyTest(TestCase):
    def test_plan_price_auto_set(self):
        company = Company.objects.create(name="MyCo", subscription_plan="basic")
        self.assertEqual(company.plan_price, 100)
        self.assertEqual(company.plan_limit, 100)

    def test_free_plan_limit(self):
        company = Company.objects.create(name="Startup", subscription_plan="free")
        self.assertEqual(company.plan_price, 0)
        self.assertEqual(company.plan_limit, 10)


User = get_user_model()

class VendorTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Company A")
        self.user = User.objects.create_user(
            phone="01011111111", email="vendor@gmail.com", password="12345", role="vendor"
        )

    def test_vendor_request(self):
        vendor = Vendor.objects.create(user=self.user, company=self.company)
        self.assertEqual(vendor.status, "pending")
        self.assertEqual(str(vendor), f"{self.user.email} -> {self.company.name} ({vendor.status})")

    def test_unique_vendor_request(self):
        Vendor.objects.create(user=self.user, company=self.company)
        with self.assertRaises(Exception):
            Vendor.objects.create(user=self.user, company=self.company)


class OTPTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="01022222222", email="client@gmail.com", password="12345"
        )

    def test_auto_generate_code(self):
        otp = OTP.objects.create(user=self.user)
        self.assertEqual(len(otp.code), 4)
        self.assertTrue(otp.code.isdigit())

    def test_code_validation(self):
        otp = OTP(user=self.user, code="12ab")
        with self.assertRaises(Exception):  
            otp.full_clean()



User = get_user_model()

class NotificationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="01033333333", email="notify@example.com", password="12345"
        )

    def test_send_user_notification(self):
        notif = Notification.send_user_notification(self.user, "Hello", "Welcome")
        self.assertIn(self.user, notif.recipients.all())
        self.assertEqual(notif.title, "Hello")

    def test_send_global_notification(self):
        Notification.send_global_notification("Global", "Message")
        self.assertEqual(Notification.objects.count(), 1)
        notif = Notification.objects.first()
        self.assertEqual(notif.recipients.count(), User.objects.count())