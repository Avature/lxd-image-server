import json
from pathlib import Path
import attr


@attr.s
class Index(object):
    path = attr.ib(default=None)
    rebuild = attr.ib(default=False)

    def __attrs_post_init__(self):
        if not self.path or not Path(self.path).exists() or self.rebuild:
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
        else:
            with open(str(Path(self.path, 'index.json'))) as json_file:
                self.root = json.load(json_file)

    @property
    def products(self):
        return self.root['index']['images']['products']

    def add(self, product):
        if product not in self.products:
            self.products.append(product)

    def delete(self, product):
        if product in self.products:
            self.products.remove(product)

    def to_json(self):
        return json.dumps(self.root)

    def save(self):
        if self.path:
            with open(str(Path(self.path, 'index.json')), 'w') as outfile:
                json.dump(self.root, outfile)
