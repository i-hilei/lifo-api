import flask
from flask import Blueprint, request, current_app
import requests
import os
import shopify
import json
from datetime import datetime, timedelta


from cloud_sql import sql_handler

import firebase_admin
from firebase_admin import firestore

API_VERSION = os.getenv('API_VERSION', '2020-07')
MAX_SHOPIFY_RESULTS_LIMIT = 200
DEFFAULT_DATE_RANGE = 30

shopify_page = Blueprint('shopify_page', __name__)

firebase_app = firebase_admin.get_app()
db = firestore.client()


def get_shopify_access_token(shop):
    res = sql_handler.get_shop_auth(shop)
    return res


def single_shopify_product():
    shop = flask.request.args.get('shop')
    res = get_shopify_access_token(shop)
    if not res:
        res = {'status': 'access token not found'}
        response = flask.jsonify(res)
        response.status_code = 204
        return response
    shop_access_token = res

    product_id = flask.request.args.get('product_id')
    url = f'https://{shop}/admin/api/{API_VERSION}/products.json?ids={product_id}'
    current_app.logger.info(f'Receiving request for url {url}')
    headers = {"X-Shopify-Access-Token": shop_access_token}
    res = requests.get(url, headers=headers)
    data = res.json()
    products = res.json().get('products')
    if products:
        for product_json in products:
            id = product_json.get('id')
            sql_handler.save_product_info(shop, id, product_json)
        current_app.logger.info(f'Saved {len(products)} for shop {shop}')
    else:
        current_app.logger.info('No products found')
    response = flask.jsonify(data)
    response.status_code = 200
    return response


def shopify_products():
    shop = flask.request.args.get('shop')
    res = get_shopify_access_token(shop)
    if not res:
        res = {'status': 'access token not found'}
        response = flask.jsonify(res)
        response.status_code = 204
        return response
    shop_access_token = res

    if request.method == 'PUT':
        url = f'https://{shop}/admin/api/{API_VERSION}/products.json'
        current_app.logger.info(f'Receiving request for url {url}')
        headers = {"X-Shopify-Access-Token": shop_access_token}
        params = {'limit': MAX_SHOPIFY_RESULTS_LIMIT}
        res = requests.get(url, headers=headers, params=params)
        current_app.logger.info(f'Obtained shop information token {shop_access_token} for shop {shop}')
        data = res.json()
        products = res.json().get('products')
        if products:
            for product_json in products:
                product_id = product_json.get('id')
                sql_handler.save_product_info(shop, product_id, product_json)
            current_app.logger.info(f'Saved {len(products)} for shop {shop}')
        else:
            current_app.logger.info('No products found')
    else:
        current_app.logger.info(f'Retrieving product information from shop {shop}')
        tags_count = sql_handler.get_product_tags_counts(shop)
        product_images = sql_handler.get_product_images(shop)
        data = {}
        tags_count_res = [{'vendor': row[0], 'tags': row[1], 'count': row[2]} for row in tags_count]
        images_res = [{'title': row[0], 'image': row[1], 'product_id': row[2]} for row in product_images]
        data['tags_count'] = tags_count_res
        data['product_images'] = images_res
    response = flask.jsonify(data)
    response.status_code = 200
    return response


def get_shopify_shop_info(shop):
    shop_info_ref = db.document('brands', shop).get()
    if shop_info_ref.to_dict():
        current_app.logger.info('Shop info exists. Skip pulling it from Shopify API.')
        return shop_info_ref.to_dict()
    res = get_shopify_access_token(shop)
    if not res:
        res = {'status': 'access token not found'}
        response = flask.jsonify(res)
        response.status_code = 404
        return response
    shop_access_token = res
    url = f'https://{shop}/admin/api/{API_VERSION}/shop.json'
    current_app.logger.info(f'Receiving request for url {url}')
    headers = {"X-Shopify-Access-Token": shop_access_token}
    res = requests.get(url, headers=headers)
    current_app.logger.info(f'Obtained shop information for shop {shop}: {res.json()}')
    brand_ref = db.collection('brands')
    brand_ref.document(shop).set(res.json())
    sql_handler.save_shop_info(shop, res.json())
    return res.json()


