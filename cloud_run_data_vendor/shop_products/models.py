from sqlalchemy import (Column, String, Integer, Float, BigInteger, Boolean, DateTime)
from sqlalchemy.orm import relationship
from datetime import datetime

from database import postgres_db


class ShopProduct(postgres_db.Model):
    shop = Column(String(255), primary_key=True)
    product_id = Column(BigInteger, primary_key=True)
    image = Column(String)
    product_name = Column(String)
    vendor = Column(String)
    commission = Column(Float)
    compare_at_price = Column(Float)
    discount = Column(Integer)
    price = Column(Float)
    cost = Column(Float)
    active = Column(Boolean, default=False)
    created = Column(DateTime, nullable=False, default=datetime.now())
    label_s = relationship('Label', secondary="label_shop_product", backref='shop_products')
