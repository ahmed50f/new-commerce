from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from decimal import Decimal
from unittest.mock import patch
from accounts.models import Company, Vendor
from products.models import Category, Product, Review
from django.utils.text import slugify


User = get_user_model()


class CategoryTest(TestCase):
    def test_create_category(self):
        cat = Category.objects.create(name="Electronics", slug="electronics")
        self.assertEqual(str(cat), "Electronics")



class ProductTest(TestCase):

    def setUp(self):
        # إنشاء مستخدم تجريبي
        self.user = User.objects.create_user(
            phone="1234567890",
            email="vendor@example.com",
            password="password123"
        )

        # إنشاء شركة تجريبية
        self.company = Company.objects.create(name="Test Company")

        # إنشاء Vendor مربوط بالمستخدم والشركة
        self.vendor = Vendor.objects.create(user=self.user, company=self.company)

        # إنشاء منتج تجريبي مع slug
        self.product = Product.objects.create(
            company=self.company,
            vendor=self.vendor,
            name="Test Product",
            slug=slugify("Test Product"),  # مهم جداً
            price=Decimal("200.00"),
            discount=Decimal("10"),
            stock=10
        )

    def test_discounted_price(self):
        discounted = self.product.discounted_price()
        expected = Decimal("180.00")  # 200 - 10%
        self.assertEqual(discounted, expected)

    def test_discounted_price_no_discount(self):
        self.product.discount = Decimal("0")
        self.product.save()
        discounted = self.product.discounted_price()
        expected = Decimal("200.00")  # بدون خصم
        self.assertEqual(discounted, expected)

class ReviewTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="GadgetCo", subscription_plan="basic")
        self.user = User.objects.create_user(
            phone="01111111111", email="cust@test.com", password="pass123"
        )
        self.vendor = Vendor.objects.create(user=self.user, company=self.company, status="approved")
        self.category = Category.objects.create(name="Laptops", slug="laptops")
        self.product = Product.objects.create(
            company=self.company,
            vendor=self.vendor,
            name="Dell XPS",
            slug="dell-xps",
            price=1500,
            stock=7,
            category=self.category,
        )

    def test_create_review(self):
        review = Review.objects.create(user=self.user, product=self.product, rating=4.5, comment="Great laptop!")
        self.assertEqual(str(review), f"{self.user.username} - {self.product.name} - 4.5")
        self.assertEqual(review.rating, 4.5)

    def test_invalid_rating(self):
        review = Review(user=self.user, product=self.product, rating=6)  # invalid
        with self.assertRaises(ValidationError):
            review.full_clean()  # يطبق الـ validators


class ProductPlanLimitTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Mobiles", slug="mobiles")

    def create_vendor_for_plan(self, plan):
        company = Company.objects.create(name=f"{plan.title()}Co", subscription_plan=plan)
        user = User.objects.create_user(
            phone=f"010{plan[:3]}12345", email=f"{plan}@test.com", password="pass123"
        )
        vendor = Vendor.objects.create(user=user, company=company, status="approved")
        return company, vendor

    def test_free_plan_limit(self):
        company, vendor = self.create_vendor_for_plan("free")
        limit = company.plan_limit  # = 10

        for i in range(limit):
            Product.objects.create(
                company=company,
                vendor=vendor,
                name=f"FreeProduct{i}",
                slug=f"free-product-{i}",
                price=100,
                stock=5,
                category=self.category,
            )

        product = Product(
            company=company,
            vendor=vendor,
            name="FreeProductOverflow",
            slug="free-product-overflow",
            price=200,
            stock=3,
            category=self.category,
        )
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_basic_plan_limit(self):
        company, vendor = self.create_vendor_for_plan("basic")
        limit = company.plan_limit  # = 100

        for i in range(limit):
            Product.objects.create(
                company=company,
                vendor=vendor,
                name=f"BasicProduct{i}",
                slug=f"basic-product-{i}",
                price=100,
                stock=5,
                category=self.category,
            )

        product = Product(
            company=company,
            vendor=vendor,
            name="BasicProductOverflow",
            slug="basic-product-overflow",
            price=200,
            stock=3,
            category=self.category,
        )
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_premium_plan_no_limit(self):
        company, vendor = self.create_vendor_for_plan("premium")

        for i in range(200):
            Product.objects.create(
                company=company,
                vendor=vendor,
                name=f"PremiumProduct{i}",
                slug=f"premium-product-{i}",
                price=100,
                stock=5,
                category=self.category,
            )

        self.assertEqual(Product.objects.filter(company=company).count(), 200)
