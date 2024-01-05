# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestProductModel

"""
import os
import logging
import unittest
from decimal import Decimal
from service.models import Product, Category, db, DataValidationError
from service import app
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertTrue(product is not None)
        self.assertEqual(product.id, None)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])
        product = ProductFactory()
        product.id = None
        product.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        # Check that it matches the original product
        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    def test_read_product(self):
        """ It should read product by id"""
        product = ProductFactory()
        product.id = None
        product.create()

        self.assertIsNotNone(product.id)
        found_product = Product.find(product.id)
        self.assertEqual(found_product.id, product.id)
        self.assertEqual(found_product.name, product.name)
        self.assertEqual(found_product.description, product.description)
        self.assertEqual(found_product.price, product.price)
        self.assertEqual(found_product.available, product.available)
        self.assertEqual(found_product.category, product.category)

    def test_update_product(self):
        """ It should update product by id"""
        product = ProductFactory()
        product.id = None
        product.create()

        self.assertIsNotNone(product.id)

        new_desc = "Some desc"
        product_id = product.id
        product.description = new_desc

        product.update()
        self.assertEqual(product.id, product_id)
        self.assertEqual(product.description, new_desc)

        updated_product = Product.all()
        self.assertEqual(len(updated_product), 1)
        self.assertEqual(updated_product[0].id, product.id)
        self.assertEqual(updated_product[0].description, product.description)

    def test_update_product_with_no_id(self):
        """ It should raise DataValidationError when update product without id"""
        product = ProductFactory()
        product.id = None
        product.create()

        self.assertIsNotNone(product.id)

        product.id = None
        self.assertRaises(DataValidationError, product.update)

    def test_delete_product(self):
        """ It should delete product by id"""
        product = ProductFactory()
        product.id = None
        product.create()

        self.assertIsNotNone(product.id)

        products = Product.all()
        self.assertEqual(len(products), 1)
        product.delete()

        products = Product.all()
        self.assertEqual(len(products), 0)

    def test_deserialize_product(self):
        """ It should create product by deserialization"""
        test_product = ProductFactory().serialize()
        product = Product()
        product.deserialize(test_product)
        product.create()

        self.assertIsNotNone(product.id)

        products = Product.all()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].id, product.id)
        self.assertEqual(products[0].name, product.name)
        self.assertEqual(products[0].description, product.description)
        self.assertEqual(products[0].price, product.price)
        self.assertEqual(products[0].available, product.available)
        self.assertEqual(products[0].category, product.category)

    def test_deserialize_product_invalid_avalability(self):
        """ It should throw DataValidationError when deserialize product with invalid avalability """
        test_product = ProductFactory().serialize()
        test_product["available"] = []
        product = Product()

        self.assertRaises(DataValidationError, product.deserialize, test_product)

    def test_deserialize_product_invalid_category(self):
        """ It should throw DataValidationError when deserialize product with invalid category """
        test_product = ProductFactory().serialize()
        test_product["category"] = "SPORTS"
        product = Product()

        self.assertRaises(DataValidationError, product.deserialize, test_product)

    def test_deserialize_product_invalid_type(self):
        """ It should throw DataValidationError when deserialize product with invalid type """
        test_product = ProductFactory().serialize()
        test_product["price"] = {}
        product = Product()

        self.assertRaises(DataValidationError, product.deserialize, test_product)

    def test_list_products(self):
        """ It should list all products """
        products = Product.all()

        self.assertEqual(len(products), 0)
        for _ in range(5):
            product = ProductFactory()
            product.id = None
            product.create()

        products = Product.all()
        self.assertEqual(len(products), 5)

    def test_list_products_by_name(self):
        """ It should list all products filter by name """
        products = Product.all()

        self.assertEqual(len(products), 0)
        for _ in range(5):
            product = ProductFactory()
            product.id = None
            product.create()

        products = Product.all()
        self.assertEqual(len(products), 5)

        first_product_name = products[0].name
        count = 0
        for product in products:
            if product.name == first_product_name:
                count = count + 1

        products = Product.find_by_name(first_product_name)
        self.assertEqual(products.count(), count)

    def test_list_products_by_availability(self):
        """ It should list all products filter by availability """
        products = Product.all()

        self.assertEqual(len(products), 0)
        for _ in range(5):
            product = ProductFactory()
            product.id = None
            product.create()

        products = Product.all()
        self.assertEqual(len(products), 5)

        first_product_availability = products[0].available
        count = 0
        for product in products:
            if product.available == first_product_availability:
                count = count + 1

        products = Product.find_by_availability(first_product_availability)
        self.assertEqual(products.count(), count)

    def test_list_products_by_category(self):
        """ It should list all products filter by category """
        products = Product.all()

        self.assertEqual(len(products), 0)
        for _ in range(5):
            product = ProductFactory()
            product.id = None
            product.create()

        products = Product.all()
        self.assertEqual(len(products), 5)

        first_product_category = products[0].category
        count = 0
        for product in products:
            if product.category == first_product_category:
                count = count + 1

        products = Product.find_by_category(first_product_category)
        self.assertEqual(products.count(), count)

    def test_list_products_by_price(self):
        """ It should list all products filter by price """
        products = Product.all()

        self.assertEqual(len(products), 0)
        for _ in range(5):
            product = ProductFactory()
            product.id = None
            product.create()

        products = Product.all()
        self.assertEqual(len(products), 5)

        first_product_price = products[0].price
        count = 0
        for product in products:
            if product.price == first_product_price:
                count = count + 1

        products = Product.find_by_price(first_product_price)
        self.assertEqual(products.count(), count)

    def test_list_products_by_string_price(self):
        """ It should list all products filter by string price """
        products = Product.all()

        self.assertEqual(len(products), 0)
        for _ in range(5):
            product = ProductFactory()
            product.id = None
            product.create()

        products = Product.all()
        self.assertEqual(len(products), 5)

        first_product_price = products[0].price
        count = 0
        for product in products:
            if product.price == first_product_price:
                count = count + 1

        products = Product.find_by_price(str(first_product_price))
        self.assertEqual(products.count(), count)
