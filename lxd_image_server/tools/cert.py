import socket
import ipaddress
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


def get_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


def generate_cert(path):
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, socket.gethostname())])

    now = datetime.utcnow()
    basic_contraints = x509.BasicConstraints(ca=True, path_length=0)
    ip_address = get_address()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1000)
        .not_valid_before(now - timedelta(days=10))
        .not_valid_after(now + timedelta(days=10 * 365))
        .add_extension(basic_contraints, False)
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(u"localhost"),
                x509.DNSName(ip_address),
                x509.IPAddress(ipaddress.ip_address(ip_address))]),
            critical=False,)
        .sign(key, hashes.SHA256(), default_backend()))

    with open(join(path, KEY_FILE), 'wb') as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),))

    with open(join(path, CERT_FILE), 'wb') as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
