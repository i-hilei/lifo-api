from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from database import postgres_db


class Campaign(postgres_db.Model):
    id = Column(String(128), primary_key=True)
    campaign_name = Column(String(128))
    brand = Column(String(128))
    platform = Column(String(128))
    time_stamp = Column(DateTime(timezone=True))
    created = Column(DateTime, nullable=False, default=datetime.now())
    account_s = relationship('SocialAccount', secondary="campaign_social_account", backref='campaigns')
    scores = relationship("CampaignScore", back_populates="campaign")


# many to many
class CampaignSocialAccount(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    social_id = Column(Integer, ForeignKey('social_account.id'))
    campaign_id = Column(String(128), ForeignKey('campaign.id'))
    __table_args__ = (UniqueConstraint('social_id', 'campaign_id', name='social_id_campaign_id_unique'), )


class CampaignScore(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    campaign_id = Column(String(128), ForeignKey('campaign.id'))
    campaign = relationship(Campaign, back_populates="scores")
    social_id = Column(Integer, ForeignKey('social_account.id'))
    social_account = relationship("SocialAccount", back_populates="campaign_scores")
    email_resp = Column(Integer, default=0)
    instruction_timelines = Column(Integer, default=0)
    commission_demand = Column(Integer, default=0)
    content_eng = Column(Integer, default=0)
    instruction_quality = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint('social_id', 'campaign_id', name='score_social_id_campaign_id_unique'),)
