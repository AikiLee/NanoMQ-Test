import importlib.util
import subprocess
from pathlib import Path

import pytest


SCRIPT_PATH = Path("scripts/prepare_nanomq_mtls.py")


@pytest.mark.tls
def test_prepare_nanomq_mtls_generates_expected_materials(tmp_path):
    module = _load_prepare_module()

    manifest = module.prepare_materials(tmp_path)

    expected_files = [
        "root/root_ca.pem",
        "root/root_ca.key",
        "intermediate/intermediate_ca.pem",
        "intermediate/intermediate_ca.key",
        "server/server.pem",
        "server/server.key",
        "server/server_chain.pem",
        "device/device.pem",
        "device/device.key",
        "device/device_chain.pem",
        "wrong-device/wrong_device.pem",
        "wrong-device/wrong_device.key",
        "nanomq-mtls.conf",
        "manifest.json",
    ]
    for relative_path in expected_files:
        assert (tmp_path / relative_path).exists(), relative_path

    assert manifest["host"] == "127.0.0.1"
    assert manifest["port"] == 8883
    assert manifest["server_name"] == "localhost"
    assert manifest["nanomq_config"].endswith("nanomq-mtls.conf")


@pytest.mark.tls
def test_generated_materials_validate_expected_chains(tmp_path):
    module = _load_prepare_module()
    module.prepare_materials(tmp_path)

    # Server identity: client trusts Root CA and receives the intermediate chain.
    _run(
        "openssl",
        "verify",
        "-purpose",
        "sslserver",
        "-CAfile",
        tmp_path / "root/root_ca.pem",
        "-untrusted",
        tmp_path / "intermediate/intermediate_ca.pem",
        "-verify_hostname",
        "localhost",
        tmp_path / "server/server.pem",
    )
    # Device identity, full chain model: NanoMQ trusts Root CA and the client
    # sends device + intermediate.
    _run(
        "openssl",
        "verify",
        "-purpose",
        "sslclient",
        "-CAfile",
        tmp_path / "root/root_ca.pem",
        "-untrusted",
        tmp_path / "intermediate/intermediate_ca.pem",
        tmp_path / "device/device.pem",
    )
    # Platform-style direct trust model: an intermediate CA can be treated as the
    # configured trust anchor when partial chains are explicitly allowed.
    _run(
        "openssl",
        "verify",
        "-partial_chain",
        "-purpose",
        "sslclient",
        "-CAfile",
        tmp_path / "intermediate/intermediate_ca.pem",
        tmp_path / "device/device.pem",
    )


@pytest.mark.tls
def test_wrong_device_certificate_is_not_trusted_by_generated_root(tmp_path):
    module = _load_prepare_module()
    module.prepare_materials(tmp_path)

    # The wrong device cert has clientAuth, but it chains to a different root.
    completed = subprocess.run(
        [
            "openssl",
            "verify",
            "-purpose",
            "sslclient",
            "-CAfile",
            str(tmp_path / "root/root_ca.pem"),
            str(tmp_path / "wrong-device/wrong_device.pem"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "error" in f"{completed.stdout}\n{completed.stderr}".lower()


def _load_prepare_module():
    spec = importlib.util.spec_from_file_location("prepare_nanomq_mtls", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(*args):
    subprocess.run(
        [str(arg) for arg in args], check=True, capture_output=True, text=True
    )
