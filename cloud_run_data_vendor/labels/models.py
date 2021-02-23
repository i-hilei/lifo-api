from sqlalchemy import (Column, String, Integer, ForeignKey, UniqueConstraint, Float, BigInteger, ForeignKeyConstraint)
from sqlalchemy.orm import relationship

from database import postgres_db


class Label(postgres_db.Model):
    id = Column(Integer, nullable=False, primary_key=True)
    name = Column(String(128), nullable=False)
    parent = Column(Integer, ForeignKey('label.id'))
    type = Column(String(128), nullable=False)
    weight = Column(Float)
    infl_ref = Column(Integer, ForeignKey('label.id'))
    account_s = relationship('SocialAccount', secondary="label_social_account", backref='labels')
    campaign_s = relationship('Campaign', secondary="label_campaign", backref='labels')
    list_s = relationship('List', secondary="label_list", backref='labels')
    shop_product_s = relationship('ShopProduct', secondary="label_shop_product", backref='labels')
    __table_args__ = (UniqueConstraint('name', 'type', name='name_type_unique'),)


# many to many
class LabelSocialAccount(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    social_id = Column(Integer, ForeignKey('social_account.id'))
    label_id = Column(Integer, ForeignKey('label.id'))
    __table_args__ = (UniqueConstraint('social_id', 'label_id', name='social_id_label_id_unique'),)


# many to many
class LabelCampaign(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    campaign_id = Column(String(128), ForeignKey('campaign.id'))
    label_id = Column(Integer, ForeignKey('label.id'))
    __table_args__ = (UniqueConstraint('campaign_id', 'label_id', name='label_id_campaign_id_unique'),)


# many to many
class LabelList(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    list_id = Column(String(128), ForeignKey('list.id'))
    label_id = Column(Integer, ForeignKey('label.id'))
    __table_args__ = (UniqueConstraint('list_id', 'label_id', name='label_id_list_id_unique'),)


# many to many
class LabelShopProduct(postgres_db.Model):
    label_id = Column(Integer, ForeignKey('label.id'), primary_key=True)
    shop = Column(String(255), primary_key=True)
    product_id = Column(BigInteger, primary_key=True)
    __table_args__ = (ForeignKeyConstraint(
            ('shop', 'product_id'),
            ('shop_product.shop', 'shop_product.product_id')
        ),
    )
