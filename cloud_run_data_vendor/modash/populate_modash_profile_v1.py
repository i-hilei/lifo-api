from pandas import read_sql, DataFrame, merge
from psycopg2 import connect
from datetime import datetime
from faker import Faker
from random import choice, randint
from string import ascii_letters, digits
from json import loads
from configparser import ConfigParser
from sys import argv
from google.cloud.secretmanager import SecretManagerServiceClient

config = ConfigParser()

try:
    config.read(f'config/{argv[1]}.conf')
except IndexError:
    print("Command should be of type: python <start file> <config name>. Example: python main.py local")
    exit()
db_creds = config['DB_CREDS']
POSTGRES_USER_CREDS_SECRET = db_creds['USER_CREDS_SECRET']

secrets = SecretManagerServiceClient()
user_creds = secrets.access_secret_version(POSTGRES_USER_CREDS_SECRET).payload.data.decode("utf-8")
user_creds = loads(user_creds)
connection = connect(dbname=db_creds['DB_NAME'], user=user_creds['USER'], password=user_creds['PASSWORD'],
                     host=db_creds['HOST'], port=db_creds['PORT'])


def get_fake_followers(profile_json: dict):
    num_followers = profile_json['profile'].get('followers')
    credibility = profile_json['audience'].get('credibility')
    if all((num_followers, credibility)):
        fake_followers = num_followers - int(num_followers * credibility)
    else:
        fake_followers = None
    return fake_followers


def populate_audience_age(profiles: DataFrame):
    existed_profiles = read_sql("SELECT id as ex_id, account_id as ex_account_id, platform as ex_platform "
                                f"""FROM public.modash_profile_v1 
                                WHERE account_id IN ('{"','".join(profiles['account_id'].tolist())}');""",
                                connection)
    joined = merge(profiles, existed_profiles, left_on=['account_id', 'platform'],
                   right_on=['ex_account_id', 'ex_platform'])

    ages_to_write = []

    for index, row in joined.iterrows():
        ages = row['profile_json']['audience'].get('ages')
        if not ages:
            continue

        for age in ages:
            new_age = [row['ex_id'], age['code'], age['weight']]
            ages_to_write.append(new_age)

    if not ages_to_write:
        return
    df = DataFrame(ages_to_write, columns=['id', 'code', 'weight'])
    df = df.drop_duplicates(['id', 'code'])
    result = write_to_db(df.values.tolist(),
                         'modash_audience_age (profile_id, code, weight)',
                         updating=True,
                         id_tag='profile_id", "code',
                         updating_fields={'weight'})
    assert result == 0, result


def populate_audience_city(profiles: DataFrame):
    existed_profiles = read_sql("SELECT id as ex_id, account_id as ex_account_id, platform as ex_platform "
                                f"""FROM public.modash_profile_v1 
                                WHERE account_id IN ('{"','".join(profiles['account_id'].tolist())}');""",
                                connection)
    joined = merge(profiles, existed_profiles, left_on=['account_id', 'platform'],
                   right_on=['ex_account_id', 'ex_platform'])

    cities_to_write = []

    for index, row in joined.iterrows():
        cities = row['profile_json']['audience'].get('geoCities')
        if not cities:
            continue

        for city in cities:
            new_city = [row['ex_id'], city['name'], city['weight']]
            cities_to_write.append(new_city)

    if not cities_to_write:
        return
    cities_df = DataFrame(cities_to_write, columns=['id', 'name', 'weight'])

    cities_to_write = cities_df.drop_duplicates(['id', 'name'])

    result = write_to_db(cities_to_write.values.tolist(),
                         'modash_audience_city (profile_id, name, weight)',
                         updating=True,
                         id_tag='profile_id", "name',
                         updating_fields={'weight'})
    assert result == 0, result


