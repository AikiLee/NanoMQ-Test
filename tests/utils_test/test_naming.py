from utils.naming import unique_client_id, unique_topic


def test_unique_client_id_is_unique():
    assert unique_client_id() != unique_client_id()


def test_unique_topic_keeps_prefix():
    topic = unique_topic("study/nanomq")
    assert topic.startswith("study/nanomq/")
