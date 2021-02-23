from sqlalchemy import Column, String, JSON, TIMESTAMP
from datetime import datetime

from database import postgres_db


class ShopifyAuth(postgres_db.Model):
    __tablename__ = 'shopify_auth'
    shop = Column(String, primary_key=True)
    access_token = Column(String)
    timestamp = Column(TIMESTAMP, default=datetime.now())


class ShopifyInfo(postgres_db.Model):
    __tablename__ = 'shopify_info'
    shop = Column(String, primary_key=True)
    shop_json = Column(JSON)
    timestamp = Column(TIMESTAMP, default=datetime.now())


class ShopifyCustomer(postgres_db.Model):
    __tablename__ = 'shopify_customers'
    shop = Column(String, primary_key=True)
    customer_id = Column(String, primary_key=True)
    customer_json = Column(JSON)
    city = Column(String)
    province = Column(String)
    country_code = Column(String)
    timestamp = Column(TIMESTAMP, default=datetime.now())


class ShopifyProduct(postgres_db.Model):
    __tablename__ = 'shopify_products'
    shop = Column(String, primary_key=True)
    product_id = Column(String, primary_key=True)
    product_json = Column(JSON)
    image = Column(JSON)
    title = Column(String)
    vendor = Column(String)
    tags = Column(String)
    timestamp = Column(TIMESTAMP, default=datetime.now())