def populate_audience_ethnicity(profiles: DataFrame):
    existed_profiles = read_sql("SELECT id as ex_id, account_id as ex_account_id, platform as ex_platform "
                                f"""FROM public.modash_profile_v1 
                                WHERE account_id IN ('{"','".join(profiles['account_id'].tolist())}');""",
                                connection)
    joined = merge(profiles, existed_profiles, left_on=['account_id', 'platform'],
                   right_on=['ex_account_id', 'ex_platform'])

    ethnicity_to_write = []

    for index, row in joined.iterrows():
        ethnicity = row['profile_json']['audience'].get('ethnicities')
        if not ethnicity:
            continue

        for eth in ethnicity:
            new_eth = [row['ex_id'], eth['name'], eth['code'], eth['weight']]
            ethnicity_to_write.append(new_eth)

    if not ethnicity_to_write:
        return
    df = DataFrame(ethnicity_to_write, columns=['id', 'name', 'code', 'weight'])
    df = df.drop_duplicates(['id', 'name'])
    result = write_to_db(df.values.tolist(),
                         'modash_audience_ethnicity (profile_id, name, code, weight)',
                         updating=True,
                         id_tag='profile_id", "name',
                         updating_fields={'weight'})
    assert result == 0, result


def populate_audience_gender(profiles: DataFrame):
    existed_profiles = read_sql("SELECT id as ex_id, account_id as ex_account_id, platform as ex_platform "
                                f"""FROM public.modash_profile_v1 
                                WHERE account_id IN ('{"','".join(profiles['account_id'].tolist())}');""",
                                connection)
    joined = merge(profiles, existed_profiles, left_on=['account_id', 'platform'],
                   right_on=['ex_account_id', 'ex_platform'])

    genders_to_write = []

    for index, row in joined.iterrows():
        genders = row['profile_json']['audience'].get('genders')
        if not genders:
            continue

        for gender in genders:
            new_gender = [row['ex_id'], gender['code'], gender['weight']]
            genders_to_write.append(new_gender)

    if not genders_to_write:
        return
    df = DataFrame(genders_to_write, columns=['id', 'code', 'weight'])
    df = df.drop_duplicates(['id', 'code'])
    result = write_to_db(df.values.tolist(),
                         'modash_audience_gender (profile_id, code, weight)',
                         updating=True,
                         id_tag='profile_id", "code',
                         updating_fields={'weight'})
    assert result == 0, result


def populate_audience_interest(profiles: DataFrame):
    existed_profiles = read_sql("SELECT id as ex_id, account_id as ex_account_id, platform as ex_platform "
                                f"""FROM public.modash_profile_v1 
                                WHERE account_id IN ('{"','".join(profiles['account_id'].tolist())}');""",
                                connection)
    joined = merge(profiles, existed_profiles, left_on=['account_id', 'platform'],
                   right_on=['ex_account_id', 'ex_platform'])

    interests_to_write = []

    for index, row in joined.iterrows():
        interests = row['profile_json']['audience'].get('interests')
        if not interests:
            continue

        for interest in interests:
            new_interest = [row['ex_id'], interest['name'], interest['weight']]
            interests_to_write.append(new_interest)

    if not interests_to_write:
        return
    df = DataFrame(interests_to_write, columns=['id', 'name', 'weight'])
    df = df.drop_duplicates(['id', 'name'])
    result = write_to_db(df.values.tolist(),
                         'modash_audience_interest (profile_id, name, weight)',
                         updating=True,
                         id_tag='profile_id", "name',
                         updating_fields={'weight'})
    assert result == 0, result


def populate_audience_language(profiles: DataFrame):
    existed_profiles = read_sql("SELECT id as ex_id, account_id as ex_account_id, platform as ex_platform "
                                f"""FROM public.modash_profile_v1 
                                WHERE account_id IN ('{"','".join(profiles['account_id'].tolist())}');""",
                                connection)
    joined = merge(profiles, existed_profiles, left_on=['account_id', 'platform'],
                   right_on=['ex_account_id', 'ex_platform'])

    languages_to_write = []

    for index, row in joined.iterrows():
        languages = row['profile_json']['audience'].get('languages')
        if not languages:
            continue

        for lang in languages:
            new_lang = [row['ex_id'], lang.get('name'), lang['code'], lang['weight']]
            languages_to_write.append(new_lang)

    if not languages_to_write:
        return
    df = DataFrame(languages_to_write, columns=['id', 'name', 'code', 'weight'])
    df = df.drop_duplicates(['id', 'name'])
    df = df.drop(df[df['name'].isna()].index)
    result = write_to_db(df.values.tolist(),
                         'modash_audience_language (profile_id, name, code, weight)',
                         updating=True,
                         id_tag='profile_id", "name',
                         updating_fields={'weight'})
    assert result == 0, result