@shopify_page.route('/am/shopify_product_info', methods=['GET', 'PUT'])
def am_shop_product_info():
    """
    This endpoint is called upon AM to access Shopify shop products for access_token
    """
    return shopify_products()


@shopify_page.route('/brand/shopify_product_info', methods=['GET', 'PUT'])
def brand_shop_product_info():
    """
    This endpoint is called upon AM to access Shopify shop products for access_token
    """
    return shopify_products()


@shopify_page.route('/am/shopify_single_product', methods=['GET'])
def am_get_product_info():
    """
    This endpoint is called upon AM to access Shopify shop products for access_token
    """
    return single_shopify_product()


@shopify_page.route('/brand/shopify_single_product', methods=['GET'])
def brand_get_product_info():
    """
    This endpoint is called upon AM to access Shopify shop products for access_token
    """
    return single_shopify_product()


@shopify_page.route('/am/shopify_shop_info', methods=['GET'])
def shop_info():
    """
    This endpoint is called upon AM to access Shopify shop products for access_token
    """
    shop = flask.request.args.get('shop')
    shop_info = get_shopify_shop_info(shop)
    if type(shop_info) is flask.Response:
        return shop_info
    response = flask.jsonify(shop_info)
    response.status_code = 200
    return response


@shopify_page.route('/am/shopify_customers', methods=['GET', 'PUT'])
def shop_customer_info():
    """
    This endpoint is called upon AM to access Shopify shop products for access_token
    """
    shop = flask.request.args.get('shop')
    days_range = flask.request.args.get('days_range')
    try:
        days_range = int(days_range)
    except Exception as e:
        current_app.logger.warning('Illegal days_range, revert to default value')
        days_range = DEFFAULT_DATE_RANGE
    res = get_shopify_access_token(shop)
    if not res:
        res = {'status': 'access token not found'}
        response = flask.jsonify(res)
        response.status_code = 404
        return response
    shop_access_token = res

    if request.method == 'PUT':
        created_at_min = datetime.now() - timedelta(days=days_range)
        url = f'https://{shop}/admin/api/{API_VERSION}/customers.json'
        current_app.logger.info(f'Receiving request for url {url}')
        headers = {"X-Shopify-Access-Token": shop_access_token}
        params = {'limit': MAX_SHOPIFY_RESULTS_LIMIT,
                  'created_at_min': created_at_min.isoformat()}
        res = requests.get(url, headers=headers, params=params)
        data = res.json()

        current_app.logger.info(f'Obtained shop information for shop {shop}: {data}')
        customers = data.get('customers')
        if customers:
            for customer_json in customers:
                customer_id = customer_json.get('id')
                sql_handler.save_customer_info(shop, customer_id, customer_json)
            current_app.logger.info(f'Saved {len(customers)} for shop {shop}')
        else:
            current_app.logger.info('No customers found')
    else:
        current_app.logger.info(f'Getting customer location data for shop {shop}')
        query_results = sql_handler.get_shop_customers_locations(shop)
        data = []
        for row in query_results:
            cur_res = {}
            cur_res['city'] = row[0]
            cur_res['province'] = row[1]
            cur_res['location_cnt'] = row[2]
            data.append(cur_res)
    response = flask.jsonify(data)
    response.status_code = 200
    return response


