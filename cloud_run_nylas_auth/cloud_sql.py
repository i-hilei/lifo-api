import logging

from flask import Response
import sqlalchemy
from sqlalchemy import MetaData, Table, Column, String, select


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
        self.db_name = "auth"
        self.db_user = "gcf"
        self.db_password = "967Shoreline"

        # // If your database is MySQL, uncomment the following two lines:
        # driver_name = 'mysql+pymysql'
        # query_string = '"unix_socket": "/cloudsql/{}".format(connection_name)'
        # #
        # // If your database is PostgreSQL, uncomment the following two lines:
        self.driver_name = 'postgres+pg8000'
        # self.query_string = '"unix_sock": "/cloudsql/{}/.s.PGSQL.5432".format(gcf)'
        self.logger = logging.getLogger()

        meta = MetaData()
        self.nylas_access_token = Table(
                'nylas_access_token', meta,
                Column('uid', String, primary_key=True),
                Column('nylas_access_token', String),
                Column('nylas_account_id', String),
                Column('email', String)
            )

        # [START cloud_sql_postgres_sqlalchemy_create]
        # The SQLAlchemy engine will help manage interactions, including automatically
        # managing a pool of connections to your database
        self.db = sqlalchemy.create_engine(
            # Equivalent URL:
            # postgres+pg8000://<db_user>:<db_pass>@/<db_name>?unix_sock=/cloudsql/<cloud_sql_instance_name>/.s.PGSQL.5432
            sqlalchemy.engine.url.URL(
                drivername='postgres+pg8000',
                username=self.db_user,
                password=self.db_password,
                database=self.db_name,
                query={'unix_sock': '/cloudsql/{}/.s.PGSQL.5432'.format(self.connection_name)}
            ),
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
        # Create tables (if they don't already exist)
        with self.db.connect() as conn:
            conn.execute(
            """
            CREATE TABLE IF NOT EXISTS authentication_test(
                uid text PRIMARY KEY, 
                token text, 
                refresh_token text NOT NULL, 
                token_uri text,
                client_id text, 
                client_secret text, 
                scopes json
            );
            """
            )
            conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nylas_access_token(
                uid text PRIMARY KEY, 
                nylas_access_token text,
                nylas_account_id text,
                email text
            );
            """
            )

    def get_nylas_access_token(self, uid):
        try:
            select_query = select([self.nylas_access_token.c.nylas_access_token]).where(self.nylas_access_token.c.uid == uid)
            conn = self.db.connect()
            result = conn.execute(select_query).fetchall()
            logging.info(f'Getting nylass code sql results: {result}')
            return result[0][0]
        except Exception as e:
            logging.error(f'Error getting access code for uid {uid}, the error is' + str(e))
            return ''

    def get_nylas_authorize_info(self, uid):
        try:
            select_query = select([self.nylas_access_token.c.nylas_access_token, self.nylas_access_token.c.email]).where(self.nylas_access_token.c.uid == uid)
            conn = self.db.connect()
            result = conn.execute(select_query).fetchall()
            logging.info(f'Getting nylas sql results: {result}')
            return result[0][0], result[0][1]
        except Exception as e:
            logging.error(f'Error getting access code for uid {uid}, the error is' + str(e))
            return '', ''

    def save_nylas_token(self, uid, nylas_access_token, nylas_account_id, email):

        # Verify that the team is one of the allowed options
        if not uid and not nylas_access_token:
            return Response(
                response="Invalid refresh token or token specified.",
                status=400
            )

        # # [START cloud_sql_postgres_sqlalchemy_connection]
        # # Preparing a statement before hand can help protect against injections.
        # stmt = sqlalchemy.text('insert into nylas_access_token (uid, nylas_access_token) values (:uid, :nylas_access_token)')
        # stmt = stmt.bindparams(uid=uid, nylas_access_token=nylas_access_token)
        try:
            # # Using a with statement ensures that the connection is always released
            # # back into the pool at the end of statement (even if an error occurs)
            with self.db.connect() as conn:
                from sqlalchemy.dialects.postgresql import insert

                insert_stmt = insert(self.nylas_access_token).values(
                    uid=uid,
                    nylas_access_token=nylas_access_token,
                    nylas_account_id=nylas_account_id,
                    email=email
                )
                do_update_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=['uid'],
                    set_=dict(nylas_access_token=nylas_access_token,
                              nylas_account_id=nylas_account_id,
                              email=email)
                )
                conn.execute(do_update_stmt)
        except Exception as e:
            # If something goes wrong, handle the error in this section. This might
            # involve retrying or adjusting parameters depending on the situation.
            # [START_EXCLUDE]
            self.logger.exception(e)
            return Response(
                status=500,
                response=f"Unable to update authentication: {e}"
            )
        return Response(
            status=200,
            response="Successfully updated authentication table"
        )

    def save_token(self, token_json):
        # Get the team and time the vote was cast.
        token = token_json['token']
        refresh_token = token_json['refresh_token']
        token_uri = token_json['token_uri']
        client_id = token_json['client_id']
            # 'token': credentials.token,
            # 'refresh_token': credentials.refresh_token,
            # 'token_uri': credentials.token_uri,
            # 'client_id': credentials.client_id,
            # 'client_secret': credentials.client_secret,
            # 'scopes': credentials.scopes}
        # Verify that the team is one of the allowed options
        if not refresh_token and not token:
            self.logger.warning(token_json)
            return Response(
                response="Invalid refresh token or token specified.",
                status=400
            )

        # [START cloud_sql_postgres_sqlalchemy_connection]
        # Preparing a statement before hand can help protect against injections.
        stmt = sqlalchemy.text('insert into authentication (refresh_token, token) values (:refresh_token, :token)')
        stmt = stmt.bindparams(refresh_token=refresh_token, token=token)
        try:
            # Using a with statement ensures that the connection is always released
            # back into the pool at the end of statement (even if an error occurs)
            with self.db.connect() as conn:
                conn.execute(stmt)
        except Exception as e:
            # If something goes wrong, handle the error in this section. This might
            # involve retrying or adjusting parameters depending on the situation.
            # [START_EXCLUDE]
            self.logger.exception(e)
            return Response(
                status=500,
                response=f"Unable to update authentication: {e}"
            )
            # [END_EXCLUDE]
        # [END cloud_sql_postgres_sqlalchemy_connection]

        return Response(
            status=200,
            response="Successfully updated authentication table"
        )
sql_handler = Sqlhandler()
