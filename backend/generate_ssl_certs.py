"""
backend/generate_ssl_certs.py
-----------------------------
Generates self-signed SSL certificates for HTTPS streaming on mobile devices.
Mobile browsers require HTTPS (or localhost) to grant camera/getUserMedia permissions.
"""

from pathlib import Path
import datetime
import ipaddress
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from backend.config.network import get_lan_ip, get_local_ipv4_addresses

CERT_DIR = Path(__file__).parent / "config"
CERT_FILE = CERT_DIR / "cert.pem"
KEY_FILE = CERT_DIR / "key.pem"


def _ip_san(ip: str):
    try:
        return x509.IPAddress(ipaddress.IPv4Address(ip))
    except ipaddress.AddressValueError:
        return None


def cert_covers_host(host: str) -> bool:
    if not CERT_FILE.exists():
        return False

    try:
        cert = x509.load_pem_x509_certificate(CERT_FILE.read_bytes())
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        return host in san.get_values_for_type(x509.DNSName) or ipaddress.IPv4Address(host) in san.get_values_for_type(x509.IPAddress)
    except Exception:
        return False


def generate_self_signed_cert(host_ip: str | None = None):
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    host_ip = host_ip or get_lan_ip()

    # Generate private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Subject & Issuer
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Border Surveillance System"),
        x509.NameAttribute(NameOID.COMMON_NAME, host_ip),
    ])

    # Subject Alternative Names (SANs)
    san_list = [x509.DNSName("localhost")]
    for ip in get_local_ipv4_addresses():
        san = _ip_san(ip)
        if san and san not in san_list:
            san_list.append(san)

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
        .sign(key, hashes.SHA256())
    )

    # Write key
    with open(KEY_FILE, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # Write cert
    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"Self-signed SSL certificate generated at:\n - {CERT_FILE}\n - {KEY_FILE}")


if __name__ == "__main__":
    generate_self_signed_cert()