@shopify_page.route('/brand/create_campaign_payment', methods=['POST'])
def create_campaign_payment():
    """
    This endpoint is called when brand create a commission based campaign.
    He/she will need to complete payment through shopify, this endpoint will 
    only create a payment request
    """
    campaign_info = flask.request.json
    # TODO: Idealy we get shop from token
    shop = campaign_info['shop']
    res = get_shopify_access_token(shop)
    if not res:
        res = {'status': 'access token not found'}
        response = flask.jsonify(res)
        response.status_code = 404
        return response
    shop_access_token = res

    campaign_id = campaign_info['campaign_id']
    campaign_ref = db.collection('brand_campaigns').document(campaign_id)
    campaign = campaign_ref.get()
    if not campaign.exists:
        res = {'status': 'campaign not found'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response
    campaign_data = campaign.to_dict()
    campaign_name = campaign_data.get('campaign_name')

    url = f'https://{shop}/admin/api/{API_VERSION}/application_charges.json'
    current_app.logger.info(f'Receiving request for url {url}')
    headers = {"X-Shopify-Access-Token": shop_access_token}
    payload = {
        'application_charge': {
            'name': f'Upfront Payment for Campaign {campaign_name}',
            'price': campaign_info['due_amount'],
            'return_url': f"http://login.lifo.ai/app/complete-campaign-payment/{campaign_id}",
            'test': True if 'is_test' in campaign_info else False
        }
    }

    shopify_page.logger.info(f'paylod {json.dumps(payload)}')
    res = requests.post(url, json=payload, headers=headers)
    current_app.logger.info(f'Create application charge for {shop}: {res.json()}')
    campaign_ref.set(res.json(), merge=True)
    response = flask.jsonify(res.json())
    response.status_code = 200
    return response


@shopify_page.route('/brand/retrieve_campaign_charge', methods=['PUT'])
def retrieve_campaign_payment():
    """
    This endpoint is called when brand/am to update a shopify payment status
    This will also update campaign data in firestore
    """
    campaign_info = flask.request.json
    # TODO: Idealy we get shop from token
    shop = campaign_info['shop']
    res = get_shopify_access_token(shop)
    if not res:
        res = {'status': 'access token not found'}
        response = flask.jsonify(res)
        response.status_code = 404
        return response
    shop_access_token = res

    campaign_id = campaign_info['campaign_id']
    campaign_ref = db.collection('brand_campaigns').document(campaign_id)
    campaign = campaign_ref.get()
    if not campaign.exists:
        res = {'status': 'campaign not found'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response

    campaign_data = campaign.to_dict()
    charge_id  = ''
    if campaign_data.get('application_charge'):
        charge_id = campaign_data.get('application_charge').get('id')

    url = f'https://{shop}/admin/api/{API_VERSION}/application_charges/{charge_id}.json'
    current_app.logger.info(f'Receiving request for url {url}')
    headers = {"X-Shopify-Access-Token": shop_access_token}
    res = requests.get(url, headers=headers)
    current_app.logger.info(f'Retrieve charge id for {shop}: {res.json()}')
    # Status could be pending, accepted, declined
    campaign_ref.set(res.json(), merge=True)
    response = flask.jsonify(res.json())
    response.status_code = 200
    return response


@shopify_page.route('/brand/activate_campaign_charge', methods=['POST'])
def activate_campaign_payment():
    """
    This endpoint is called after shopify payment completes and we need to
    active the payment internally before payout.
    """
    campaign_info = flask.request.json
    # TODO: Idealy we get shop from token
    shop = campaign_info['shop']
    res = get_shopify_access_token(shop)
    if not res:
        res = {'status': 'access token not found'}
        response = flask.jsonify(res)
        response.status_code = 404
        return response
    shop_access_token = res

    campaign_id = campaign_info['campaign_id']
    campaign_ref = db.collection('brand_campaigns').document(campaign_id)
    campaign = campaign_ref.get()
    if not campaign.exists:
        res = {'status': 'campaign not found'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response

    campaign_data = campaign.to_dict()
    charge_id  = ''
    if campaign_data.get('application_charge'):
        charge_id = campaign_data.get('application_charge').get('id')

    url = f'https://{shop}/admin/api/{API_VERSION}/application_charges/{charge_id}/activate.json'
    current_app.logger.info(f'Receiving request for url {url}')
    headers = {"X-Shopify-Access-Token": shop_access_token}
    res = requests.post(url,  json={'application_charge': campaign_data.get('application_charge')}, headers=headers)
    current_app.logger.info(f'Retrieve charge id for {shop}: {res.json()}')
    # Status could be pending, accepted, declined
    campaign_ref.set(res.json(), merge=True)
    response = flask.jsonify(res.json())
    response.status_code = 200
    return response


@shopify_page.route('/brand/create_order', methods=['POST'])
def create_shopify_order():
    """
    This endpoint is called to when creating an order through shopify
    Currently this orddr is part of the campaign and influencer, so the campaign 
    and influencer status will be updated.
    """
    campaign_info = flask.request.json
    shop = campaign_info['shop']
    res = get_shopify_access_token(shop)
    if not res:
        res = {'error': 'access token not found'}
        response = flask.jsonify(res)
        response.status_code = 404
        return response
    shop_access_token = res

    campaign_id = campaign_info['campaign_id']
    campaign_ref = db.collection('brand_campaigns').document(campaign_id)
    campaign = campaign_ref.get()
    if not campaign.exists:
        res = {'error': 'campaign not found'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response
    influencer_ref = campaign_ref.collection('influencers').document(campaign_info['account_id'])
    influencer = influencer_ref.get()
    if not influencer.exists:
        res = {'error': 'influencer not found'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response

    influencer_data = influencer.to_dict()
    if 'order' in influencer_data:
        res = {'error': 'order already exist'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response
    variant_ids = str(campaign_info['variant_id']).split(',')
    items = []
    for variant_id in variant_ids:
        items.append({
            'price': 0,
            'variant_id': variant_id,
            'quantity': 1
        })
    
    url = f'https://{shop}/admin/api/{API_VERSION}/orders.json'
    current_app.logger.info(f'Receiving request for url {url}')
    headers = {"X-Shopify-Access-Token": shop_access_token}
    payload = {
        "order": {
            "email": campaign_info['email'],
            "shipping_address": {
                "first_name": campaign_info['first_name'],
                "last_name": campaign_info['last_name'],
                "address1": campaign_info['address_line_1'],
                "address2": campaign_info['address_line_2'] if 'address_line_2' in campaign_info else '',
                "phone": campaign_info['phone_number'],
                "city": campaign_info['city'],
                "province": campaign_info['province'],
                "country": campaign_info['country'],
                "zip": campaign_info['zip']
            },
            "line_items": items,
            "financial_status": "paid",
            "tags": 'Lifo'
        }
    }

    current_app.logger.info(f'paylod {json.dumps(payload)}')
    res = requests.post(url, json=payload, headers=headers)
    current_app.logger.info(f'Create order for {shop}: {res.json()}')
    influencer_ref.set(res.json(), merge=True)
    response = flask.jsonify(res.json())
    response.status_code = 200
    return response


@shopify_page.route('/brand/view_order', methods=['GET'])
def view_shopify_order():
    """
    This endpoint is called to retrive an order through shopify
    This call will not update status of the order in firestore
    """
    shop = flask.request.args.get('shop')
    order_id = flask.request.args.get('order_id')
    res = get_shopify_access_token(shop)
    if not res:
        res = {'status': 'access token not found'}
        response = flask.jsonify(res)
        response.status_code = 404
        return response
    shop_access_token = res

    url = f'https://{shop}/admin/api/{API_VERSION}/orders/{order_id}.json'
    current_app.logger.info(f'Receiving request for url {url}')
    headers = {"X-Shopify-Access-Token": shop_access_token}
    res = requests.get(url, headers=headers)
    current_app.logger.info(f'get order for {shop}: {res.json()}')
    # Status could be pending, accepted, declined
    response = flask.jsonify(res.json())
    response.status_code = 200
    return response


@shopify_page.route('/brand/update_order', methods=['PUT'])
def update_shopify_order():  
    """
    This endpoint is called to retrive an order through shopify
    This call will ALSO update status of the order in firestore
    """
    order_info = flask.request.json
    shop = order_info['shop']
    res = get_shopify_access_token(shop)
    if not res:
        res = {'status': 'access token not found'}
        response = flask.jsonify(res)
        response.status_code = 404
        return response
    shop_access_token = res

    campaign_id = order_info['campaign_id']
    campaign_ref = db.collection('brand_campaigns').document(campaign_id)
    campaign = campaign_ref.get()
    if not campaign.exists:
        res = {'status': 'campaign not found'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response
    influencer_ref = campaign_ref.collection('influencers').document(order_info['account_id'])
    influencer = influencer_ref.get()
    if not influencer.exists:
        res = {'status': 'influencer not found'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response

    influencer_data = influencer.to_dict()
    order_id = ''
    if influencer_data.get('order') and influencer_data.get('order').get('id'):
        order_id = influencer_data.get('order').get('id')
    if not order_id:
        res = {'status': 'order not found'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response

    url = f'https://{shop}/admin/api/{API_VERSION}/orders/{order_id}.json'
    current_app.logger.info(f'Receiving request for url {url}')
    headers = {"X-Shopify-Access-Token": shop_access_token}
    res = requests.get(url, headers=headers)
    current_app.logger.info(f'get order for {shop}: {res.json()}')
    # Status could be pending, accepted, declined
    order_data = res.json()
    # If Shipping Info
    if (order_data['order']['fulfillments'] and len(order_data['order']['fulfillments']) > 0):
        shipping_info = {
            'tracking_number': order_data['order']['fulfillments'][0]['tracking_number'],
            'carrier': order_data['order']['fulfillments'][0]['tracking_company'] 
        }
        order_data['shipping_info'] = shipping_info
        if 'product_ship_time' not in order_data:
            order_data['product_ship_time'] = datetime.datetime.fromisoformat(order_data['order']['fulfillments'][0]['created_at']).timestamp()
    influencer_ref.set(order_data, merge=True)
    response = flask.jsonify(order_data)
    response.status_code = 200
    return response


@shopify_page.route('/brand/create_price_rule', methods=['POST'])
def create_price_rule():
    """
    This endpoint is called to create price rule for a store, a price rule
    is required to create coupon code. The price rule information will be stored
    into firestore together with campaign.
    """
    price_rule_info = flask.request.json
    shop = price_rule_info['shop']
    res = get_shopify_access_token(shop)
    if not res:
        res = {'error': 'access token not found'}
        response = flask.jsonify(res)
        response.status_code = 404
        return response
    shop_access_token = res

    campaign_id = price_rule_info['campaign_id']
    campaign_ref = db.collection('brand_campaigns').document(campaign_id)
    campaign = campaign_ref.get()
    if not campaign.exists:
        res = {'error': 'campaign not found'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response

    # This 2 could be retrieve from campaign
    percent_off = price_rule_info['coupon_discount_percentage']
    product_id = price_rule_info['product_id']
    target_selection = price_rule_info['target_selection']

    url = f'https://{shop}/admin/api/{API_VERSION}/price_rules.json'
    current_app.logger.info(f'Receiving request for url {url}')
    headers = {"X-Shopify-Access-Token": shop_access_token}
    price_rule = {
        "title": f"{percent_off}OFFLIFO",
        "target_type": "line_item",
        "target_selection": target_selection, 
        "allocation_method": "across",
        "value_type": "percentage",
        "value": f"-{percent_off}",
        "customer_selection": "all",
        "starts_at": "2020-01-01T00:00:00Z"
    }
    # Handle sitewide discount
    if target_selection != 'all':
        price_rule["entitled_product_ids"] = [
            product_id
        ]
    payload = {
        "price_rule": price_rule
    }
    current_app.logger.info(f'paylod {json.dumps(payload)}')
    res = requests.post(url, json=payload, headers=headers)
    campaign_ref.set(res.json(), merge=True)
    current_app.logger.info(f'Create price rule for {shop}: {res.json()}')
    response = flask.jsonify(res.json())
    response.status_code = 200
    return response


@shopify_page.route('/brand/create_coupon_code', methods=['POST'])
def create_coupon_code():
    """
    This endpoint is called to create a coupon code for campaign/influencer,
    coupon code is based on price rule, also we can create each coupon code for 
    each influencer, and this will be stored in firebase.
    """
    coupon_code_info = flask.request.json
    shop = coupon_code_info['shop']
    res = get_shopify_access_token(shop)
    if not res:
        res = {'error': 'access token not found'}
        response = flask.jsonify(res)
        response.status_code = 404
        return response
    shop_access_token = res

    campaign_id = coupon_code_info['campaign_id']
    account_id = coupon_code_info['account_id']
    campaign_ref = db.collection('brand_campaigns').document(campaign_id)
    campaign = campaign_ref.get()
    if not campaign.exists:
        res = {'error': 'campaign not found'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response
    influencer_ref = campaign_ref.collection('influencers').document(account_id)
    influencer = influencer_ref.get()
    if not influencer.exists:
        res = {'error': 'influencer not found'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response
    
    coupon_code = coupon_code_info['coupon_code']
    price_rule_id = coupon_code_info['price_rule_id']

    url = f'https://{shop}/admin/api/{API_VERSION}/price_rules/{price_rule_id}/discount_codes.json'
    current_app.logger.info(f'Receiving request for url {url}')
    headers = {"X-Shopify-Access-Token": shop_access_token}
    payload = {
        "discount_code": {
            "code": coupon_code
        }
    }
    current_app.logger.info(f'paylod {json.dumps(payload)}')
    res = requests.post(url, json=payload, headers=headers)
    influencer_ref.set(res.json(), merge=True)
    current_app.logger.info(f'Create coupon code for {shop}: {res.json()}')
    response = flask.jsonify(res.json())
    response.status_code = 200
    return response


@shopify_page.route('/am/create_product', methods=['POST'])
def create_product():
    """
    This endpoint is called to create a product in shopify
    Implementation will be added soon.
    """
    pass


@shopify_page.route('/influencer/order_history', methods=['GET'])
def get_order_history():
    """
    This endpoint is called to retrieve historical orders from shopify
    Implementation will be added soon.
    """

    session = shopify.Session('lifo-store.myshopify.com', '2020-10', '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')
    shop_id = flask.session['uid']
    shopify.ShopifyResource.activate_session(session)
    orders = shopify.Order.find()
    print(orders)
    order_reports = []
    for order in orders:
        # print(order.order_number)
        # order.note_attributes = [
        #     {
        #         'name': 'lifo_shop_id',
        #         'value': 'ugwz63OVH3YDGK6eqnUDG3YfrR72'
        #     }
        # ]
        # order.save()
        match_order = False
        commission = 0
        for attribute in order.note_attributes:
            if attribute.name == 'commission':
                commission = attribute.value
            if attribute.name == 'lifo_shop_id' and attribute.value == shop_id:
                match_order = True

        if not match_order:
            continue
        
        for line_item in order.line_items:
            order_reports.append({
                'product_id': line_item.product_id,
                'quantity': line_item.quantity,
                'price': float(line_item.price),
                'commission': float(commission)
            })
       
    shopify.ShopifyResource.clear_session()
    
    response = flask.jsonify({'orders': order_reports})
    response.status_code = 200
    return response


@shopify_page.route('/shared/list_product', methods=['GET'])
def list_product():
    shop_items = db.collection('shop_item').stream()

    shop_items_list = []
    for item in shop_items:
        shop_items_list.append(item.to_dict())

    response = flask.jsonify({'items': shop_items_list})
    response.status_code = 200
    return response

@shopify_page.route('/am/upload_product', methods=['POST'])
def upload_product():
    product_info = flask.request.json
    product_id = product_info['product_id']
    discount = product_info['discount']
    commission = product_info['commission']
    compare_at_price = product_info['compare_at_price']
    price = product_info['price']

    session = shopify.Session('lifo-store.myshopify.com', '2020-10', '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')
    shopify.ShopifyResource.activate_session(session)
    product = shopify.Product.find(product_id)

    variants = product.variants
    for variant in variants:
        variant.price = price
        variant.compare_at_price = compare_at_price
    product.save()

    product_info['status'] = 'active'
    db.collection('shop_item').document(str(product_id)).set(product_info, merge=True)

    response = flask.jsonify({'status': 'OK'})
    response.status_code = 200
    return response


@shopify_page.route('/am/offload_product', methods=['POST'])
def offload_product():
    product_info = flask.request.json
    product_id = product_info['product_id']
    db.collection('shop_item').document(str(product_id)).set({
        'status': 'inactive',
    }, merge=True)

    response = flask.jsonify({'status': 'OK'})
    response.status_code = 200
    return response

