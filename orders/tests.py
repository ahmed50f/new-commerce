from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import Company, Vendor
from products.models import Product, Category
from orders.models import Order, OrderItem, Transaction
from django.utils.text import slugify

User = get_user_model()


class OrderTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="TestCo", subscription_plan="free")
        self.customer = User.objects.create_user(
            phone="01000000000", email="cust@gmail.com", password="pass123"
        )
        self.category = Category.objects.create(name="General", slug="general")
        self.vendor = Vendor.objects.create(user=self.customer, company=self.company, status="approved")
        self.product = Product.objects.create(
            company=self.company,
            vendor=self.vendor,
            name="Test Product",
            slug=slugify("Test Product"), 
            price=50,
            stock=10,
            category=self.category,
        )

    def test_order_update_totals(self):
        order = Order.objects.create(customer=self.customer, company=self.company, shipping_cost=20, governorate="Cairo")
        OrderItem.objects.create(order=order, product=self.product, quantity=2)
        order.update_totals()
        self.assertEqual(order.items_total, 100)
        self.assertEqual(order.shipping_cost, 20)
        self.assertEqual(order.total_amount, 120)

    def test_order_str(self):
        order = Order.objects.create(customer=self.customer, company=self.company)
        self.assertIn(str(self.customer), str(order))

class TransactionTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="PayCo", subscription_plan="free")
        self.customer = User.objects.create_user(
            phone="01111111111", email="pay@gmail.com", password="pass123"
        )

        # نعمل كاتيجوري للمنتج
        self.category = Category.objects.create(name="Electronics", slug="electronics")

        # نعمل Vendor للشركة
        self.vendor = Vendor.objects.create(user=self.customer, company=self.company, status="approved")

        # المنتج لازم يبقى كامل
        self.product = Product.objects.create(
            company=self.company,
            vendor=self.vendor,
            name="Phone",
            slug=slugify("Phone"),
            price=200,
            stock=5,
            category=self.category,
        )

        self.order = Order.objects.create(customer=self.customer, company=self.company, shipping_cost=10)
        OrderItem.objects.create(order=self.order, product=self.product, quantity=1)
        self.order.update_totals()

    def test_transaction_auto_amount(self):
        tx = Transaction.objects.create(
            user=self.customer,
            order=self.order,
            method="visa",
        )
        self.assertEqual(tx.amount, self.order.total_amount)
        self.assertIsNotNone(tx.reference_id)
        self.assertEqual(len(tx.reference_id), 12)

    def test_transaction_str(self):
        tx = Transaction.objects.create(
            user=self.customer,
            order=self.order,
            method="paypal",
        )
        self.assertIn("Order", str(tx))
        self.assertIn(str(self.customer.phone), str(tx))
