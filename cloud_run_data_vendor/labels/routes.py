import flask
from sqlalchemy.exc import IntegrityError

from database import postgres_db
from campaigns.models import Campaign
from influencers.models import SocialAccount
from shop_products.models import ShopProduct
from lists.models import List
from .serializers import LabelSchema
from .models import Label, LabelShopProduct

labels_page = flask.Blueprint('labels_page', __name__)


@labels_page.route("/am/label/label", methods=["GET", "POST"])
def label_label():
    """
    List of labels. parent=null returns root labels. parent=3 returns sub-labels of label with id = 3. To get all labels
    don't include argument 'parent'.
    Create label. Input examples
    1. For root label - {"name": "cars", type="Social", weight=0.2}
    2. For sub-label - {"name": "cars", parent=1, weight=0.4}
    """
    if flask.request.method == 'GET':
        labels_schema = LabelSchema(many=True)

        args = flask.request.args
        if args.get('parent') and args.get('parent') == 'null':
            labels = Label.query.filter_by(parent=None)
        elif args.get('parent'):
            labels = Label.query.filter_by(parent=args.get('parent'))
        else:
            labels = Label.query.all()
        serialized = labels_schema.dump(labels)
        return flask.jsonify(serialized)

    if flask.request.method == 'POST':
        data = flask.request.json
        name = data.get('name')
        type_ = data.get('type')
        parent_id = data.get('parent')
        weight = data.get('weight')
        if not name:
            return flask.jsonify({"Error": "Name is required."}), 400
        elif not parent_id and not type_:
            return flask.jsonify({"Error": "Type is required for roots."}), 400
        elif parent_id:
            parent = Label.query.get(parent_id)
            if not parent:
                return flask.jsonify({"Error": f"Parent with key {parent_id} not found."}), 400
            type_ = parent.type

        new_label = Label(name=name, parent=parent_id, type=type_, weight=weight)
        label_schema = LabelSchema()
        try:
            postgres_db.session.add(new_label)
            postgres_db.session.commit()
            response = label_schema.dump(new_label)
            return flask.jsonify(response)
        except IntegrityError as err:
            response = {"Error": str(err)}
            return flask.jsonify(response), 400


@labels_page.route("/am/label/label/<id_>", methods=["GET", "PUT", "DELETE"])
def label_label_id(id_):
    """
    GET - Information about a particular label.
    PUT - Updating a particular label.
    DELETE - Delete a particular label.
    """
    label_schema = LabelSchema()
    label = Label.query.get(id_)
    if not label:
        return flask.jsonify({"Error": "Not found"}), 404

    if flask.request.method == 'PUT':
        data = flask.request.json
        type_ = data.get('type')
        parent_id = data.get('parent')
        name = data.get('name')
        weight = data.get('weight')
        if not name:
            return flask.jsonify({"Error": "Name is required."}), 400
        elif not parent_id and not type_:
            return flask.jsonify({"Error": "Type is required for roots."}), 400
        elif parent_id:
            parent = Label.query.get(parent_id)
            if not parent:
                return flask.jsonify({"Error": f"Parent with key {parent_id} not found."}), 400
            type_ = parent.type

        label.name = name
        label.type = type_
        label.parent = parent_id
        label.weight = weight
        try:
            postgres_db.session.add(label)
            postgres_db.session.commit()
        except IntegrityError as err:
            response = {"Error": str(err)}
            return flask.jsonify(response), 400

    if flask.request.method == 'DELETE':
        try:
            postgres_db.session.delete(label)
            postgres_db.session.commit()
        except IntegrityError as err:
            response = {"Error": str(err)}
            return flask.jsonify(response), 400
    serialized = label_schema.dump(label)
    return flask.jsonify(serialized)


