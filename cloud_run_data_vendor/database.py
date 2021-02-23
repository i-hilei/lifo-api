from flask_sqlalchemy import SQLAlchemy

postgres_db = SQLAlchemy()

from labels import models as label_models
from lists import models as list_models
from influencers import models as influencer_models
from modash import models as modash_models
from shopify_lifo import models as shopify_models
from campaigns import models as campaign_models
from referrals import models as referral_models
from shop_products import models as shop_product_models


if __name__ == '__main__':
    from main import app
    label_models.postgres_db.create_all(app=app)
    list_models.postgres_db.create_all(app=app)
    influencer_models.postgres_db.create_all(app=app)
    modash_models.postgres_db.create_all(app=app)
    shopify_models.postgres_db.create_all(app=app)
    campaign_models.postgres_db.create_all(app=app)
    referral_models.postgres_db.create_all(app=app)
    shop_product_models.postgres_db.create_all(app=app)
    cursor = postgres_db.get_engine(app=app)

    for name in ['age', 'gender']:
        modash_models.create_modash_audience_triggers(name, cursor)
    modash_models.create_modash_audience_triggers('ethnicity', cursor, 'name')
