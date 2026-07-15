from auth.stores.authorization_code_store import AuthorizationCodeStore


def test_create_and_consume():

    store = AuthorizationCodeStore()

    code = store.create(
        session_id="session123",
        redirect_uri="http://localhost/callback",
        code_challenge="challenge123"
    )

    auth_code = store.consume(code)

    assert auth_code is not None
    assert auth_code.session_id == "session123"
    assert auth_code.redirect_uri == "http://localhost/callback"


    auth_code = store.consume(code)

    assert auth_code is None