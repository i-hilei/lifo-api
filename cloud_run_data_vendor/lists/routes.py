from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from database import postgres_db
from influencers.models import SocialAccount
from .serializers import ListSchema
from .models import List

lists_page = Blueprint('lists_page', __name__)


@lists_page.route("/am/list/list", methods=["GET", "POST"])
def list_list():
    """
    GET - List of all lists.
    POST - Create a new list
    """
    if request.method == 'GET':
        list_schema = ListSchema()
        lists = List.query.options(joinedload('accounts')).order_by(List.created.desc()).all()
        response = []
        for list_ in lists:
            serialized = list_schema.dump(list_)
            serialized['ins_list'] = [acc.account_id for acc in list_.accounts]
            response.append(serialized)
        return jsonify(response)

    if request.method == 'POST':
        data = request.json
        name = data.get('name')
        platform = data.get('platform')
        if None in (name, platform):
            return jsonify({"Error": "Name and platform are required."}), 400

        new_list = List(name=name, platform=platform)
        list_schema = ListSchema()
        try:
            postgres_db.session.add(new_list)
            postgres_db.session.commit()
            response = list_schema.dump(new_list)
            return jsonify(response)
        except IntegrityError as err:
            response = {"Error": str(err)}
            return jsonify(response), 400


@lists_page.route("/am/list/list/<id_>", methods=["GET", "PUT", "DELETE"])
def list_list_id(id_):
    """
    GET - Info on a particular list.
    DELETE - Delete a list of the given id.
    """
    list_schema = ListSchema()
    list_ = List.query.get(id_)
    if not list_:
        return jsonify({"Error": "Not found"}), 404

    if request.method == 'DELETE':
        try:
            postgres_db.session.delete(list_)
            postgres_db.session.commit()
        except IntegrityError as err:
            response = {"Error": str(err)}
            return jsonify(response), 400
    if request.method == 'PUT':
        data = request.json
        name = data.get('name')
        platform = data.get('platform')
        if not any([name, platform]):
            return jsonify({"Error": "Provide new name or platform."}), 400

        list_.name = name
        list_.platform = platform
        try:
            postgres_db.session.add(list_)
            postgres_db.session.commit()
        except IntegrityError as err:
            response = {"Error": str(err)}
            return jsonify(response), 400
    serialized = list_schema.dump(list_)
    serialized['ins_list'] = [acc.account_id for acc in list_.accounts]
    return jsonify(serialized)


@lists_page.route("/am/list/social-account", methods=["POST", "DELETE"])
def list_social_account():
    """
    POST - Create a new relation list-social_account. Input example {"list": "2wefxsd...", "account_id": "asdfs23"}
    DELETE - Delete a relation list-social_account. Input example {"list": "2wefxsd...", "account_id": "asdfs23"}
    """
    data = request.json
    list_id = data.get('list')
    account_id = data.get('account_id')
    if not all([list_id, account_id]):
        return jsonify({"Error": f"Please provide list_id and account_id."}), 400
    list_ = List.query.get(list_id)
    if not list_:
        return jsonify({"Error": f"List with id {list_id} not found."}), 404

    account = SocialAccount.query.filter(SocialAccount.account_id == account_id, SocialAccount.platform == list_.platform)\
        .first()

    if request.method == "POST":
        if not account:
            account = SocialAccount(account_id=account_id, platform=list_.platform)
            try:
                postgres_db.session.add(account)
                postgres_db.session.commit()
            except IntegrityError as err:
                response = {"Error": f"Writing new account ot database:: {err}"}
                return jsonify(response), 400
        list_.accounts.append(account)
        response = jsonify({"Success": "Account was added to list"})
    else:
        if not account:
            return jsonify({"Error": f"Account with account_id {account_id} and platform {list_.platform} not found"}), 404
        list_.accounts.remove(account)
        response = jsonify({"Success": "Account was removed from list"})
    try:
        postgres_db.session.add(list_)
        postgres_db.session.commit()
        return response
    except IntegrityError as err:
        response = {"Error": str(err)}
        return jsonify(response), 400
