import tempfile
import os
from lxd_image_server.tools.cert import generate_cert


class TestCert(object):

    def test_generate_cert(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_cert(tmpdir)
            assert os.path.exists(os.path.join(tmpdir, 'nginx.key'))
            assert os.path.exists(os.path.join(tmpdir, 'nginx.crt'))
