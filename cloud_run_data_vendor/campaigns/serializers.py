from serializing import ma
from flask_marshmallow.fields import fields


class CampaignScoreSchema(ma.Schema):
    account_id = fields.Method('get_account_id')
    platform = fields.Method('get_platform')

    class Meta:
        fields = ('id', 'campaign_id', 'account_id', 'platform', 'email_resp', 'instruction_timelines',
                  'commission_demand', 'content_eng', 'instruction_quality')

    def get_account_id(self, obj):
        account = obj.social_account
        return account.account_id

    def get_platform(self, obj):
        campaign = obj.campaign
        return campaign.platform
