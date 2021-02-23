from sqlalchemy import Column, String, Integer, ForeignKey, JSON, TIMESTAMP, Boolean, UniqueConstraint, Float
from datetime import datetime

from database import postgres_db


class ModashProfile(postgres_db.Model):
    __tablename__ = 'modash_profile'
    account_id = Column(String, primary_key=True)
    platform = Column(String, primary_key=True)
    profile_json = Column(JSON)
    timestamp = Column(TIMESTAMP, default=datetime.now())
    is_registered = Column(Boolean)
    complete_campaign = Column(Boolean)
    in_campaign = Column(Boolean)
    in_list = Column(Boolean)


class ModashProfileV1(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    account_id = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP, default=datetime.now())
    is_registered = Column(Boolean)
    complete_campaign = Column(Boolean)
    in_campaign = Column(Boolean)
    in_list = Column(Boolean)
    country = Column(String, index=True)
    city = Column(String, index=True)
    language = Column(String, index=True)
    gender = Column(String, index=True)
    followers = Column(Integer)
    fake_followers = Column(Integer)
    engagements = Column(Integer)
    avg_likes = Column(Integer)
    avg_comments = Column(Integer)
    age_group = Column(String)
    audience_ethnicity = Column(String(64))
    audience_age = Column(String(64))
    audience_gender = Column(String(64))
    __table_args__ = (UniqueConstraint('account_id', 'platform', name='account_platform_unique'),)


class ModashProfileHashtag(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('modash_profile_v1.id'), nullable=False)
    tag = Column(String(64), nullable=False, index=True)
    weight = Column(Float)
    __table_args__ = (UniqueConstraint('profile_id', 'tag', name='hashtag_profile_id_tag_unique'),)


class ModashAudienceCity(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('modash_profile_v1.id'), nullable=False)
    name = Column(String(64), nullable=False, index=True)
    weight = Column(Float, nullable=False)
    __table_args__ = (UniqueConstraint('profile_id', 'name', name='city_profile_id_name_unique'),)


class ModashAudienceLanguage(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('modash_profile_v1.id'), nullable=False)
    name = Column(String(128), nullable=False, index=True)
    code = Column(String(16))
    weight = Column(Float)
    __table_args__ = (UniqueConstraint('profile_id', 'name', name='language_profile_id_code_unique'),)


class ModashAudienceEthnicity(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('modash_profile_v1.id'), nullable=False)
    name = Column(String(128), nullable=False, index=True)
    code = Column(String(64))
    weight = Column(Float)
    __table_args__ = (UniqueConstraint('profile_id', 'name', name='ethnicity_profile_id_code_unique'),)


class ModashAudienceAge(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('modash_profile_v1.id'), nullable=False)
    code = Column(String(16), nullable=False, index=True)
    weight = Column(Float)
    __table_args__ = (UniqueConstraint('profile_id', 'code', name='age_profile_id_code_unique'),)


class ModashAudienceGender(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('modash_profile_v1.id'), nullable=False)
    code = Column(String(16), nullable=False)
    weight = Column(Float)
    __table_args__ = (UniqueConstraint('profile_id', 'code', name='gender_profile_id_code_unique'),)


class ModashAudienceInterest(postgres_db.Model):
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('modash_profile_v1.id'), nullable=False)
    name = Column(String(128), nullable=False, index=True)
    weight = Column(Float)
    __table_args__ = (UniqueConstraint('profile_id', 'name', name='interest_profile_id_name_unique'),)


def create_modash_audience_triggers(name: str, cursor, init_field='code'):
    func_query = f"""
        CREATE OR REPLACE FUNCTION public.modash_audience_{name}()
        RETURNS trigger
        LANGUAGE 'plpgsql'
         NOT LEAKPROOF
        AS $BODY$
        BEGIN
            UPDATE modash_profile_v1 SET
            audience_{name} = (
                                SELECT {init_field} FROM public.modash_audience_{name}
            WHERE (
                    weight = (
                        SELECT max(weight) FROM public.modash_audience_{name} WHERE profile_id = new.profile_id
                    )) AND (profile_id = new.profile_id) 
            LIMIT 1
            )
            WHERE id = new.profile_id;
            RETURN NEW;
        END;
        $BODY$;
    """

    trigger_create = f"""
        DROP TRIGGER IF EXISTS create_audience_{name} ON public.modash_audience_{name};

        CREATE TRIGGER create_audience_{name}
        AFTER INSERT
        ON public.modash_audience_{name}
        FOR EACH ROW
        WHEN (new.weight IS NOT NULL)
        EXECUTE PROCEDURE public.modash_audience_{name}();
    """

    trigger_update = f"""
        DROP TRIGGER IF EXISTS update_audience_{name} ON public.modash_audience_{name};

        CREATE TRIGGER update_audience_{name}
        AFTER UPDATE OF weight
        ON public.modash_audience_{name}
        FOR EACH ROW
        WHEN (new.weight IS DISTINCT FROM old.weight)
        EXECUTE PROCEDURE public.modash_audience_{name}();
    """

    trigger_delete = f"""
        DROP TRIGGER IF EXISTS delete_audience_{name} ON public.modash_audience_{name};

        CREATE TRIGGER delete_audience_{name}
        AFTER DELETE
        ON public.modash_audience_{name}
        FOR EACH ROW
        EXECUTE PROCEDURE public.modash_audience_{name}();
    """
    cursor.execute(func_query)
    cursor.execute(trigger_create)
    cursor.execute(trigger_update)
    cursor.execute(trigger_delete)
