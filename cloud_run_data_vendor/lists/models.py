from sqlalchemy import (Column, String, DateTime, Integer, ForeignKey, UniqueConstraint)
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4

from database import postgres_db


class List(postgres_db.Model):
    id = Column(String(128), primary_key=True, default=str(uuid4()))
    name = Column(String(128))
    platform = Column(String(128))
    created = Column(DateTime, nullable=False, default=datetime.now())
    account_s = relationship('SocialAccount', secondary="list_social_account", backref='lists')
    __table_args__ = (UniqueConstraint('name', 'platform', name='name_platform_unique'),)


# many to many
class ListSocialAccount(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    social_id = Column(Integer, ForeignKey('social_account.id'))
    list_id = Column(String(128), ForeignKey('list.id'))
    __table_args__ = (UniqueConstraint('social_id', 'list_id', name='social_id_list_id_unique'),)
