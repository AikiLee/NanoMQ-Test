from api_clients.base_client import BaseClient


def test_build_url_with_slash():
    client = BaseClient("http://localhost:8081/api/v4", timeout=10)

    assert client._build_url("/nodes") == "http://localhost:8081/api/v4/nodes"

    client.close()
