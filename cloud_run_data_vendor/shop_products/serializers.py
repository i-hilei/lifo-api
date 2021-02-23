from .models import ShopProduct
from serializing import ma


class ShopProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ShopProduct
        include_fk = True


class InfluencerShopProductSchema(ma.Schema):

    class Meta:
        fields = ('shop', 'product_id', 'image', 'product_name', 'vendor', 'commission', 'price', 'active', 'created')


class SharedShopProductSchema(ma.Schema):

    class Meta:
        fields = ('shop', 'product_id', 'image', 'product_name', 'vendor', 'price', 'active', 'created')
