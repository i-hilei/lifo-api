from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4

from database import postgres_db


class User(postgres_db.Model):
    id = Column(String(128), primary_key=True, default=str(uuid4()), unique=True, nullable=False)
    email = Column(String(128), nullable=False, unique=True)
    signup_date = Column(DateTime, nullable=False, default=datetime.now())
    influencer = relationship("Influencer", uselist=False, back_populates="user")
    created = Column(DateTime, nullable=False, default=datetime.now())


class Influencer(postgres_db.Model):
    id = Column(String(128), ForeignKey('user.id'), nullable=False, primary_key=True)
    user = relationship("User", back_populates="influencer")
    name = Column(String(128))
    last_name = Column(String(128))
    instagram_id = Column(String(128))
    phone_number = Column(String(32))
    address1 = Column(String(256))
    address2 = Column(String(256))
    city = Column(String(128))
    province = Column(String(128))
    country = Column(String(128))
    zip = Column(String(128))
    followers_count = Column(Integer)
    accounts = relationship("SocialAccount", back_populates="influencer")
    referrals = relationship("Referral", back_populates="referral_profile")
    created = Column(DateTime, nullable=False, default=datetime.now())


class SocialAccount(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    account_id = Column(String(128), nullable=False)
    platform = Column(String(128), nullable=False)
    influencer_id = Column(String(128), ForeignKey('influencer.id'))
    influencer = relationship("Influencer", back_populates="accounts")
    campaign_s = relationship('Campaign', secondary="campaign_social_account", backref='accounts')
    list_s = relationship('List', secondary="list_social_account", backref='accounts')
    label_s = relationship('Label', secondary="label_social_account", backref='accounts')
    campaign_scores = relationship('CampaignScore', back_populates="social_account")
    __table_args__ = (UniqueConstraint('account_id', 'platform', name='social_account_3432_unique'),)


class Unsubscribed(postgres_db.Model):
    email = Column(String(256), primary_key=True)
    created = Column(DateTime, nullable=False, default=datetime.now())