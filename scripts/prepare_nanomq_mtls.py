from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".tmp" / "nanomq-mtls"


def prepare_materials(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    """Generate a disposable PKI and NanoMQ config for local mTLS tests."""
    base_dir = Path(output_dir)
    _reset_dir(base_dir)

    # The test PKI mirrors a common production shape: an offline-ish root signs an
    # intermediate, and the intermediate signs all leaf certificates.
    root = _build_root_ca(base_dir / "root", common_name="NanoMQ mTLS Root CA")
    intermediate = _build_intermediate_ca(
        base_dir / "intermediate",
        root_cert=root["cert"],
        root_key=root["key"],
        common_name="NanoMQ mTLS Intermediate CA",
    )
    server = _build_leaf_certificate(
        base_dir / "server",
        ca_cert=intermediate["cert"],
        ca_key=intermediate["key"],
        common_name="localhost",
        ext_lines=[
            "basicConstraints=critical,CA:FALSE",
            "keyUsage=critical,digitalSignature,keyEncipherment",
            "extendedKeyUsage=serverAuth",
            "subjectAltName=DNS:localhost,IP:127.0.0.1",
            "subjectKeyIdentifier=hash",
            "authorityKeyIdentifier=keyid,issuer",
        ],
        output_stem="server",
    )
    device = _build_leaf_certificate(
        base_dir / "device",
        ca_cert=intermediate["cert"],
        ca_key=intermediate["key"],
        common_name="nanomq-mtls-device-001",
        ext_lines=[
            "basicConstraints=critical,CA:FALSE",
            "keyUsage=critical,digitalSignature,keyEncipherment",
            "extendedKeyUsage=clientAuth",
            "subjectKeyIdentifier=hash",
            "authorityKeyIdentifier=keyid,issuer",
        ],
        output_stem="device",
    )
    wrong_root = _build_root_ca(
        base_dir / "wrong-root",
        common_name="NanoMQ mTLS Wrong Root CA",
    )
    wrong_device = _build_leaf_certificate(
        base_dir / "wrong-device",
        ca_cert=wrong_root["cert"],
        ca_key=wrong_root["key"],
        common_name="nanomq-mtls-wrong-device",
        ext_lines=[
            "basicConstraints=critical,CA:FALSE",
            "keyUsage=critical,digitalSignature,keyEncipherment",
            "extendedKeyUsage=clientAuth",
            "subjectKeyIdentifier=hash",
            "authorityKeyIdentifier=keyid,issuer",
        ],
        output_stem="wrong_device",
    )

    # NanoMQ trusts the root CA. Clients and the server therefore send their leaf
    # certificate plus the intermediate so the peer can build a complete chain.
    server_chain = base_dir / "server" / "server_chain.pem"
    _write_chain(server_chain, [server["cert"], intermediate["cert"]])
    device_chain = base_dir / "device" / "device_chain.pem"
    _write_chain(device_chain, [device["cert"], intermediate["cert"]])

    nanomq_config = base_dir / "nanomq-mtls.conf"
    nanomq_config.write_text(
        _nanomq_config(
            server_key=server["key"],
            server_chain=server_chain,
            client_ca=root["cert"],
        ),
        encoding="utf-8",
    )

    manifest = {
        "host": "127.0.0.1",
        "port": 8883,
        "server_name": "localhost",
        "nanomq_config": str(nanomq_config),
        "certificates": {
            "root_ca": str(root["cert"]),
            "intermediate_ca": str(intermediate["cert"]),
            "server_cert": str(server["cert"]),
            "server_key": str(server["key"]),
            "server_chain": str(server_chain),
            "device_cert": str(device["cert"]),
            "device_key": str(device["key"]),
            "device_chain": str(device_chain),
            "wrong_device_cert": str(wrong_device["cert"]),
            "wrong_device_key": str(wrong_device["key"]),
        },
    }
    manifest_path = base_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest["manifest"] = str(manifest_path)
    return manifest


def _build_root_ca(root_dir: Path, common_name: str) -> dict[str, Path]:
    """Create a self-signed trust anchor used by NanoMQ's cacertfile."""
    root_dir.mkdir(parents=True, exist_ok=True)
    root_key = root_dir / "root_ca.key"
    root_cert = root_dir / "root_ca.pem"

    _run("openssl", "genrsa", "-out", root_key, "4096")
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
        "3650",
        "-out",
        root_cert,
        "-subj",
        f"/CN={common_name}",
        "-addext",
        "basicConstraints=critical,CA:TRUE,pathlen:1",
        "-addext",
        "keyUsage=critical,keyCertSign,cRLSign",
        "-addext",
        "subjectKeyIdentifier=hash",
    )
    return {"key": root_key, "cert": root_cert}


