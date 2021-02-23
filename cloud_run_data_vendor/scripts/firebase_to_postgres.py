from psycopg2 import connect
import os
from firebase_admin import auth, firestore, initialize_app
from datetime import datetime
from pandas import DataFrame, read_sql, concat, merge
from api_client import ApiClient
from json import loads
from configparser import ConfigParser
from sys import argv
from google.cloud.secretmanager import SecretManagerServiceClient

secrets = SecretManagerServiceClient()

config = ConfigParser()

try:
    config.read(f'config/{argv[1]}.conf')
except IndexError:
    print("Command should be of type: python <start file> <config name>. Example: python main.py local")
    exit()
db_creds = config['DB_CREDS']
POSTGRES_USER_CREDS_SECRET = db_creds['USER_CREDS_SECRET']
user_creds = secrets.access_secret_version(POSTGRES_USER_CREDS_SECRET).payload.data.decode("utf-8")
user_creds = loads(user_creds)

connection = connect(dbname=db_creds['DB_NAME'], user=user_creds['USER'], password=user_creds['PASSWORD'],
                     host=db_creds['HOST'], port=db_creds['PORT'])

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/dmytro_berehovets/lifo-api/influencer-272204-d7c0a5d8097f.json'
firebase_app = initialize_app()
firebase_db = firestore.client()
api_client = ApiClient()


def get_influencer_followers():
    print(datetime.now(), "Getting followers")
    infl_df = read_sql("SELECT * FROM influencer "
                       "WHERE (instagram_id IS NOT NULL) AND (instagram_id NOT IN ('lifoinc', 'instagram'))",
                       connection)
    assert not infl_df.empty, "No influencers with instagram_id"
    instagram_ids = infl_df['instagram_id'].values.tolist()
    ids_len = len(instagram_ids)
    for i in range(0, ids_len, 50):
        print(f"Receiving accounts {i}-{i + 50}/{ids_len}...")

        # getting profiles info from modash api
        profiles_batch = api_client.fetch_modash_profile(instagram_ids[i:i + 50])

        fetch_ins_data = {}
        for ins_id in profiles_batch:
            fetch_ins_data[ins_id] = int(profiles_batch[ins_id]['profile']['followers'])

        # write the received information into the database
        df_to_write = infl_df[infl_df['instagram_id'].isin(instagram_ids[i:i + 50])]
        for index, row in df_to_write.iterrows():
            if fetch_ins_data.get(row['instagram_id']):
                df_to_write['followers_count'].loc[index] = fetch_ins_data.get(row['instagram_id'])

        df_to_write = df_to_write.where(df_to_write.notna(), None)
        df_to_write['created'] = df_to_write['created'].apply(lambda x: str(x))
        result = write_to_db(df_to_write.values.tolist(),
                             'influencer',
                             updating=True,
                             id_tag='id',
                             updating_fields={'followers_count'})
        assert result == 0, result
    print(f"\n{datetime.now()}", "OK")


def make_today_tables():
    today_name = datetime.today().strftime('%Y%m%d')
    today = str(datetime.today().date())
    users_query = f"""DROP TABLE IF EXISTS user_{today_name};
                      CREATE TABLE user_{today_name} AS SELECT * FROM public.user
                      WHERE date(public.user.created) = '{today}';"""
    influencers_query = f"""DROP TABLE IF EXISTS influencer_{today_name};
                            CREATE TABLE IF NOT EXISTS influencer_{today_name} AS SELECT * FROM influencer 
                            WHERE date(created) = '{today}';"""
    referrals_query = f"""DROP TABLE IF EXISTS referral_{today_name};
                          CREATE TABLE IF NOT EXISTS referral_{today_name} AS SELECT * FROM referral
                          WHERE date(created) = '{today}';"""

    cursor = connection.cursor()
    cursor.execute(users_query)
    cursor.execute(influencers_query)
    cursor.execute(referrals_query)
    connection.commit()


