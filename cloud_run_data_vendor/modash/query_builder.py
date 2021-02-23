def add_to_query(query: str, amend: str):
    if query.endswith('WHERE '):
        query += f"{amend} "
    else:
        query += f'AND {amend} '
    return query


def get_city_of_language(old_query: str, request: dict, key: str):
    perc_from = request[f'audience_{key}_from']/100 if request.get(f'audience_{key}_from') else None
    perc_to = request[f'audience_{key}_to']/100 if request.get(f'audience_{key}_to') else None
    if all([perc_from, perc_to]):
        query = add_to_query(old_query,
                             f"id IN (SELECT profile_id FROM modash_audience_{key} " 
                             f"WHERE name = '{request.get(f'audience_{key}')}' AND {perc_from} <= weight AND "
                             f"weight <= {perc_to})")
    elif perc_from:
        query = add_to_query(old_query,
                             f"id IN (SELECT profile_id FROM modash_audience_{key} " 
                             f"WHERE name = '{request.get(f'audience_{key}')}' AND {perc_from} <= weight)")
    elif perc_to:
        query = add_to_query(old_query,
                             f"id IN (SELECT profile_id FROM modash_audience_{key} " 
                             f"WHERE name = '{request.get(f'audience_{key}')}' AND weight <= {perc_to})")
    else:
        query = add_to_query(old_query,
                             f"id IN (SELECT profile_id FROM modash_audience_{key} " 
                             f"WHERE name = '{request.get(f'audience_{key}')}'")
    return query


def get_filter_query(request: dict, count: bool = False):
    if count:
        query = "SELECT COUNT(account_id) FROM modash_profile_v1 WHERE "
    else:
        query = "SELECT account_id, platform, followers, fake_followers, engagements, avg_likes, avg_comments, gender," \
                "age_group, country, city, language FROM modash_profile_v1 WHERE "

    for key, value in request.items():
        if not value:
            continue

        if key == 'country':
            query = add_to_query(query, f"""country IN ('{"','".join(value)}', NULL)""")
        if key == 'city':
            query = add_to_query(query, f"""city IN ('{"','".join(value)}', NULL)""")
        if key == 'language':
            query = add_to_query(query, f"""language IN ('{"','".join(value)}', NULL)""")
        if key == 'gender':
            query = add_to_query(query, f"""gender IN ('{"','".join(value)}', NULL)""")

        if key == 'followers_from':
            query = add_to_query(query, f'{value} <= followers')
            request['followers_from'] = None
        if key == 'followers_to':
            query = add_to_query(query, f'followers <= {value}')
            request['followers_to'] = None

        if key == 'engagement_from':
            query = add_to_query(query, f'{value} <= engagements')
            request['engagement_from'] = None
        if key == 'engagement_to':
            query = add_to_query(query, f'engagements <= {value}')
            request['engagement_to'] = None

        if key == 'audience_city':
            query = get_city_of_language(query, request, 'city')
        if key == 'audience_language':
            query = get_city_of_language(query, request, 'language')
        if key == 'audience_ethnicity':
            query = add_to_query(query, f"""audience_ethnicity = '{value}'""")
        if key == 'audience_age':
            query = add_to_query(query, f"""audience_age IN ('{"','".join(value)}', NULL)""")
        if key == 'audience_gender':
            query = add_to_query(query, f"""audience_gender = '{value}'""")
        if key == 'hashtag':
            query = add_to_query(query,
                                 f"""id IN (SELECT profile_id FROM modash_profile_hashtag WHERE tag IN ('{"','".join(value)}'))""")
        if key == 'interests':
            query = add_to_query(query,
                                 f"""id IN (SELECT profile_id FROM modash_audience_interest WHERE name IN ('{"','".join(value)}'))""")

    if query.endswith('WHERE '):
        query.replace('WHERE ', '')

    if not count:
        page = request.get('page') or 1
        page_size = request.get('page_size') or 15
        sort_by = request.get('sort_by') or ('account_id', 'ASC')

        query += f"ORDER BY {sort_by[0]} {sort_by[1]} LIMIT {page_size} OFFSET {(page - 1) * page_size};"
    return query
