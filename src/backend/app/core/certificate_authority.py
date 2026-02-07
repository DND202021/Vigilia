"""Certificate Authority for generating device X.509 certificates."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class CertificateAuthorityError(Exception):
    """Certificate authority related errors."""
    pass


class CertificateAuthority:
    """Internal CA for signing device certificates.

    Generates X.509 certificates for device authentication with MQTT broker.
    Each certificate has device_id in CN and agency_id in Organization.
    """

    def __init__(self, ca_cert_path: str, ca_key_path: str):
        """Initialize CA with certificate and private key.

        Args:
            ca_cert_path: Path to CA certificate PEM file
            ca_key_path: Path to CA private key PEM file

        Raises:
            CertificateAuthorityError: If CA files cannot be loaded
        """
        try:
            # Load CA certificate
            ca_cert_file = Path(ca_cert_path)
            if not ca_cert_file.exists():
                raise CertificateAuthorityError(
                    f"CA certificate not found: {ca_cert_path}. "
                    f"Ensure CA cert is mounted at the configured path."
                )

            with open(ca_cert_path, "rb") as f:
                self.ca_cert = x509.load_pem_x509_certificate(f.read())

            # Load CA private key
            ca_key_file = Path(ca_key_path)
            if not ca_key_file.exists():
                raise CertificateAuthorityError(
                    f"CA private key not found: {ca_key_path}. "
                    f"Ensure CA key is mounted at the configured path."
                )

            with open(ca_key_path, "rb") as f:
                self.ca_key = serialization.load_pem_private_key(f.read(), password=None)

        except FileNotFoundError as e:
            raise CertificateAuthorityError(
                f"CA files not found. Check ca_cert_path and ca_key_path settings. Error: {e}"
            )
        except Exception as e:
            raise CertificateAuthorityError(
                f"Failed to load CA certificate or key: {e}"
            )

    def generate_device_certificate(
        self,
        device_id: str,
        agency_id: str,
        validity_days: int = 365
    ) -> tuple[bytes, bytes]:
        """Generate device certificate and private key.

        Certificate details:
        - CN: device_{device_id}
        - Organization: agency_{agency_id}
        - Key size: 2048-bit RSA
        - Signature: SHA256
        - Extensions: BasicConstraints(ca=False), ExtendedKeyUsage(CLIENT_AUTH)

        Args:
            device_id: UUID of the device
            agency_id: UUID of the agency owning the device
            validity_days: Certificate validity period (default 365 days)

        Returns:
            Tuple of (certificate_pem, private_key_pem) as bytes

        Raises:
            CertificateAuthorityError: If certificate generation fails
        """
        try:
            # Generate device private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            # Build certificate subject with device_id and agency_id
            subject = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, f"device_{device_id}"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, f"agency_{agency_id}"),
            ])

            # Build certificate
            builder = x509.CertificateBuilder()
            builder = builder.subject_name(subject)
            builder = builder.issuer_name(self.ca_cert.subject)
            builder = builder.public_key(private_key.public_key())
            builder = builder.serial_number(x509.random_serial_number())
            builder = builder.not_valid_before(datetime.now(timezone.utc))
            builder = builder.not_valid_after(
                datetime.now(timezone.utc) + timedelta(days=validity_days)
            )

            # Add extensions for client authentication
            builder = builder.add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            builder = builder.add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
                critical=True,
            )

            # Sign certificate with CA private key
            certificate = builder.sign(self.ca_key, hashes.SHA256())

            # Serialize to PEM format
            cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            return cert_pem, key_pem

        except Exception as e:
            raise CertificateAuthorityError(
                f"Failed to generate device certificate: {e}"
            )
