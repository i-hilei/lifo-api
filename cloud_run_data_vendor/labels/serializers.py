from .models import Label
from serializing import ma


class LabelSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Label
        include_fk = True
