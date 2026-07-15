from auth.stores.oauth_request_store import OAuthRequestStore

def test_create_get_delete_session():

  store = OAuthRequestStore()

  request_id = store.create(
      client_id="claude",
      redirect_uri="http://localhost/callback",
      state="xyz",
      code_challenge="abc"
  )

  request = store.get(request_id)

  assert request is not None
  assert request.client_id == "claude"

  store.delete(request_id)
