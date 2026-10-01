"""End-to-end API flow in offline mode."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

PROFILE = {"height_cm": 178, "weight_kg": 80, "build": "athletic", "budget_tier": "standard",
           "default_mode": "mixed"}


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "navy").save(buffer, "PNG")
    return buffer.getvalue()


def _analyze(client: TestClient, hint: str, intent: str = "references", images: int = 1) -> dict:
    files = [("images", (f"{i}.png", _png(), "image/png")) for i in range(images)]
    response = client.post("/api/costumes/analyze", files=files,
                           data={"name": "Knight", "hint": hint, "intent": intent})
    assert response.status_code == 200
    return response.json()


def test_full_costume_flow() -> None:
    with TestClient(app) as client:
        assert client.put("/api/profile", json=PROFILE).status_code == 200
        concept = _analyze(client, "helmet, cape, boots, body paint")["concepts"][0]
        detail = client.post("/api/costumes/select", json={"costume_id": concept["id"]}).json()
        parts = {c["name"]: c for c in detail["components"]}

        assert parts["Body paint"]["needs_fabrication"] is False
        assert parts["Helmet"]["model3d"]["thumbnail_url"]
        assert client.get(f"/api/components/{parts['Helmet']['id']}/model.stl").status_code == 200
        assert client.get(f"/api/components/{parts['Cape']['id']}/pattern.svg").status_code == 200

        helmet = parts["Helmet"]
        steps = list(range(len(helmet["build_steps"])))
        done = client.patch(f"/api/components/{helmet['id']}",
                            json={"status": "building", "steps_done": steps}).json()
        assert done["status"] == "completed"

        boots = client.patch(f"/api/components/{parts['Boots']['id']}",
                             json={"status": "completed", "acquired_via": "buy"}).json()
        assert boots["acquired_via"] == "buy"

        progress = client.get(f"/api/costumes/{concept['id']}").json()["progress"]
        assert progress["completed"] == 2 and progress["bought"] == 1


def test_variants_create_up_to_three_concepts_and_keep_choices() -> None:
    with TestClient(app) as client:
        client.put("/api/profile", json=PROFILE)
        result = _analyze(client, "armor", intent="variants", images=4)
        ids = [c["id"] for c in result["concepts"]]
        assert len(ids) == 3
        client.post("/api/costumes/select", json={"costume_id": ids[0], "keep_ids": [ids[1]]})
        saved = {c["id"] for c in client.get("/api/costumes").json()}
        assert {ids[0], ids[1]} <= saved and ids[2] not in saved


def test_disallowed_method_is_rejected() -> None:
    with TestClient(app) as client:
        client.put("/api/profile", json={**PROFILE, "allowed_methods": ["3d_print", "buy"]})
        concept = _analyze(client, "scarf, helmet")["concepts"][0]
        detail = client.post("/api/costumes/select", json={"costume_id": concept["id"]}).json()
        assert all(c["method"] in {"3d_print", "buy"} for c in detail["components"])
        scarf = next(c for c in detail["components"] if c["name"] == "Scarf")
        response = client.patch(f"/api/components/{scarf['id']}", json={"method": "knit"})
        assert response.status_code == 422
