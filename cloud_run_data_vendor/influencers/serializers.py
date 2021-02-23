from .models import Unsubscribed
from serializing import ma


class UnsubscribedSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Unsubscribed
        fields = ('email', )
