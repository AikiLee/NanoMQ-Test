"""Offline server-certificate chain checks.

These tests do not start NanoMQ or connect to a network service. They generate a
minimal Root -> Intermediate -> Server chain in pytest's tmp_path and then use
the same OpenSSL verification path as the production helper. The goal is to
teach and lock down the server-side certificate-chain rules before adding any
live broker dependency.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from utils.cert_chain_validator import validate_certificate_chain


@dataclass(frozen=True)
class CertificateFiles:
    root_ca: Path
    intermediate_ca: Path
    server_cert: Path


@pytest.mark.tls
def test_valid_server_certificate_chain_is_accepted(tmp_path):
    """A trusted root plus intermediate should validate the server certificate."""
    certs = _build_certificate_chain(tmp_path)

    result = validate_certificate_chain(
        root_ca=certs.root_ca,
        server_cert=certs.server_cert,
        intermediates=[certs.intermediate_ca],
        expected_hostname="nanomq.local",
    )

    assert result.ok, result.output


@pytest.mark.tls
def test_server_certificate_signed_by_untrusted_ca_is_rejected(tmp_path):
    """Changing only the trust root must break the chain."""
    certs = _build_certificate_chain(tmp_path)
    wrong_root = _build_root_ca(tmp_path / "wrong-root", common_name="Wrong Root CA")

    result = validate_certificate_chain(
        root_ca=wrong_root,
        server_cert=certs.server_cert,
        intermediates=[certs.intermediate_ca],
        expected_hostname="nanomq.local",
    )

    assert not result.ok
    assert "error" in result.output.lower()


@pytest.mark.tls
def test_server_certificate_with_hostname_mismatch_is_rejected(tmp_path):
    """A valid signature chain is not enough when SAN does not match the host."""
    certs = _build_certificate_chain(tmp_path)

    result = validate_certificate_chain(
        root_ca=certs.root_ca,
        server_cert=certs.server_cert,
        intermediates=[certs.intermediate_ca],
        expected_hostname="wrong.local",
    )

    assert not result.ok
    assert "hostname" in result.output.lower()


def _build_certificate_chain(base_dir: Path) -> CertificateFiles:
    """
    Create Root -> Intermediate -> Server certificates for one test case.
    then return
    """
    root_ca = _build_root_ca(base_dir / "root", common_name="Study Root CA")

    intermediate_dir = base_dir / "intermediate"
    intermediate_dir.mkdir()
    intermediate_key = intermediate_dir / "intermediate.key"
    intermediate_csr = intermediate_dir / "intermediate.csr"
    intermediate_cert = intermediate_dir / "intermediate.pem"
    intermediate_ext = intermediate_dir / "intermediate.ext"

    # The intermediate is a CA, but pathlen=0 prevents it from creating another
    # subordinate CA. It can only issue leaf certificates in this test chain.
    _run("openssl", "genrsa", "-out", intermediate_key, "2048")
    _run(
        "openssl",
        "req",
        "-new",
        "-key",
        intermediate_key,
        "-out",
        intermediate_csr,
        "-subj",
        "/CN=Study Intermediate CA",
    )
    intermediate_ext.write_text(
        "\n".join(
            [
                "basicConstraints=critical,CA:TRUE,pathlen:0",
                "keyUsage=critical,keyCertSign,cRLSign",
                "subjectKeyIdentifier=hash",
                "authorityKeyIdentifier=keyid,issuer",
            ]
        ),
        encoding="utf-8",
    )
    _run(
        "openssl",
        "x509",
        "-req",
        "-in",
        intermediate_csr,
        "-CA",
        root_ca,
        "-CAkey",
        intermediate_dir.parent / "root" / "root.key",
        "-CAcreateserial",
        "-out",
        intermediate_cert,
        "-days",
        "365",
        "-sha256",
        "-extfile",
        intermediate_ext,
    )

    server_dir = base_dir / "server"
    server_dir.mkdir()
    server_key = server_dir / "server.key"
    server_csr = server_dir / "server.csr"
    server_cert = server_dir / "server.pem"
    server_ext = server_dir / "server.ext"

    # The server certificate is a leaf cert: CA:FALSE plus serverAuth and SAN.
    # Hostname validation later checks SAN, not just the subject CN.
    _run("openssl", "genrsa", "-out", server_key, "2048")
    _run(
        "openssl",
        "req",
        "-new",
        "-key",
        server_key,
        "-out",
        server_csr,
        "-subj",
        "/CN=nanomq.local",
    )
    server_ext.write_text(
        "\n".join(
            [
                "basicConstraints=critical,CA:FALSE",
                "keyUsage=critical,digitalSignature,keyEncipherment",
                "extendedKeyUsage=serverAuth",
                "subjectAltName=DNS:nanomq.local,IP:127.0.0.1",
                "authorityKeyIdentifier=keyid,issuer",
            ]
        ),
        encoding="utf-8",
    )
    _run(
        "openssl",
        "x509",
        "-req",
        "-in",
        server_csr,
        "-CA",
        intermediate_cert,
        "-CAkey",
        intermediate_key,
        "-CAcreateserial",
        "-out",
        server_cert,
        "-days",
        "365",
        "-sha256",
        "-extfile",
        server_ext,
    )

    return CertificateFiles(
        root_ca=root_ca,
        intermediate_ca=intermediate_cert,
        server_cert=server_cert,
    )


def _build_root_ca(root_dir: Path, common_name: str) -> Path:
    """Create a self-signed root CA used as the OpenSSL trust anchor."""
    root_dir.mkdir()
    root_key = root_dir / "root.key"
    root_cert = root_dir / "root.pem"

    _run("openssl", "genrsa", "-out", root_key, "2048")
    _run(
        "openssl",
        "req",
        "-x509",
        "-new",
        "-nodes",
        "-key",
        root_key,
        "-sha256",
        "-days",
        "365",
        "-out",
        root_cert,
        "-subj",
        f"/CN={common_name}",
        "-addext",
        "basicConstraints=critical,CA:TRUE,pathlen:1",
        "-addext",
        "keyUsage=critical,keyCertSign,cRLSign",
    )
    return root_cert


def _run(*args) -> None:
    """Run OpenSSL and fail the test immediately on command errors."""
    subprocess.run(
        [str(arg) for arg in args], check=True, capture_output=True, text=True
    )