def _build_intermediate_ca(
    output_dir: Path,
    *,
    root_cert: Path,
    root_key: Path,
    common_name: str,
) -> dict[str, Path]:
    """Create the CA that signs the server and device leaf certificates."""
    output_dir.mkdir(parents=True, exist_ok=True)
    key = output_dir / "intermediate_ca.key"
    csr = output_dir / "intermediate_ca.csr"
    cert = output_dir / "intermediate_ca.pem"
    ext = output_dir / "intermediate_ca.ext"

    _run("openssl", "genrsa", "-out", key, "4096")
    _run(
        "openssl",
        "req",
        "-new",
        "-key",
        key,
        "-out",
        csr,
        "-subj",
        f"/CN={common_name}",
    )
    _write_ext(
        ext,
        [
            "basicConstraints=critical,CA:TRUE,pathlen:0",
            "keyUsage=critical,keyCertSign,cRLSign",
            "subjectKeyIdentifier=hash",
            "authorityKeyIdentifier=keyid,issuer",
        ],
    )
    _run(
        "openssl",
        "x509",
        "-req",
        "-in",
        csr,
        "-CA",
        root_cert,
        "-CAkey",
        root_key,
        "-CAcreateserial",
        "-out",
        cert,
        "-days",
        "1825",
        "-sha256",
        "-extfile",
        ext,
    )
    return {"key": key, "cert": cert}


def _build_leaf_certificate(
    output_dir: Path,
    *,
    ca_cert: Path,
    ca_key: Path,
    common_name: str,
    ext_lines: list[str],
    output_stem: str,
) -> dict[str, Path]:
    """Create a non-CA certificate for either serverAuth or clientAuth."""
    output_dir.mkdir(parents=True, exist_ok=True)
    key = output_dir / f"{output_stem}.key"
    csr = output_dir / f"{output_stem}.csr"
    cert = output_dir / f"{output_stem}.pem"
    ext = output_dir / f"{output_stem}.ext"

    _run("openssl", "genrsa", "-out", key, "2048")
    _run(
        "openssl",
        "req",
        "-new",
        "-key",
        key,
        "-out",
        csr,
        "-subj",
        f"/CN={common_name}",
    )
    _write_ext(ext, ext_lines)
    _run(
        "openssl",
        "x509",
        "-req",
        "-in",
        csr,
        "-CA",
        ca_cert,
        "-CAkey",
        ca_key,
        "-CAcreateserial",
        "-out",
        cert,
        "-days",
        "365",
        "-sha256",
        "-extfile",
        ext,
    )
    return {"key": key, "cert": cert}


def _nanomq_config(*, server_key: Path, server_chain: Path, client_ca: Path) -> str:
    # verify_peer + fail_if_no_peer_cert makes this a true mTLS listener:
    # clients must present a certificate signed by client_ca.
    return f"""listeners.ssl {{
  bind = "0.0.0.0:8883"
  keyfile = "{server_key}"
  certfile = "{server_chain}"
  cacertfile = "{client_ca}"
  verify_peer = true
  fail_if_no_peer_cert = true
}}
"""


def _write_ext(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_chain(path: Path, certs: list[Path]) -> None:
    path.write_text(
        "\n".join(cert.read_text(encoding="utf-8").strip() for cert in certs) + "\n",
        encoding="utf-8",
    )


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def _run(*args: object) -> None:
    subprocess.run(
        [str(arg) for arg in args],
        check=True,
        capture_output=True,
        text=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate temporary NanoMQ mTLS certificates and config."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory. Default: {DEFAULT_OUTPUT_DIR}",
    )
    args = parser.parse_args()

    manifest = prepare_materials(args.output_dir)
    print(f"Generated NanoMQ mTLS materials in {args.output_dir}")
    print(f"Manifest: {manifest['manifest']}")
    print(f"NanoMQ config: {manifest['nanomq_config']}")


if __name__ == "__main__":
    main()