@labels_page.route("/am/label/social-account", methods=["GET", "POST"])
def label_social_account():
    """
    GET - Get all labels related to influencers.
    - arg. account_id=doulsf23 along with platform=instagram returns labels for the influencer that has an account
    with the given params.
    - arg. include_lists=True adds the labels of the lists that contain the given account.
    - arg. include_campaigns=True adds the labels of the campaigns that contain the given account.

    POST - Create a new relation label-influencer. Input example {"label": [2, 4], "account_id": "doulsf23",
    "platform": "instagram"}
    DELETE - Delete a relation label-influencer. Input example {"label": [2, 4], "account_id": "doulsf23",
    "platform": "instagram"}
    """
    if flask.request.method == 'GET':
        labels_schema = LabelSchema(many=True)

        args = flask.request.args
        account_id = args.get('account_id')
        platform = args.get('platform')
        include_lists = args.get('include_lists')
        include_campaigns = args.get('include_campaigns')

        if all([account_id, platform]):
            socaccs = SocialAccount.query\
                .filter(SocialAccount.account_id == account_id, SocialAccount.platform == platform).all()
        elif account_id:
            socaccs = SocialAccount.query.filter_by(account_id=account_id).all()
        else:
            return flask.jsonify({"Error": "Account id required"})

        labels = []
        for acc in socaccs:
            labels += acc.labels

        if include_lists:
            for account in socaccs:
                for list_ in account.lists:
                    labels += [label for label in list_.labels if label not in labels]

        if include_campaigns:
            for account in socaccs:
                for campaign in account.campaigns:
                    labels += [label for label in campaign.labels if label not in labels]

        serialized = labels_schema.dump(labels)
        return flask.jsonify(serialized)

    if flask.request.method == "POST":
        data = flask.request.json
        labels_id = data.get('label')
        account_id = data.get('account_id')
        platform = data.get('platform')
        if None in (labels_id, account_id, platform):
            return flask.jsonify({"Error": f"Please provide labels, account_id and platform."}), 400
        labels = Label.query.filter(Label.id.in_(labels_id)).all()
        account = SocialAccount.query\
            .filter(SocialAccount.account_id == account_id, SocialAccount.platform == platform).first()

        if not labels:
            return flask.jsonify({"Error": f"Labels with ids {labels_id} not found."}), 404
        if not account:
            return flask.jsonify({"Error": f"Account with account_id {account_id} and platform {platform} not found."}), 404

        account.labels = labels
        try:
            postgres_db.session.add(account)
            postgres_db.session.commit()
            return flask.jsonify({"Success": "Label was added to account"})
        except IntegrityError as err:
            response = {"Error": str(err)}
            return flask.jsonify(response), 400


@labels_page.route("/am/label/campaign", methods=["GET", "POST"])
def label_campaign():
    """
    GET - Get all labels related to campaigns.
    - arg. campaign=3 returns labels related to the campaign with id=3.
    - arg. include_influencers=True adds the labels of the influencers related to the given campaign.

    POST - Create a new relation label-campaign. Input example {"label": [2, 4], "campaign": 121}
    DELETE - Delete a relation label-campaign. Input example {"label": [2, 4], "campaign": 121}
    """
    if flask.request.method == 'GET':
        labels_schema = LabelSchema(many=True)
        args = flask.request.args
        campaign_id = args.get('campaign')
        include_influencers = args.get('include_influencers')

        if campaign_id:
            campaigns = Campaign.query.filter_by(id=campaign_id)
        else:
            campaigns = Campaign.query.all()

        if not campaigns:
            return flask.jsonify([])

        labels = []
        for camp in campaigns:
            labels += camp.labels
            if include_influencers:
                for infl in camp.influencers:
                    labels += infl.labels
        labels = list(set(labels))
        serialized = labels_schema.dump(labels)
        return flask.jsonify(serialized)

    if flask.request.method == "POST":
        data = flask.request.json
        labels_id = data.get('label')
        campaign_id = data.get('campaign')
        if None in (labels_id, campaign_id):
            return flask.jsonify({"Error": f"Please provide label_id and campaign_id."}), 400
        labels = Label.query.filter(Label.id.in_(labels_id)).all()
        campaign = Campaign.query.get(campaign_id)

        if not labels:
            return flask.jsonify({"Error": f"Labels with ids {labels_id} not found."}), 404
        if not campaign:
            return flask.jsonify({"Error": f"Campaign with id {campaign_id} not found."}), 404

        campaign.labels = labels
        try:
            postgres_db.session.add(campaign)
            postgres_db.session.commit()
            return flask.jsonify({"Success": "Label was added to campaign"})
        except IntegrityError as err:
            response = {"Error": str(err)}
            return flask.jsonify(response), 400