def migrate_firebase_campaigns():
    """
    Migrating campaigns from firebase to postgres. A campaign has a list of the influencers account ids. This is named
    'inf_campaign_dict'. For each of this account, create a row in table social_account and add many-to-many relation
    between the new campaigns and contained accounts.
    """
    print(datetime.now(), "Migrating brand campaigns...")
    campaigns = []
    campaigns_docs = firebase_db.collection('brand_campaigns').stream()
    for campaign in campaigns_docs:
        campaign_data = campaign.to_dict()
        campaign_data['id'] = campaign.id
        campaigns.append(campaign_data)

    campaigns_df = DataFrame(campaigns)
    campaigns_df = campaigns_df.where(campaigns_df.notna(), None)
    campaigns_df['platform'] = campaigns_df['platform'].apply(lambda x: x[0] if type(x) == list else x)
    campaigns_df['platform'] = campaigns_df['platform'].apply(lambda x: x.lower() if x else 'instagram')
    infl_df = campaigns_df[['id', 'platform', 'inf_campaign_dict']]
    infl_df = infl_df[infl_df['inf_campaign_dict'].astype(bool)]
    campaigns_df = campaigns_df[['id', 'campaign_name', 'brand', 'platform', 'time_stamp']]
    campaigns_df['time_stamp'] = campaigns_df['time_stamp'].apply(lambda x: str(x))
    campaigns_df['created'] = str(datetime.now())
    result = write_to_db(campaigns_df.values.tolist(),
                         "campaign (id, campaign_name, brand, platform, time_stamp, created)",
                         updating=True,
                         id_tag='id',
                         updating_fields={'campaign_name', 'brand', 'platform', 'time_stamp'})
    assert result == 0, result

    for index, row in infl_df.iterrows():
        cursor = connection.cursor()
        cursor.execute(f"DELETE FROM campaign_social_account WHERE campaign_id = '{row['id']}'")
        connection.commit()
        accounts = []
        for acc_id in row['inf_campaign_dict']:
            accounts.append([acc_id, row['platform'].lower()])
        accounts_df = DataFrame(accounts, columns=['account_id', 'platform'])
        accounts_df = accounts_df.drop_duplicates(['account_id', 'platform'])

        result = write_to_db(accounts_df.values.tolist(),
                             "social_account (account_id, platform)")
        assert result == 0, result

        written_df = read_sql(f"""SELECT id as social_id, account_id, platform FROM social_account 
                WHERE account_id IN ('{"','".join(accounts_df['account_id'].values)}');""", connection)

        merged = merge(accounts_df, written_df, how='inner', on=['account_id', 'platform'])

        many_to_many = merged[['social_id']]
        many_to_many['campaign_id'] = row['id']
        result = write_to_db(many_to_many.values.tolist(),
                             "campaign_social_account (social_id, campaign_id)")
        assert result == 0, result
    print(datetime.now(), "OK")


def migrate_firebase_users():
    print(datetime.now(), "Migrating users...")
    all_uids = []
    page = auth.list_users()
    while page:
        for user in page.users:
            # Skip internal testing account
            if user.email and 'lifo.ai' in user.email:
                continue
            creation_time = datetime.utcfromtimestamp(user.user_metadata.creation_timestamp / 1000).strftime(
                '%Y-%m-%d %H:%M:%S')
            all_uids.append([user.uid, user.email, creation_time])

        page = page.get_next_page()

    users_df = DataFrame(all_uids, columns=['uid', 'email', 'creation_time'])
    users_df = users_df[~users_df['email'].isna()]
    users_df['created'] = str(datetime.now())
    result = write_to_db(users_df.values.tolist(), 'public.user')
    assert result == 0, result
    print(datetime.now(), "OK")


