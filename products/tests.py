from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from accounts.models import Company, Vendor
from products.models import Category, Product, Review

User = get_user_model()


class CategoryTest(TestCase):
    def test_create_category(self):
        cat = Category.objects.create(name="Electronics", slug="electronics")
        self.assertEqual(str(cat), "Electronics")


class ProductTest(TestCase):
    def setUp(self):
        # شركة + يوزر + Vendor
        self.company = Company.objects.create(name="TechCo", subscription_plan="free")
        self.user = User.objects.create_user(
            phone="01234567890", email="vendor@test.com", password="pass123"
        )
        self.vendor = Vendor.objects.create(user=self.user, company=self.company, status="approved")
        self.category = Category.objects.create(name="Mobiles", slug="mobiles")

    def test_create_product_success(self):
        product = Product.objects.create(
            company=self.company,
            vendor=self.vendor,
            name="iPhone 15",
            slug="iphone-15",
            price=1000,
            stock=10,
            category=self.category,
        )
        self.assertEqual(str(product), "iPhone 15")
        self.assertEqual(product.company, self.company)
        self.assertEqual(product.vendor, self.vendor)

    def test_monthly_limit_restriction(self):
        # free plan → الحد = 10 منتجات
        limit = self.company.plan_limit

        for i in range(limit):
            Product.objects.create(
                company=self.company,
                vendor=self.vendor,
                name=f"Product {i}",
                slug=f"product-{i}",
                price=1000,
                stock=10,
                category=self.category,
            )

        # المنتج التالي لازم يرمي ValidationError
        product_overflow = Product(
            company=self.company,
            vendor=self.vendor,
            name="Overflow Product",
            slug="overflow-product",
            price=900,
            stock=5,
            category=self.category,
        )
        with self.assertRaises(ValidationError):
            product_overflow.full_clean()
            product_overflow.save()

    def test_discounted_price(self):
        product = Product.objects.create(
            company=self.company,
            vendor=self.vendor,
            name="Headphones",
            slug="headphones",
            price=200,
            stock=15,
            category=self.category,
        )
        discounted = product.discounted_price(total_price=200, discount_percentage=10)
        self.assertEqual(discounted, 180)  # 10% خصم


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