def populate_profile_hashtags(profiles: DataFrame):
    existed_profiles = read_sql("SELECT id as ex_id, account_id as ex_account_id, platform as ex_platform "
                                f"""FROM public.modash_profile_v1 
                                WHERE account_id IN ('{"','".join(profiles['account_id'].tolist())}');""",
                                connection)
    joined = merge(profiles, existed_profiles, left_on=['account_id', 'platform'],
                   right_on=['ex_account_id', 'ex_platform'])

    hashtags_to_write = []

    for index, row in joined.iterrows():
        hashtags = row['profile_json'].get('hashtags')
        if not hashtags:
            continue

        for hashtag in hashtags:
            new_tag = [row['ex_id'], hashtag['tag'], hashtag['weight']]
            hashtags_to_write.append(new_tag)

    if not hashtags_to_write:
        return
    df = DataFrame(hashtags_to_write, columns=['id', 'tag', 'weight'])
    df = df.drop_duplicates(['id', 'tag'])
    result = write_to_db(df.values.tolist(),
                         'modash_profile_hashtag (profile_id, tag, weight)',
                         updating=True,
                         id_tag='profile_id", "tag',
                         updating_fields={'weight'})
    assert result == 0, result


def write_new_profiles(profiles: DataFrame):
    new_profiles = profiles[['account_id', 'platform']]
    new_profiles['timestamp'] = profiles['timestamp'].apply(str)
    new_profiles['country'] = profiles['profile_json'].apply(lambda x: x.get('country'))
    new_profiles['city'] = profiles['profile_json'].apply(lambda x: x.get('city'))
    new_profiles['language'] = profiles['profile_json'].apply(
        lambda x: x['language'].get('name') if x.get('language') else None)
    new_profiles['gender'] = profiles['profile_json'].apply(lambda x: x.get('gender'))
    new_profiles['followers'] = profiles['profile_json'].apply(lambda x: x['profile'].get('followers'))
    new_profiles['fake_followers'] = profiles['profile_json'].apply(get_fake_followers)
    new_profiles['engagements'] = profiles['profile_json'].apply(lambda x: x['profile'].get('engagements'))
    new_profiles['avg_likes'] = profiles['profile_json'].apply(lambda x: x.get('avgLikes'))
    new_profiles['avg_comments'] = profiles['profile_json'].apply(lambda x: x.get('avgComments'))
    new_profiles['age_group'] = profiles['profile_json'].apply(lambda x: x.get('ageGroup'))
    new_profiles = new_profiles.where(new_profiles.notna(), None)

    new_profiles = new_profiles.drop_duplicates(['account_id', 'platform'])

    result = write_to_db(new_profiles.values.tolist(),
                         'modash_profile_v1 (account_id, platform, timestamp, country, city, language, gender,'
                         'followers, fake_followers, engagements, avg_likes, avg_comments, age_group)',
                         updating=True,
                         id_tag='account_id", "platform',
                         updating_fields={'country', 'city', 'language', 'gender', 'followers',
                                          'fake_followers', 'engagements', 'avg_likes', 'avg_comments',
                                          'age_group'}
                         )
    assert result == 0, result


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

    for row in to_db_list:
        for value in row:
            if type(value) == str and "'" in value:
                row[row.index(value)] = value.replace("'", "''")

    values = ', '.join(str(tuple(x)) for x in to_db_list)  # list of lists to string of tuples
    insert_statement = f'INSERT INTO {table_name} VALUES {values}'.replace('None', 'NULL').replace('"', "'")
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


def populate_modash_from_raw_data(account_id: str, platform: str, profile_json: dict):
    raw_data = [[account_id, platform, profile_json, datetime.now()]]
    df = DataFrame(raw_data, columns=['account_id', 'platform', 'profile_json', 'timestamp'])
    write_new_profiles(df)
    populate_audience_age(df)
    populate_audience_city(df)
    populate_audience_ethnicity(df)
    populate_audience_gender(df)
    populate_audience_interest(df)
    populate_audience_language(df)
    populate_profile_hashtags(df)


