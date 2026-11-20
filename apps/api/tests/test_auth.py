def test_registration_requires_a_verified_email_and_then_signs_in(client):
    blocked = client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "verification_token": "not-a-real-verification-token",
            "first_name": "Asha",
            "last_name": "Rao",
            "phone_country": "IN",
            "phone": "9876543210",
            "university": "NIAT - Joy University, Tirunelveli",
            "batch": "2025",
            "niat_id": "N25H05F9974",
            "password": "Hackhub1",
        },
    )
    assert blocked.status_code == 403

    sent = client.post("/api/v1/auth/email/code", json={"email": "student@example.com"})
    assert sent.status_code == 200, sent.text
    code = sent.json()["dev_code"]
    assert code and len(code) == 6

    confirmed = client.post("/api/v1/auth/email/confirm", json={"email": "student@example.com", "code": code})
    assert confirmed.status_code == 200, confirmed.text
    token = confirmed.json()["verification_token"]

    created = client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "verification_token": token,
            "first_name": "Asha",
            "last_name": "Rao",
            "phone_country": "IN",
            "phone": "9876543210",
            "university": "NIAT - Joy University, Tirunelveli",
            "batch": "2025",
            "niat_id": "N25H05F9974",
            "password": "Hackhub1",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "Asha Rao"
    assert created.json()["role"] == "student"
    assert client.get("/api/v1/auth/me").status_code == 200

    client.post("/api/v1/auth/logout")
    wrong = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "wrongpass1"})
    assert wrong.status_code == 401
    signed_in = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "Hackhub1"})
    assert signed_in.status_code == 200, signed_in.text
    assert signed_in.json()["email"] == "student@example.com"
