######################################################################
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
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from urllib.parse import quote_plus
from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_get_product(self):
        """It should get a Product"""
        test_product = self._create_products()[0]
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check the data is correct
        found_product = response.get_json()
        self.assertEqual(found_product["name"], test_product.name)
        self.assertEqual(found_product["description"], test_product.description)
        self.assertEqual(Decimal(found_product["price"]), test_product.price)
        self.assertEqual(found_product["available"], test_product.available)
        self.assertEqual(found_product["category"], test_product.category.name)

    def test_get_product_not_found(self):
        """ Get product with not found id should return 404 """
        test_product = self._create_products()[0]
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product(self):
        """ It should update the product correctly """
        test_product = self._create_products()[0]
        logging.debug("Test Product: %s", test_product.serialize())

        new_desc = "Some desc"
        test_product.description = new_desc
        response = self.client.put(f"{BASE_URL}/{test_product.id}", json=test_product.serialize())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()['description'], new_desc)

    def test_update_product_not_found(self):
        """ Update product with not found id should response with 404 """
        test_product = self._create_products()[0]
        logging.debug("Test Product: %s", test_product.serialize())

        new_desc = "Some desc"
        test_product.description = new_desc
        response = self.client.put(f"{BASE_URL}/0", json=test_product.serialize())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("message", response.get_json())

    def test_update_product_invalid_payload(self):
        """ Update product with invalid payload should response with 400 """
        test_product = self._create_products()[0]
        logging.debug("Test Product: %s", test_product.serialize())
        new_desc = "Some desc"
        test_product.description = new_desc
        test_product = test_product.serialize()
        test_product['price'] = {}

        response = self.client.put(f"{BASE_URL}/{test_product['id']}", json=test_product)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("message", response.get_json())

    def test_delete_product(self):
        """ It should delete product correctly """
        test_product = self._create_products()[0]
        logging.debug("Test Product: %s", test_product.serialize())

        response = self.client.delete(f"{BASE_URL}/{test_product.id}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(f"{BASE_URL}/{test_product.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_product_not_found(self):
        """ It should delete product correctly """
        test_product = self._create_products()[0]
        logging.debug("Test Product: %s", test_product.serialize())

        response = self.client.delete(f"{BASE_URL}/0")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_products(self):
        """ It should list all Products """
        test_products = self._create_products(10)
        test_products_list = list(
            map(
                self.mapper,
                test_products
            )
        )

        response = self.client.get(BASE_URL)
        products = response.get_json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(products), 10)
        self.assertCountEqual(products, test_products_list)

    def test_list_products_by_name(self):
        """It should list all Products which contain the give name"""
        test_products = self._create_products(10)
        first_product_name = test_products[0].name

        test_products_match_name = []
        for product in test_products:
            if product.name == first_product_name:
                test_products_match_name.append(product)
        count = len(test_products_match_name)

        response = self.client.get(
            BASE_URL,
            query_string={
                "name": quote_plus(first_product_name)
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_products_match_name = list(
            map(
                self.mapper, test_products_match_name
            )
        )

        # Check the data is correct
        found_products = response.get_json()

        self.assertEqual(len(found_products), count)
        self.assertCountEqual(found_products, test_products_match_name)

    def test_list_products_by_category(self):
        """It should list all Products which contain the give category"""
        test_products = self._create_products(10)
        first_product_category = test_products[0].category.value

        test_products_match_category = []
        for product in test_products:
            if product.category.value == first_product_category:
                test_products_match_category.append(product)
        count = len(test_products_match_category)

        response = self.client.get(
            BASE_URL,
            query_string={
                "category": quote_plus(str(first_product_category))
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_products_match_category = list(
            map(
                self.mapper, test_products_match_category
            )
        )

        # Check the data is correct
        found_products = response.get_json()

        self.assertEqual(len(found_products), count)
        self.assertCountEqual(found_products, test_products_match_category)

    def test_list_products_by_category_string(self):
        """It should list all Products which contain the give category"""
        test_products = self._create_products(10)
        first_product_category = test_products[0].category.name

        test_products_match_category = []
        for product in test_products:
            if product.category.name == first_product_category:
                test_products_match_category.append(product)
        count = len(test_products_match_category)

        response = self.client.get(
            BASE_URL,
            query_string={
                "category": quote_plus(str(first_product_category))
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_products_match_category = list(
            map(
                self.mapper, test_products_match_category
            )
        )

        # Check the data is correct
        found_products = response.get_json()

        self.assertEqual(len(found_products), count)
        self.assertCountEqual(found_products, test_products_match_category)

    def test_list_products_by_availability(self):
        """It should list all Products which contain the give availability"""
        test_products = self._create_products(10)
        first_product_availability = test_products[0].available

        test_products_match_availability = []
        for product in test_products:
            if product.available == first_product_availability:
                test_products_match_availability.append(product)
        count = len(test_products_match_availability)

        response = self.client.get(
            BASE_URL,
            query_string={
                "available": quote_plus(str(first_product_availability))
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test_products_match_availability = list(
            map(
                self.mapper, test_products_match_availability
            )
        )

        # Check the data is correct
        found_products = response.get_json()

        self.assertEqual(len(found_products), count)
        self.assertCountEqual(found_products, test_products_match_availability)

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)

    def mapper(self, product):
        """ Mapping list of Product in to list of dict """
        return product.serialize()
