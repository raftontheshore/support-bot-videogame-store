def test_index_serves_the_chat_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Retro Games" in response.data