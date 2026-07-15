from auth.stores.session_store import SessionStore


def test_create_get_delete_session():

    store = SessionStore()

    session_id = store.create(
        username="RAM",
        ais_token="AIS123456"
    )


    session = store.get(session_id)

    assert session is not None
    assert session.username == "RAM"
    assert session.ais_token == "AIS123456"

    store.delete(session_id)