def migrate_firebase_influencers():
    print(datetime.now(), "Migrating influencers...")
    users_df = read_sql('SELECT * FROM public.user', connection)
    influencers = []
    influencer_docs = firebase_db.collection('influencers').stream()
    for influencer in influencer_docs:
        influencer_data = influencer.to_dict()
        if (influencer.id not in users_df['id'].values) or \
                (influencer_data.get('instagram_id') and influencer_data['instagram_id'] in ['lifoinc', 'instagram']):
            # print("influencer not in users")
            continue
        influencer_data['id'] = influencer.id
        influencers.append(influencer_data)

    init_df = DataFrame(influencers)
    infl_df = init_df[['id', 'name', 'last_name', 'instagram_id', 'phone_number', 'address1', 'address2', 'city',
                       'province', 'country', 'zip']]
    infl_df = infl_df.where(infl_df.notna(), None)
    infl_df['created'] = str(datetime.now())

    result = write_to_db(infl_df.values.tolist(),
                         'influencer (id, name, last_name, instagram_id, phone_number, address1, address2, city, '
                         'province, country, zip, created)',
                         updating=True,
                         id_tag='id',
                         updating_fields={'name', 'last_name', 'instagram_id', 'phone_number', 'address1', 'address2',
                                          'city', 'province', 'country', 'zip'})
    assert result == 0, result

    accounts_df = init_df[['id', 'instagram_id', 'tiktok_id']]
    instagram_df = accounts_df[~accounts_df['instagram_id'].isna()][['id', 'instagram_id']]
    instagram_df['platform'] = 'instagram'
    instagram_df.columns = ['id', 'account_id', 'platform']
    tiktok_df = accounts_df[~accounts_df['tiktok_id'].isna()][['id', 'tiktok_id']]
    tiktok_df['platform'] = 'tiktok'
    tiktok_df.columns = ['id', 'account_id', 'platform']
    accounts_to_write = concat([instagram_df, tiktok_df])

    if 'accounts' in init_df.columns:
        influencers = init_df[~init_df['accounts'].isna()][['id', 'accounts']]
        values_to_write = []
        for index, infl in influencers.iterrows():
            accounts = infl['accounts']
            for platform, account_id in accounts.items():
                values_to_write.append([infl['id'], account_id, platform])
        df_to_write = DataFrame(values_to_write, columns=['id', 'account_id', 'platform'])
        accounts_to_write = concat([accounts_to_write, df_to_write])

    accounts_to_write = accounts_to_write.where(accounts_to_write.notna(), None)
    accounts_to_write = accounts_to_write.drop(accounts_to_write[accounts_to_write['account_id'] == ''].index)
    accounts_to_write = accounts_to_write.drop_duplicates(['account_id', 'platform'])
    accounts_to_write = accounts_to_write[~accounts_to_write['account_id'].isna()]
    result = write_to_db(accounts_to_write.values.tolist(),
                         'social_account (influencer_id, account_id, platform)',
                         updating=True,
                         id_tag='account_id", "platform',
                         updating_fields={'influencer_id'})
    assert result == 0, result
    print(datetime.now(), "OK")


def migrate_firebase_lists():
    """
    Similar to campaigns migration. First get the lists. Then get the influencers the lists contain. If list contains
    influencers it has a field 'ins_list' that is a list of account ids. Method creates lists, social_accounts contained
    in the lists and many-to-many relations between the accounts and lists.
    """
    print(datetime.now(), "Migrating lists...")
    lists = []
    lists_docs = firebase_db.collection('influencer_list').stream()
    for list_ in lists_docs:
        list_data = list_.to_dict()
        list_data['id'] = list_.id
        lists.append(list_data)

    list_df = DataFrame(lists)
    list_df = list_df[list_df['deleted'] != True]
    list_df = list_df.where(list_df.notna(), None)
    list_df['platform'] = list_df['platform'].apply(lambda x: x or 'instagram')
    list_df = list_df.drop_duplicates(['name', 'platform'])
    df_to_write = list_df[['id', 'name', 'platform']]
    df_to_write['created'] = str(datetime.now())

    result = write_to_db(df_to_write.values.tolist(),
                         "list (id, name, platform, created)")
    assert result == 0, result

    for index, row in list_df.iterrows():
        cursor = connection.cursor()
        cursor.execute(f"DELETE FROM list_social_account WHERE list_id = '{row['id']}'")
        connection.commit()
        if not row['ins_list']:
            continue

        accounts = []
        for acc_id in row['ins_list']:
            accounts.append([acc_id, row['platform']])

        accounts_df = DataFrame(accounts, columns=['account_id', 'platform'])
        accounts_df = accounts_df.drop_duplicates(['account_id', 'platform'])

        result = write_to_db(accounts_df.values.tolist(),
                             "social_account (account_id, platform)")
        assert result == 0, result

        written_df = read_sql(f"""SELECT id as social_id, account_id, platform FROM social_account 
        WHERE account_id IN ('{"','".join(accounts_df['account_id'].values)}');""", connection)

        merged = merge(accounts_df, written_df, how='inner', on=['account_id', 'platform'])

        many_to_many = merged[['social_id']]
        many_to_many['list_id'] = row['id']
        result = write_to_db(many_to_many.values.tolist(),
                             "list_social_account (social_id, list_id)")
        assert result == 0, result
    print(datetime.now(), "OK")


