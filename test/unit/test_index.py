import json
from hamcrest import assert_that, is_, equal_to
from lxd_image_server.simplestreams.index import Index


class TestIndex(object):

    def test_generate_json(self):
        INDEX = {
            'format': 'index:1.0',
            'index': {
                'images': {
                    'datatype': 'image-downloads',
                    'path': 'streams/v1/images.json',
                    'format': 'products:1.0',
                    'products': ['product1', 'product2']
                }
            }
        }
        index = Index()
        index.add('product1')
        index.add('product2')
        out = json.loads(index.to_json())
        assert_that(out, is_(equal_to(INDEX)))

    def test_no_duplicate(self):
        INDEX = {
            'format': 'index:1.0',
            'index': {
                'images': {
                    'datatype': 'image-downloads',
                    'path': 'streams/v1/images.json',
                    'format': 'products:1.0',
                    'products': ['product1']
                }
            }
        }
        index = Index()
        index.add('product1')
        index.add('product1')
        index.add('product1')
        out = json.loads(index.to_json())
        assert_that(out, is_(equal_to(INDEX)))

    def test_update_product(self):
        INDEX = {
            'format': 'index:1.0',
            'index': {
                'images': {
                    'datatype': 'image-downloads',
                    'path': 'streams/v1/images.json',
                    'format': 'products:1.0',
                    'products': ['product1']
                }
            }
        }
        index = Index()
        index.add('product1')
        index.add('iats:xenial:amd64:default')
        index.delete('iats:xenial:amd64:default')
        out = json.loads(index.to_json())
        assert_that(out, is_(equal_to(INDEX)))

    def test_delete_all(self):
        INDEX = {
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
        index = Index()
        index.add('iats:xenial:amd64:default')
        index.delete('iats:xenial:amd64:default')
        out = json.loads(index.to_json())
        assert_that(out, is_(equal_to(INDEX)))
