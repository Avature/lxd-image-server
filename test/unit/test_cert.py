import os
from lxd_image_server.tools.cert import generate_cert


class TestCert(object):

    def test_generate_cert(self, tmpdir):
        generate_cert(str(tmpdir))
        assert os.path.exists(os.path.join(str(tmpdir), 'nginx.key'))
        assert os.path.exists(os.path.join(str(tmpdir), 'nginx.crt'))
