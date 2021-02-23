import shopify


def migrate_items(shop='dreamegg.myshopify.com', token='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'):
    session = shopify.Session(shop, '2020-10', token)
    # 
    shopify.ShopifyResource.activate_session(session)

    products = shopify.Product.find()
    for product in products:
        print(product.to_dict())

    shopify.ShopifyResource.clear_session


    session = shopify.Session('lifo-store.myshopify.com', '2020-10', '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')
    shopify.ShopifyResource.activate_session(session)
    for product in products:
        new_product = shopify.Product()
        new_product.title = product.title
        new_product.body_html = product.body_html
        new_product.vendor = product.vendor
        new_product.product_type = product.product_type
        new_product.handle = product.handle
        new_product.template_suffix = product.template_suffix
        # new_product.status = product.status
        new_product.published_scope = product.published_scope
        new_product.tags = product.tags
        for variant in product.variants:
            variant.fulfillment_service = 'manual'
            variant.image_id = None
        new_product.variants = product.variants
        new_product.options = product.options
        new_product.images = product.images
        new_product.image = product.image
        result = new_product.save()
        print(result)

        # for variant in product.variants:
        #     new_variant = shopify.Variant()
        #     new_variant.product_id = new_product.id
        #     new_variant.title = 'ABC'
        #     new_variant.price = variant.price
        #     new_variant.compare_at_price = variant.compare_at_price
        #     new_variant.sku = variant.sku
        #     # new_variant.position = 2
        #     new_variant.inventory_policy = variant.inventory_policy
        #     # new_variant.fulfillment_service = variant.fulfillment_service
        #     new_variant.inventory_management = None
        #     # new_variant.inventory_item_id = variant.inventory_item_id
        #     # new_variant.inventory_quantity = variant.inventory_quantity
        #     # new_variant.old_inventory_quantity = variant.old_inventory_quantity
        #     new_variant.option1 = variant.option1
        #     new_variant.option2 = variant.option2
        #     new_variant.option3 = variant.option3
        #     new_variant.taxable = variant.taxable
        #     new_variant.barcode = variant.barcode
        #     new_variant.grams = variant.grams
        #     new_variant.image_id = variant.image_id
        #     new_variant.weight = variant.weight
        #     new_variant.weight_unit = variant.weight_unit
        #     new_variant.requires_shipping = variant.requires_shipping
        #     result = new_variant.save()
        #     print(result)
            
        # result = new_product.save()
        # print(result)
#def 

def update_inventory(shop='dreamegg.myshopify.com', token='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'):
    session = shopify.Session(shop, '2020-10', token)
    shopify.ShopifyResource.activate_session(session)
    products = shopify.Product.find()
    shopify.ShopifyResource.clear_session

    session = shopify.Session('lifo-store.myshopify.com', '2020-10', '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')
    shopify.ShopifyResource.activate_session(session)

    for product in products:
        print(product.title)
        internal_products = shopify.Product.find(title=product.title)
        for new_product in internal_products:
            if product.title == new_product.title:
                print(product.to_dict())
                print(new_product.to_dict())
                for i in range(len(new_product.variants)):
                    if new_product.variants[i].inventory_management is not None:
                        inventory_item = shopify.InventoryLevel.find(inventory_item_ids=new_product.variants[i].inventory_item_id)
                        for item in inventory_item:
                            print(item.to_dict())
                            shopify.InventoryLevel.set(location_id=item.location_id, inventory_item_id=new_product.variants[i].inventory_item_id, available=product.variants[i].inventory_quantity)


def list_orders(): 
    session = shopify.Session('lifo-store.myshopify.com', '2020-10', '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')
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
            print(attribute.name)
            print(attribute.value)
            # if attribute.name == 'commission':
            #     commission = attribute.value
            # if attribute.name == 'lifo_shop_id' and attribute.value == shop_id:
            #     match_order = True

        # if not match_order:
        #     continue
        
        # for line_item in order.line_items:
        #     order_reports.append({
        #         'product_id': line_item.product_id,
        #         'quantity': line_item.quantity,
        #         'price': float(line_item.price),
        #         'commission': float(commission)
        #     })
       
    shopify.ShopifyResource.clear_session()

list_orders()
# migrate_items('ihealthlabsonline.myshopify.com', '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')
# update_inventory('ihealthlabsonline.myshopify.com', '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')

# migrate_items('toppinlife.myshopify.com', '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')
# migrate_items('uligota-store.myshopify.com', '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')
# update_inventory('toppinlife.myshopify.com', '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')
# update_inventory('uligota-store.myshopify.com', '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')


