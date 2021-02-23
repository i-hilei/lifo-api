from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from database import postgres_db
from influencers.models import SocialAccount
from .serializers import CampaignScoreSchema
from .models import CampaignScore, Campaign

campaigns_page = Blueprint('campaigns_page', __name__)


@campaigns_page.route("/brand/campaigns/score", methods=["GET", "POST"])
def campaign_score():
    """
    GET - List of all campaign scores saved in db.
    POST - Create a new score
    """
    score_schema = CampaignScoreSchema()
    if request.method == 'GET':
        account_id = request.args.get('account_id')
        campaign_id = request.args.get('campaign_id')
        platform = request.args.get('platform')

        scores = CampaignScore.query

        if campaign_id:
            scores = scores.filter_by(campaign_id=campaign_id)
        if account_id:
            social_ids = SocialAccount.query.with_entities(SocialAccount.id).filter_by(account_id=account_id).all()
            social_ids = [soc[0] for soc in social_ids]
            scores = scores.filter(CampaignScore.social_id.in_(social_ids))
        if platform:
            campaign_ids = Campaign.query.with_entities(Campaign.id).filter_by(platform=platform).all()
            campaign_ids = [cam[0] for cam in campaign_ids]
            scores = scores.filter(CampaignScore.campaign_id.in_(campaign_ids))

        response = []
        for score in scores.all():
            serialized = score_schema.dump(score)
            serialized['avg_score'] = round(sum([score.email_resp, score.instruction_timelines, score.commission_demand,
                                                 score.content_eng, score.instruction_quality]) / 5, 1)
            response.append(serialized)
        return jsonify(response)

    if request.method == 'POST':
        data = request.json
        email_resp = data.get('email_rest')
        instruction_timelines = data.get('instruction_timelines')
        commission_demand = data.get('commission_demand')
        content_eng = data.get('content_eng')
        instruction_quality = data.get('instruction_quality')
        campaign_id = data.get('campaign_id')
        account_id = data.get('account_id')

        if None in (email_resp, instruction_timelines, commission_demand, content_eng, instruction_quality,
                    campaign_id, account_id):
            return jsonify({"Error": "Please provide email_resp, instruction_timelines, commission_demand, "
                                     "content_eng, instruction_quality, campaign_id and account_id"}), 400

        campaign = Campaign.query.filter_by(id=str(campaign_id)).first()

        if not campaign:
            return jsonify({"Error": f"Campaign with id {campaign_id} does not exist"}), 404

        platform = campaign.platform
        account = SocialAccount.query\
            .filter(SocialAccount.account_id == str(account_id), SocialAccount.platform == str(platform)).first()
        if not account:
            return jsonify({"Error": f"Social account with id {account_id} and platform {platform} does not exist"}), 404

        score_exists = CampaignScore.query\
            .filter(CampaignScore.social_id == account.id, CampaignScore.campaign_id == campaign_id).first()
        if score_exists:
            return jsonify({"Success": f"Score with campaign_id {campaign_id} and account_id {account_id} already exists"})

        new_score = CampaignScore(
            campaign_id=campaign_id,
            social_id=account.id,
            email_resp=email_resp,
            instruction_timelines=instruction_timelines,
            commission_demand=commission_demand,
            content_eng=content_eng,
            instruction_quality=instruction_quality
        )
        try:
            postgres_db.session.add(new_score)
            postgres_db.session.commit()
            response = score_schema.dump(new_score)
            return jsonify(response)
        except IntegrityError as err:
            response = {"Error": str(err)}
            return jsonify(response), 400


@campaigns_page.route("/brand/campaigns/score/<id_>", methods=["GET", "DELETE"])
def campaign_score_id(id_):
    score_schema = CampaignScoreSchema()
    score = CampaignScore.query.get(id_)
    if not score:
        return jsonify({"Error": "Not found"}), 404

    if request.method == 'DELETE':
        try:
            postgres_db.session.delete(score)
            postgres_db.session.commit()
            return jsonify({"Success": "Deleted"})
        except IntegrityError as err:
            response = {"Error": str(err)}
            return jsonify(response), 400

    serialized = score_schema.dump(score)
    return jsonify(serialized)
