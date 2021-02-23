from .models import List
from serializing import ma


class ListSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = List
        include_fk = True
