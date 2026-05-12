from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path
import subprocess
import tempfile
from typing import Iterable


@dataclass(frozen=True)
class CertificateChainValidationResult:
    ok: bool
    output: str


def validate_certificate_chain(
    *,
    root_ca: str | Path,
    server_cert: str | Path,
    intermediates: Iterable[str | Path] | None = None,
    expected_hostname: str | None = None,
) -> CertificateChainValidationResult:
    root_ca_path = Path(root_ca)
    server_cert_path = Path(server_cert)
    intermediate_paths = [Path(path) for path in intermediates or []]

    missing_files = [
        str(path)
        for path in [root_ca_path, server_cert_path, *intermediate_paths]
        if not path.exists()
    ]
    if missing_files:
        return CertificateChainValidationResult(
            ok=False,
            output=f"Missing certificate file(s): {', '.join(missing_files)}",
        )

    with _untrusted_bundle(intermediate_paths) as untrusted_path:
        command = [
            "openssl",
            "verify",
            "-purpose",
            "sslserver",
            "-CAfile",
            str(root_ca_path),
        ]
        if untrusted_path is not None:
            command.extend(["-untrusted", str(untrusted_path)])
        if expected_hostname:
            command.extend(_host_verify_args(expected_hostname))
        command.append(str(server_cert_path))

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
            )
        except FileNotFoundError:
            return CertificateChainValidationResult(
                ok=False,
                output="OpenSSL executable was not found",
            )

    output = "\n".join(
        part for part in [completed.stdout.strip(), completed.stderr.strip()] if part
    )
    return CertificateChainValidationResult(
        ok=completed.returncode == 0,
        output=output,
    )


def _host_verify_args(value: str) -> list[str]:
    try:
        ip_address(value)
    except ValueError:
        return ["-verify_hostname", value]
    return ["-verify_ip", value]


class _untrusted_bundle:
    def __init__(self, intermediates: list[Path]):
        self._intermediates = intermediates
        self._temp_file: tempfile.NamedTemporaryFile | None = None

    def __enter__(self) -> Path | None:
        if not self._intermediates:
            return None
        if len(self._intermediates) == 1:
            return self._intermediates[0]

        self._temp_file = tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".pem",
            delete=False,
        )
        for certificate in self._intermediates:
            self._temp_file.write(certificate.read_bytes())
            self._temp_file.write(b"\n")
        self._temp_file.close()
        return Path(self._temp_file.name)

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._temp_file is not None:
            Path(self._temp_file.name).unlink(missing_ok=True)