@labels_page.route("/am/label/list", methods=["GET", "POST", "DELETE"])
def label_list():
    """
    GET - Get all labels related to lists.
    - arg. list=3 returns labels related to the list with id=3.
    - arg. include_influencers=True adds the labels of the influencers related to the given list.

    POST - Create a new relation label-list. Input example {"label": [2, 4], "list": 121}
    DELETE - Delete a relation label-list. Input example {"label": [2, 4], "list": 121}
    """
    if flask.request.method == 'GET':
        labels_schema = LabelSchema(many=True)
        args = flask.request.args
        list_id = args.get('list')
        include_influencers = args.get('include_influencers')

        if list_id:
            lists = List.query.filter_by(id=list_id)
        else:
            lists = List.query.all()

        if not lists:
            return flask.jsonify([])

        labels = []
        for lst in lists:
            labels += lst.labels
            if include_influencers:
                for infl in lst.influencers:
                    labels += infl.labels
        labels = list(set(labels))
        serialized = labels_schema.dump(labels)
        return flask.jsonify(serialized)

    if flask.request.method == "POST":
        data = flask.request.json
        labels_id = data.get('label')
        list_id = data.get('list')
        if None in (labels_id, list_id):
            return flask.jsonify({"Error": f"Please provide label_id and list_id."}), 400
        labels = Label.query.filter(Label.id.in_(labels_id)).all()
        lst = List.query.get(list_id)

        if not labels:
            return flask.jsonify({"Error": f"Labels with ids {labels_id} not found."}), 404
        if not lst:
            return flask.jsonify({"Error": f"List with id {list_id} not found."}), 404

        lst.labels = labels
        try:
            postgres_db.session.add(lst)
            postgres_db.session.commit()
            return flask.jsonify({"Success": "Label was added to list"})
        except IntegrityError as err:
            response = {"Error": str(err)}
            return flask.jsonify(response), 400


@labels_page.route("/label/shop-product", methods=["GET", "POST"])
def label_shop_product():
    """
    GET - Get all labels related to shop products.
    - arg. shop=my-shop returns labels related to the products with shop=my-shop.
    - arg. product_id=2342 returns labels related to the products with product_id=2342.

    POST - Set labels to a shop product. Input example {"label": [2, 4], "shop": my-shop, "product_id": 2342}
    """
    if flask.request.method == 'GET':
        labels_schema = LabelSchema(many=True)
        args = flask.request.args
        shop = args.get('shop')
        product_id = args.get('product_id')

        label_products = LabelShopProduct.query
        if shop:
            label_products = label_products.filter_by(shop=shop)
        if product_id:
            label_products = label_products.filter_by(product_id=product_id)

        label_products = label_products.all()
        if not label_products:
            return flask.jsonify([])

        label_ids = [prod.label_id for prod in label_products]
        labels = Label.query.filter(Label.id.in_(label_ids)).all()
        serialized = labels_schema.dump(labels)
        return flask.jsonify(serialized)

    if flask.request.method == "POST":
        data = flask.request.json
        labels_id = data.get('label')
        shop = data.get('shop')
        product_id = data.get('product_id')
        if None in (labels_id, shop, product_id):
            return flask.jsonify({"Error": f"Please provide label_id, shop and product_id."}), 400
        labels = Label.query.filter(Label.id.in_(labels_id)).all()
        shop_product = ShopProduct.query.get((shop, product_id))

        if not labels:
            return flask.jsonify({"Error": f"Labels with ids {labels_id} not found."}), 404
        if not shop_product:
            shop_product = ShopProduct(shop=shop, product_id=product_id)
            postgres_db.session.add(shop_product)
            postgres_db.session.commit()

        shop_product.labels = labels
        try:
            postgres_db.session.add(shop_product)
            postgres_db.session.commit()
            return flask.jsonify({"Success": "Label was added to shop product"})
        except IntegrityError as err:
            response = {"Error": str(err)}
            return flask.jsonify(response), 400
