def assert_success_body(response):
    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    return body


def assert_data_list_body(response):
    body = assert_success_body(response)
    assert isinstance(body["data"], list)
    return body


def assert_not_found(response):
    body = response.json()
    assert response.status_code == 404
    assert body["code"] == 102


def assert_unauthorized(response):
    body = response.json()
    assert response.status_code == 401
    assert body["code"] == 104
