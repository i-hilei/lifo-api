from flask import Blueprint, request, jsonify, session
from sqlalchemy.exc import IntegrityError
import firebase_admin
from firebase_admin import firestore
import shopify
from sqlalchemy.orm import joinedload

from database import postgres_db
from .serializers import ShopProductSchema, InfluencerShopProductSchema, SharedShopProductSchema
from .models import ShopProduct
from influencers.models import SocialAccount
from labels.models import Label

shop_products_page = Blueprint('shop_products_page', __name__)

firebase_app = firebase_admin.get_app()
db = firestore.client()


def get_shop_products(permission: str):
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    search_input = request.args.get('search_input', None, type=str)
    search_field = request.args.get('search_field', 'product_name', type=str)
    ordering = request.args.get('ordering', '-created', type=str)
    ordering_field = ordering.replace('-', '')
    if permission == 'admin':
        products = ShopProduct.query
    else:
        products = ShopProduct.query.filter_by(active=True)

    if search_input and search_field in dir(ShopProduct):
        products = products.filter(getattr(ShopProduct, search_field).like(f'%{search_input}%'))

    if ordering and ordering_field in dir(ShopProduct):
        if ordering.startswith('-'):
            products = products.order_by(getattr(ShopProduct, ordering_field).desc())
        else:
            products = products.order_by(getattr(ShopProduct, ordering_field))
    products = products.paginate(page, page_size, False).items

    return products


@shop_products_page.route("/am/shop-product", methods=["GET"])
def am_shop_product():
    """
    GET - Paginated list of products.
    """
    shop_product_schema = ShopProductSchema(many=True)
    serialized = shop_product_schema.dump(get_shop_products('admin'))
    return jsonify(serialized)


@shop_products_page.route("/influencer/shop-product", methods=["GET"])
def brand_shop_product():
    """
    GET - Paginated list of products.
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    search_input = request.args.get('search_input', None, type=str)
    ordering = request.args.get('ordering', None, type=str)
    if any([search_input, ordering]):
        shop_product_schema = InfluencerShopProductSchema(many=True)
        serialized = shop_product_schema.dump(get_shop_products('influencer'))
        return jsonify(serialized)

    shop_product_schema = InfluencerShopProductSchema(many=True)
    accounts = SocialAccount.query.options(joinedload('lists'),
                                           joinedload('campaigns'),
                                           joinedload('labels')).filter_by(influencer_id=session['uid']).all()
    if not accounts:
        serialized = shop_product_schema.dump(get_shop_products('influencer'))
        return jsonify(serialized)

    influencer_labels = []
    for account in accounts:
        influencer_labels += account.labels
        for lst in account.lists:
            influencer_labels += lst.labels
        for campaign in account.campaigns:
            influencer_labels += campaign.labels
    influencer_labels = list(set(influencer_labels))

    infl_label_ids = [label.id for label in influencer_labels]
    preferred_product_labels = Label.query.options(joinedload('shop_products'))\
        .filter(Label.infl_ref.in_(infl_label_ids)).all()
    preferred_products = []
    for label in preferred_product_labels:
        preferred_products += label.shop_products

    preferred_ids = [prod.product_id for prod in preferred_products]
    preferred_shops = [prod.shop for prod in preferred_products]
    preferred_count = len(preferred_products)
    end_point = page * page_size
    preferred = ShopProduct.query.filter(ShopProduct.active == True,
                                         ShopProduct.shop.in_(preferred_shops),
                                         ShopProduct.product_id.in_(preferred_ids)).order_by(ShopProduct.created.desc())
    if preferred_count > end_point:
        result = preferred.paginate(page, page_size, False).items
    elif preferred_count <= end_point and end_point - preferred_count < page_size:
        preferred = preferred.paginate(page, page_size, False).items
        products = ShopProduct.query.filter(ShopProduct.active == True,
                                            ~ShopProduct.shop.in_(preferred_shops),
                                            ~ShopProduct.product_id.in_(preferred_ids)).order_by(ShopProduct.created.desc())
        products = products.paginate(1, end_point - preferred_count, False).items
        result = preferred + products
    else:
        products = ShopProduct.query.filter(ShopProduct.active == True,
                                            ~ShopProduct.shop.in_(preferred_shops),
                                            ~ShopProduct.product_id.in_(preferred_ids)).order_by(ShopProduct.created.desc())
        result = products.paginate(page, page_size, False).items
    return jsonify(shop_product_schema.dump(result))


@shop_products_page.route("/shared/shop-product", methods=["GET"])
def shared_shop_product():
    """
    GET - Paginated list of products.
    """
    shop_product_schema = SharedShopProductSchema(many=True)
    serialized = shop_product_schema.dump(get_shop_products('shared'))
    return jsonify(serialized)


@shop_products_page.route("/am/shop-product/<shop>__<id_>", methods=["GET", "PUT", "PATCH", "DELETE"])
def shop_product_id(shop, id_):
    """
    GET - Info on a particular product.
    PUT - Update a particular product.
    DELETE - Delete a particular product.
    """
    product_schema = ShopProductSchema()
    product = ShopProduct.query.get((shop, id_))
    if not product:
        return jsonify({"Error": "Not found"}), 404

    if request.method in ('PUT', 'PATCH'):
        data = request.json
        price = data.get('price')
        compare_at_price = data.get('compare_at_price')
        active = data.get('active')

        if all([active, price, compare_at_price]):
            session = shopify.Session('lifo-store.myshopify.com', '2020-10',
                                      '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')
            shopify.ShopifyResource.activate_session(session)
            product = shopify.Product.find(id_)

            variants = product.variants
            for variant in variants:
                variant.price = price
                variant.compare_at_price = compare_at_price
            product.save()

        for key, value in data.items():
            if key in dir(ShopProduct):
                setattr(product, key, value)
        postgres_db.session.add(product)
        postgres_db.session.commit()

    if request.method == 'DELETE':
        try:
            postgres_db.session.delete(product)
            postgres_db.session.commit()
        except IntegrityError as err:
            response = {"Error": str(err)}
            return jsonify(response), 400
    serialized = product_schema.dump(product)
    return jsonify(serialized)
