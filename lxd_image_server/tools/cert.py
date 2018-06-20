from socket import gethostname
from os.path import join
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


CERT_FILE = "nginx.crt"
KEY_FILE = "nginx.key"


def generate_cert(path):
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, gethostname())])

    basic_contraints = x509.BasicConstraints(ca=True, path_length=0)
    now = datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1000)
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=10 * 365))
        .add_extension(basic_contraints, False)
        .sign(key, hashes.SHA256(), default_backend()))

    cert_data = cert.public_bytes(encoding=serialization.Encoding.PEM)
    key_data = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),)

    with open(join(path, CERT_FILE), 'wb') as pem_out:
        for line in cert_data.splitlines():
            pem_out.write(line)

    with open(join(path, KEY_FILE), 'wb') as pem_out:
        for line in key_data.splitlines():
            pem_out.write(line)
