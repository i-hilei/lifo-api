from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4

from database import postgres_db


class Referral(postgres_db.Model):
    id = Column(String(128), primary_key=True, default=uuid4, unique=True, nullable=False)
    referral_profile_id = Column(String(128), ForeignKey('influencer.id'))
    referral_profile = relationship("Influencer", back_populates="referrals")

    extra_tickets = Column(Integer)
    instagram_id = Column(String(128))
    invitation_source = Column(String(256))
    invited_by = Column(String(128))
    invited_to_lottery = Column(String(128))
    signed_up_at = Column(DateTime())
    invited_at = Column(DateTime())
    campaign_completed_at = Column(DateTime())
    status = Column(String(32))
    tickets = Column(Integer)
    created = Column(DateTime, nullable=False, default=datetime.now())
