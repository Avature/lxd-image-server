import attr
import json


@attr.s
class Index(object):

    def __attrs_post_init__(self):
        self.root = {
            'format': 'index:1.0',
            'index': {
                'images': {
                    'datatype': 'image-downloads',
                    'path': 'streams/v1/images.json',
                    'format': 'products:1.0',
                    'products': []
                }
            }
        }

    @property
    def products(self):
        return self.root['index']['images']['products']

    def add(self, product):
        if product not in self.products:
            self.products.append(product)

    def to_json(self):
        return json.dumps(self.root)
