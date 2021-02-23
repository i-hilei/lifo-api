import logging
import datetime
from json import loads
from configparser import ConfigParser
from sys import argv
from google.cloud import secretmanager

from flask import Response
import sqlalchemy
from sqlalchemy import MetaData, Table, Column, String, select, JSON, Numeric, Date, text, DateTime
from modash.populate_modash_profile_v1 import populate_modash_from_raw_data

config = ConfigParser()
secrets = secretmanager.SecretManagerServiceClient()

try:
    config.read(f'config/{argv[1]}.conf')
except IndexError:
    print("Command should be of type: python <start file> <config name>. Example: python main.py local")
    exit()
db_creds = config['DB_CREDS']
POSTGRES_USER_CREDS_SECRET = db_creds['USER_CREDS_SECRET']
postgres_user_creds = secrets.access_secret_version(POSTGRES_USER_CREDS_SECRET).payload.data.decode("utf-8")
postgres_user_creds = loads(postgres_user_creds)


# // Depending on which database you are using, you'll set some variables differently.
# // In this code we are inserting only one field with one value.
# // Feel free to change the insert statement as needed for your own table's requirements.
#
# // Uncomment and set the following variables depending on your specific instance and database:
class Sqlhandler:
    def __init__(self):
        self.connection_name = "influencer-272204:us-central1:influencersql" #"gcf"
        self.table_name = "authentication"
        self.table_field = ""
        self.table_field_value = ""
        self.db_name = db_creds['DB_NAME']
        self.db_user = postgres_user_creds['USER']
        self.db_password = postgres_user_creds['PASSWORD']
        if argv[1] == 'local':
            self.engine = sqlalchemy.engine.url.URL(
                drivername='postgres+pg8000',
                username=self.db_user,
                password=self.db_password,
                database=self.db_name,
                host='localhost')
        else:
            self.engine = sqlalchemy.engine.url.URL(
                drivername='postgres+pg8000',
                username=self.db_user,
                password=self.db_password,
                database=self.db_name,
                query={'unix_sock': '/cloudsql/{}/.s.PGSQL.5432'.format(self.connection_name)})
        # // If your database is MySQL, uncomment the following two lines:
        # driver_name = 'mysql+pymysql'
        # query_string = '"unix_socket": "/cloudsql/{}".format(connection_name)'
        # #
        # // If your database is PostgreSQL, uncomment the following two lines:
        self.driver_name = 'postgres+pg8000'
        # self.query_string = '"unix_sock": "/cloudsql/{}/.s.PGSQL.5432".format(gcf)'
        self.logger = logging.getLogger()

        # [START cloud_sql_postgres_sqlalchemy_create]
        # The SQLAlchemy engine will help manage interactions, including automatically
        # managing a pool of connections to your database
        self.db = sqlalchemy.create_engine(
            # Equivalent URL:
            # postgres+pg8000://<db_user>:<db_pass>@/<db_name>?unix_sock=/cloudsql/<cloud_sql_instance_name>/.s.PGSQL.5432
            self.engine,
            # ... Specify additional properties here.
            # [START_EXCLUDE]

            # [START cloud_sql_postgres_sqlalchemy_limit]
            # Pool size is the maximum number of permanent connections to keep.
            pool_size=5,
            # Temporarily exceeds the set pool_size if no connections are available.
            max_overflow=2,
            # The total number of concurrent connections for your application will be
            # a total of pool_size and max_overflow.
            # [END cloud_sql_postgres_sqlalchemy_limit]

            # [START cloud_sql_postgres_sqlalchemy_backoff]
            # SQLAlchemy automatically uses delays between failed connection attempts,
            # but provides no arguments for configuration.
            # [END cloud_sql_postgres_sqlalchemy_backoff]

            # [START cloud_sql_postgres_sqlalchemy_timeout]
            # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
            # new connection from the pool. After the specified amount of time, an
            # exception will be thrown.
            pool_timeout=30,  # 30 seconds
            # [END cloud_sql_postgres_sqlalchemy_timeout]

            # [START cloud_sql_postgres_sqlalchemy_lifetime]
            # 'pool_recycle' is the maximum number of seconds a connection can persist.
            # Connections that live longer than the specified amount of time will be
            # reestablished
            pool_recycle=1800,  # 30 minutes
            # [END cloud_sql_postgres_sqlalchemy_lifetime]

            # [END_EXCLUDE]
        )
        # [END cloud_sql_postgres_sqlalchemy_create]
        self.create_tables()

    def create_tables(self):
        self.MODASH_PROFILE = Table(
                'modash_profile', MetaData(),
                Column('account_id', String, primary_key=True),
                Column('platform', String, primary_key=True),
                Column('profile_json', JSON),
                Column('timestamp', DateTime),
            )

        self.SHOPIFY_AUTH = Table(
            'shopify_auth', MetaData(),
            Column('shop', String, primary_key=True),
            Column('access_token', String),
            Column('timestamp', DateTime)
        )

        self.SHOPIFY_INFO = Table(
            'shopify_info', MetaData(),
            Column('shop', String, primary_key=True),
            Column('shop_json', JSON),
            Column('timestamp', DateTime)
        )

        self.SHOPIFY_CUSTOMERS = Table(
            'shopify_customers', MetaData(),
            Column('shop', String, primary_key=True),
            Column('customer_id', String, primary_key=True),
            Column('customer_json', JSON),
            Column('city', String),
            Column('province', String),
            Column('country_code', String),
            Column('timestamp', DateTime)
        )

        self.SHOPIFY_PRODUCTS = Table(
            'shopify_products', MetaData(),
            Column('shop', String, primary_key=True),
            Column('product_id', String, primary_key=True),
            Column('product_json', JSON),
            Column('image', JSON),
            Column('title', String),
            Column('vendor', String),
            Column('tags', String),
            Column('timestamp', DateTime)
        )

        # Create tables (if they don't already exist)
        with self.db.connect() as conn:
            conn.execute(
            """
            CREATE TABLE IF NOT EXISTS modash_profile(
                account_id text, 
                platform text, 
                profile_json json, 
                timestamp timestamp,
                PRIMARY KEY (account_id, platform)
            );
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shopify_auth(
                    shop text,
                    access_token text,
                    timestamp timestamp,
                    PRIMARY KEY (shop)
                );
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shopify_info(
                    shop text,
                    shop_json json,
                    timestamp timestamp,
                    PRIMARY KEY (shop)
                );
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shopify_customers(
                    shop text,
                    customer_id text,
                    customer_json json,
                    city text,
                    province text,
                    country_code text,
                    timestamp timestamp,
                    PRIMARY KEY (shop, customer_id)
                );
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shopify_products(
                    shop text,
                    product_id text,
                    product_json json,
                    image json,
                    title text,
                    vendor text,
                    tags text,
                    timestamp timestamp,
                    PRIMARY KEY (shop, product_id)
                );
                """
            )

    def save_profile(self, account_id, platform, profile_json):
        try:
            # # Using a with statement ensures that the connection is always released
            # # back into the pool at the end of statement (even if an error occurs)
            with self.db.connect() as conn:
                from sqlalchemy.dialects.postgresql import insert
                insert_stmt = insert(self.MODASH_PROFILE).values(
                    account_id=account_id,
                    platform=platform,
                    profile_json=profile_json,
                    timestamp=datetime.datetime.now()
                )
                do_update_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=['account_id', 'platform'],
                    set_=dict(
                        profile_json=profile_json,
                        timestamp=datetime.datetime.now()
                    )
                )
                conn.execute(do_update_stmt)

            populate_modash_from_raw_data(account_id, platform, profile_json)

        except Exception as e:
            # If something goes wrong, handle the error in this section. This might
            # involve retrying or adjusting parameters depending on the situation.
            # [START_EXCLUDE]
            self.logger.exception(e)
            return False
        return True

    def get_profile(self, account_id, platform='instagram'):
        """
        :param account_id: account id for each platform
        :param platform: currently only support instagram
        :return: pair: success, profile_json. If found, success will be True; if not, will be False.
        """
        try:
            # # Using a with statement ensures that the connection is always released
            # # back into the pool at the end of statement (even if an error occurs)
            with self.db.connect() as conn:
                stmt = text(
                """
                SELECT profile_json, timestamp 
                FROM modash_profile 
                WHERE account_id = :account_id and platform = :platform
                """)
                stmt = stmt.bindparams(account_id=account_id, platform=platform)
                result = conn.execute(stmt, {"account_id": account_id, "platform": platform}).fetchall()
                if len(result) == 0:
                    logging.info(f'No profile cache found for account {account_id} on {platform}')
                    return {}, None
                # logging.info(f'the cached profile result is {result[0]}')
                return result[0][0], result[0][1]
        except Exception as e:
            self.logger.exception(e)
            return {}, None

    def save_shop_auth(self, shop, access_token):
        try:
            # # Using a with statement ensures that the connection is always released
            # # back into the pool at the end of statement (even if an error occurs)
            with self.db.connect() as conn:
                from sqlalchemy.dialects.postgresql import insert
                insert_stmt = insert(self.SHOPIFY_AUTH).values(
                    shop=shop,
                    access_token=access_token,
                    timestamp=datetime.datetime.now(),
                )
                do_update_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=['shop'],
                    set_=dict(
                        access_token=access_token,
                        timestamp=datetime.datetime.now(),
                    )
                )
                conn.execute(do_update_stmt)
        except Exception as e:
            # If something goes wrong, handle the error in this section. This might
            # involve retrying or adjusting parameters depending on the situation.
            # [START_EXCLUDE]
            self.logger.exception(e)
            return {'status': 'Failed'}
        return {'status': 'OK'}

    def get_shop_auth(self, shop):
        try:
            with self.db.connect() as conn:
                stmt = text(
                    """
                    select access_token
                    from shopify_auth
                    where shop=:shop
                    """)
                stmt = stmt.bindparams(shop=shop)
                result = conn.execute(stmt, {"shop": shop}).fetchall()
                logging.info(f'the get shop auth succeeded')
                if not result or len(result) == 0:
                    return ''
                return result[0][0]
        except Exception as e:
            self.logger.exception(e)
            return ''

    def save_shop_info(self, shop, shop_json):
        try:
            # # Using a with statement ensures that the connection is always released
            # # back into the pool at the end of statement (even if an error occurs)
            with self.db.connect() as conn:
                from sqlalchemy.dialects.postgresql import insert
                insert_stmt = insert(self.SHOPIFY_INFO).values(
                    shop=shop,
                    shop_json=shop_json,
                    timestamp=datetime.datetime.now(),
                )
                do_update_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=['shop'],
                    set_=dict(
                        shop_json=shop_json,
                        timestamp=datetime.datetime.now(),
                    )
                )
                conn.execute(do_update_stmt)
        except Exception as e:
            # If something goes wrong, handle the error in this section. This might
            # involve retrying or adjusting parameters depending on the situation.
            # [START_EXCLUDE]
            self.logger.exception(e)
            return {'status': 'Failed'}
        return {'status': 'OK'}

    def get_shop_customers_locations(self, shop):
        try:
            with self.db.connect() as conn:
                stmt = text(
                    """
                    select city, province, COUNT(*) as location_cnt
                    from shopify_customers
                    where shop=:shop
                    GROUP BY city, province
                    """
                )
                stmt = stmt.bindparams(shop=shop)
                result = conn.execute(stmt, {"shop": shop}).fetchall()
                logging.info(f'the get shop auth succeeded')
                return result
        except Exception as e:
            self.logger.exception(e)
            return []

    def save_customer_info(self, shop, customer_id, customer_json):
        try:
            address = customer_json.get('default_address')
            city, province, country_code = address.get('city'), address.get('province'), address.get('country_code')
            # # Using a with statement ensures that the connection is always released
            # # back into the pool at the end of statement (even if an error occurs)
            with self.db.connect() as conn:
                from sqlalchemy.dialects.postgresql import insert
                insert_stmt = insert(self.SHOPIFY_CUSTOMERS).values(
                    shop=shop,
                    customer_id=customer_id,
                    customer_json=customer_json,
                    city=city,
                    province=province,
                    country_code=country_code,
                    timestamp=datetime.datetime.now(),
                )
                do_update_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=['shop', 'customer_id'],
                    set_=dict(
                        customer_json=customer_json,
                        city=city,
                        province=province,
                        country_code=country_code,
                        timestamp=datetime.datetime.now(),
                    )
                )
                conn.execute(do_update_stmt)
        except Exception as e:
            # If something goes wrong, handle the error in this section. This might
            # involve retrying or adjusting parameters depending on the situation.
            # [START_EXCLUDE]
            self.logger.exception(e)
            return {'status': 'Failed'}
        return {'status': 'OK'}

    def get_product_tags_counts(self, shop):
        try:
            with self.db.connect() as conn:
                stmt = text(
                    """
                    select vendor, tags, COUNT(*) as product_count
                    from shopify_products
                    where shop=:shop
                    GROUP BY vendor, tags
                    """
                )
                stmt = stmt.bindparams(shop=shop)
                result = conn.execute(stmt, {"shop": shop}).fetchall()
                logging.info(f'the get shop auth succeeded')
                return result
        except Exception as e:
            self.logger.exception(e)
            return []

    def get_product_images(self, shop):
        try:
            with self.db.connect() as conn:
                stmt = text(
                    """
                    select title, image, product_id
                    from shopify_products
                    where shop=:shop
                    """
                )
                stmt = stmt.bindparams(shop=shop)
                result = conn.execute(stmt, {"shop": shop}).fetchall()
                logging.info(f'the get shop auth succeeded')
                return result
        except Exception as e:
            self.logger.exception(e)
            return []

    def get_product_info(self, shop, product_id):
        try:
            with self.db.connect() as conn:
                stmt = text(
                    """
                    select title, image, product_json
                    from shopify_products
                    where shop=:shop and product_id=:product_id
                    """
                )
                stmt = stmt.bindparams(shop=shop, product_id=product_id)
                result = conn.execute(stmt, {
                    "shop": shop,
                    "product_id": product_id
                }).fetchall()
                logging.info(f'the get shop product info succeeded')
                return result[0]
        except Exception as e:
            self.logger.exception(e)
            return []

    def save_product_info(self, shop, product_id, product_json):
        try:
            title = product_json.get('title')
            tags = product_json.get('tags')
            image = product_json.get('image')
            vendor = product_json.get('vendor')

            # # Using a with statement ensures that the connection is always released
            # # back into the pool at the end of statement (even if an error occurs)
            with self.db.connect() as conn:
                from sqlalchemy.dialects.postgresql import insert
                insert_stmt = insert(self.SHOPIFY_PRODUCTS).values(
                    shop=shop,
                    product_id=product_id,
                    product_json=product_json,
                    title=title,
                    tags=tags,
                    image=image,
                    vendor=vendor,
                    timestamp=datetime.datetime.now(),
                )
                do_update_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=['shop', 'product_id'],
                    set_=dict(
                        product_json=product_json,
                        title=title,
                        tags=tags,
                        image=image,
                        vendor=vendor,
                        timestamp=datetime.datetime.now(),
                    )
                )
                conn.execute(do_update_stmt)
        except Exception as e:
            # If something goes wrong, handle the error in this section. This might
            # involve retrying or adjusting parameters depending on the situation.
            # [START_EXCLUDE]
            self.logger.exception(e)
            return {'status': 'Failed'}
        return {'status': 'OK'}

sql_handler = Sqlhandler()