def populate_w_fake_data(rows_num: int):
    fake = Faker()
    genders = ['MALE', 'FEMALE']
    age_groups = ["4-12", "13-17", "18-24", "25-34", "35-44", "45-64", "65+"]
    hashtags = [
        {
            "tag": "cottagestyle",
            "weight": 0.397959
        },
        {
            "tag": "cottagefarmhouse",
            "weight": 0.346939
        },
        {
            "tag": "bhghome",
            "weight": 0.295918
        },
        {
            "tag": "farmhousecharm",
            "weight": 0.295918
        },
        {
            "tag": "farmhouseinspired",
            "weight": 0.285714
        },
        {
            "tag": "homedecorinspo",
            "weight": 0.27551
        },
        {
            "tag": "neutralstyle",
            "weight": 0.265306
        },
        {
            "tag": "comfycottagecharm",
            "weight": 0.255102
        },
        {
            "tag": "antiquefinds",
            "weight": 0.255102
        },
        {
            "tag": "onetofollow",
            "weight": 0.244898
        },
        {
            "tag": "vintagefarmhouse",
            "weight": 0.244898
        },
        {
            "tag": "cottagesandbungalows",
            "weight": 0.234694
        },
        {
            "tag": "farmhousestyle",
            "weight": 0.204082
        },
        {
            "tag": "woodsandwhites",
            "weight": 0.193878
        },
        {
            "tag": "neutraldecor",
            "weight": 0.193878
        },
        {
            "tag": "betterhomesandgardens",
            "weight": 0.193878
        },
        {
            "tag": "antiquefarmhouse",
            "weight": 0.183673
        },
        {
            "tag": "cozyhome",
            "weight": 0.183673
        },
        {
            "tag": "modernfarmhouse",
            "weight": 0.173469
        },
        {
            "tag": "currentdesignsituation",
            "weight": 0.163265
        },
        {
            "tag": "mypastperfectfind",
            "weight": 0.163265
        },
        {
            "tag": "howwedwell",
            "weight": 0.153061
        },
        {
            "tag": "diyhomedecor",
            "weight": 0.153061
        },
        {
            "tag": "paintedfurniture",
            "weight": 0.153061
        },
        {
            "tag": "housebeautiful",
            "weight": 0.153061
        },
        {
            "tag": "vintagestyle",
            "weight": 0.153061
        },
        {
            "tag": "antiquefurniture",
            "weight": 0.153061
        },
        {
            "tag": "fixerupperstyle",
            "weight": 0.112245
        },
        {
            "tag": "farmhousedecor",
            "weight": 0.112245
        },
        {
            "tag": "homedecorideas",
            "weight": 0.112245
        }
    ]
    interests = [
            {
                "name": "Home Decor, Furniture & Garden",
                "weight": 0.625228
            },
            {
                "name": "Shopping & Retail",
                "weight": 0.59529
            },
            {
                "name": "Friends, Family & Relationships",
                "weight": 0.554765
            },
            {
                "name": "Toys, Children & Baby",
                "weight": 0.50931
            },
            {
                "name": "Clothes, Shoes, Handbags & Accessories",
                "weight": 0.463308
            },
            {
                "name": "Restaurants, Food & Grocery",
                "weight": 0.460022
            },
            {
                "name": "Wedding",
                "weight": 0.394852
            },
            {
                "name": "Travel, Tourism & Aviation",
                "weight": 0.325666
            },
            {
                "name": "Pets",
                "weight": 0.319825
            },
            {
                "name": "Electronics & Computers",
                "weight": 0.298467
            },
            {
                "name": "Coffee, Tea & Beverages",
                "weight": 0.289704
            },
            {
                "name": "Camera & Photography",
                "weight": 0.271449
            },
            {
                "name": "Beauty & Cosmetics",
                "weight": 0.26287
            },
            {
                "name": "Healthy Lifestyle",
                "weight": 0.249544
            },
            {
                "name": "Television & Film",
                "weight": 0.240234
            },
            {
                "name": "Business & Careers",
                "weight": 0.220153
            },
            {
                "name": "Art & Design",
                "weight": 0.215225
            },
            {
                "name": "Sports",
                "weight": 0.209566
            },
            {
                "name": "Beer, Wine & Spirits",
                "weight": 0.143666
            },
            {
                "name": "Fitness & Yoga",
                "weight": 0.138919
            },
            {
                "name": "Jewellery & Watches",
                "weight": 0.127966
            },
            {
                "name": "Cars & Motorbikes",
                "weight": 0.121942
            },
            {
                "name": "Music",
                "weight": 0.118839
            },
            {
                "name": "Luxury Goods",
                "weight": 0.106791
            },
            {
                "name": "Gaming",
                "weight": 0.074115
            },
            {
                "name": "Activewear",
                "weight": 0.052026
            },
            {
                "name": "Healthcare & Medicine",
                "weight": 0.045455
            }
        ]
    cities = [{"name": fake.city(), "weight": randint(10, 900)/1000} for i in range(20)]
    letters = [symb for symb in ascii_letters]
    digs = [dig for dig in digits]
    new_profiles = []
    for i in range(rows_num):
        print(f'\r{i}', end='')
        ethnicities = [
            {
                "code": "white",
                "name": "White / Caucasian",
                "weight": randint(10, 900) / 1000
            },
            {
                "code": "asian",
                "name": "Asian",
                "weight": randint(10, 900) / 1000
            },
            {
                "code": "african_american",
                "name": "African American",
                "weight": randint(10, 900) / 1000
            },
            {
                "code": "hispanic",
                "name": "Hispanic",
                "weight": randint(10, 900) / 1000
            }
        ]
        account_id = ''.join([choice(letters) for i in range(6)]) + ''.join([choice(digs) for i in range(2)])
        platform = choice(['instagram', 'tiktok'])
        timestamp = datetime.now()
        country = fake.country_code()
        city = fake.city()
        language = fake.language_name()
        gender = choice(genders)
        followers = randint(1000, 200000000)
        credibility = randint(1, 1000) / 1000
        engagements = randint(50, 600)
        avg_likes = randint(50, 600)
        avg_comments = randint(50, 600)
        age_group = choice(age_groups)

        audience_ages = [{"code": code, "weight": randint(10, 900)/1000} for code in age_groups]
        audience_cities = cities[randint(0, len(cities) - 1):len(cities)]
        audience_gender = []
        weight = randint(10, 900) / 1000
        audience_gender.append({"code": genders[0], "weight": weight})
        audience_gender.append({"code": genders[1], "weight": 1 - weight})

        audience_interest = interests[randint(0, len(interests) - 1):len(interests)]

        audience_languages = [{"name": fake.language_name(),
                               "code": fake.language_code(),
                               "weight": randint(10, 900) / 1000} for i in range(5)]
        profile_hashtags = hashtags[randint(0, len(hashtags) - 1):len(hashtags)]

        profile_json = {
            "profile": {
                "followers": followers,
                "engagements": engagements
            },
            "city": city,
            "country": country,
            "language": {"name": language},
            "gender": gender,
            "ageGroup": age_group,
            "avgLikes": avg_likes,
            "avgComments": avg_comments,
            "hashtags": profile_hashtags,
            "audience": {
                "ages": audience_ages,
                "languages": audience_languages,
                "geoCities": audience_cities,
                "interests": audience_interest,
                "credibility": credibility,
                "genders": audience_gender,
                "ethnicities": ethnicities
            }

        }
        info = [account_id, platform, profile_json, timestamp]
        new_profiles.append(info)

    profiles_df = DataFrame(new_profiles, columns=['account_id', 'platform', 'profile_json', 'timestamp'])
    profiles_df.drop_duplicates(['account_id', 'platform'])
    print("new profiles")
    write_new_profiles(profiles_df)
    print("ages")
    populate_audience_age(profiles_df)
    print("cities")
    populate_audience_city(profiles_df)
    print("ethnicities")
    populate_audience_ethnicity(profiles_df)
    print("genders")
    populate_audience_gender(profiles_df)
    print("interests")
    populate_audience_interest(profiles_df)
    print("languages")
    populate_audience_language(profiles_df)
    print("hashtags")
    populate_profile_hashtags(profiles_df)


if __name__ == '__main__':
    step = 500
    offset = 0
    profiles = read_sql(f"SELECT account_id, platform, profile_json, timestamp FROM modash_profile ORDER BY account_id "
                        f"LIMIT {step} "
                        f"OFFSET {offset};",
                        connection)

    while not profiles.empty:
        print("new profiles")
        write_new_profiles(profiles)
        print("ages")
        populate_audience_age(profiles)
        print("cities")
        populate_audience_city(profiles)
        print("ethnicities")
        populate_audience_ethnicity(profiles)
        print("genders")
        populate_audience_gender(profiles)
        print("interests")
        populate_audience_interest(profiles)
        print("languages")
        populate_audience_language(profiles)
        print("hashtags")
        populate_profile_hashtags(profiles)
        offset += step
        print(offset)
        profiles = read_sql(f"SELECT account_id, platform, profile_json, timestamp FROM modash_profile "
                            f"ORDER BY account_id "
                            f"LIMIT {step} "
                            f"OFFSET {offset};",
                            connection)