def migrate_firebase_referrals():
    print(datetime.now(), "Migrating referrals...")
    influencers_id = read_sql('SELECT id FROM influencer', connection)
    referrals = []
    referrals_docs = firebase_db.collection('referrals').stream()
    for referral in referrals_docs:
        referral_data = referral.to_dict()
        if referral_data.get('referral_profile_id') and referral_data.get('referral_profile_id') not in influencers_id['id'].values:
            # print("influencer not in users")
            continue
        referral_data['id'] = referral.id
        if referral_data.get('signed_up_at'):
            referral_data['signed_up_at'] = datetime.utcfromtimestamp(referral_data['signed_up_at'] / 1000).strftime(
                    '%Y-%m-%d %H:%M:%S')
        if referral_data.get('invited_at'):
            referral_data['invited_at'] = datetime.utcfromtimestamp(referral_data['invited_at'] / 1000).strftime(
                    '%Y-%m-%d %H:%M:%S')
        referrals.append(referral_data)
    refer_df = DataFrame(referrals)
    refer_df = refer_df[['id', 'referral_profile_id', 'extra_tickets', 'instagram_id', 'invitation_source',
                         'invited_by', 'invited_to_lottery', 'signed_up_at',
                         'invited_at', 'status', 'tickets']]
    refer_df = refer_df.where(refer_df.notna(), None)
    refer_df['created'] = str(datetime.now())
    result = write_to_db(refer_df.values.tolist(),
                         "referral (id, referral_profile_id, extra_tickets, instagram_id, invitation_source, "
                         "invited_by, invited_to_lottery, signed_up_at, invited_at, status, tickets, created)",
                         updating=True,
                         id_tag='id',
                         updating_fields={'referral_profile_id', 'extra_tickets', 'instagram_id', 'invitation_source',
                                          'invited_by', 'invited_to_lottery', 'signed_up_at',
                                          'invited_at', 'status', 'tickets'})
    assert result == 0, result
    print(datetime.now(), "OK")


def write_to_db(to_db_list: list,
                table_name: str,
                updating: bool = False,
                id_tag: str = None,
                updating_fields: set = None):
    """
    :param to_db_list: list of lists with data
    :param table_name: table to update
    :param updating: true if table should be updated instead of just adding new values.
    :param id_tag: primary key. should be given with a list of fields to update.
    :param updating_fields: list of fields to update.
    :return: 0 or exception
    """
    cursor = connection.cursor()

    args_str = '(' + ('%s,' * len(to_db_list[0]))[:-1] + ')'
    values = b','.join(cursor.mogrify(args_str, x) for x in to_db_list)
    values = values.decode()

    insert_statement = f'INSERT INTO {table_name} VALUES ' + values
    conflict_statement = ' ON CONFLICT DO NOTHING'

    # if updating change conflict statement
    if updating:
        update_string = ", ".join(f"{field} = EXCLUDED.{field}" for field in updating_fields)  # updating fields to str
        conflict_statement = f' ON CONFLICT ("{id_tag}") DO UPDATE SET {update_string};'

    try:
        cursor.execute(insert_statement + conflict_statement)
        connection.commit()
    except Exception as e:
        connection.rollback()
        return e
    return 0


if __name__ == '__main__':
    migrate_firebase_users()
    migrate_firebase_influencers()
    migrate_firebase_referrals()
    get_influencer_followers()
    make_today_tables()
    migrate_firebase_lists()
    migrate_firebase_campaigns()
