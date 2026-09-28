import os
import sys
import unittest
from fastapi.testclient import TestClient
from app import app, users_db

client = TestClient(app)

class TestPocketSmartAI(unittest.TestCase):

    def test_01_landing_page(self):
        """Test landing page serves HTML with 200 OK"""
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("PocketSmart AI", response.text)
        self.assertIn("Our Smart Budget Planners", response.text)

    def test_02_auth_flow(self):
        """Test user registration and login flow"""
        import uuid
        uname = f"tester_{uuid.uuid4().hex[:6]}"
        reg_payload = {
            "username": uname,
            "email": f"{uname}@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "full_name": "Test User"
        }
        res_reg = client.post("/register", json=reg_payload)
        self.assertEqual(res_reg.status_code, 200)
        self.assertIn("access_token", res_reg.json())

        # Test login
        login_payload = {
            "username": uname,
            "password": "Password123"
        }
        res_login = client.post("/login", json=login_payload)
        self.assertEqual(res_login.status_code, 200)
        token = res_login.json()["access_token"]
        self.assertTrue(len(token) > 20)

    def test_03_home_budget_planner(self):
        """Test home interior recommendation generation and links"""
        # Login demo user
        res_login = client.post("/login", json={"username": "demo", "password": "demo123"})
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "total_budget": 60000,
            "num_lights": 6,
            "num_fans": 3,
            "num_furniture": 2,
            "num_dining_tables": 1,
            "has_living_room": True,
            "has_kitchen": True,
            "has_bedroom": True,
            "additional_requirements": "Warm contemporary wooden aesthetic"
        }

        res = client.post("/home-budget", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_budget", data)
        self.assertIn("budget_breakdown", data)
        self.assertIn("calculation_table", data)
        self.assertIn("remaining_budget", data)

        # Check shopping links
        for cat in data["budget_breakdown"]:
            for item in cat["items"]:
                self.assertIn("shopping_links", item)
                self.assertIn("amazon", item["shopping_links"])
                self.assertIn("flipkart", item["shopping_links"])

    def test_04_party_budget_planner(self):
        """Test party planning recommendations and category links"""
        res_login = client.post("/login", json={"username": "demo", "password": "demo123"})
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "total_budget": 25000,
            "num_guests": 20,
            "party_type": "Birthday",
            "venue_type": "Banquet Hall",
            "needs_catering": True,
            "needs_decoration": True,
            "needs_entertainment": True,
            "additional_requirements": "Vegetarian buffet and retro balloon theme"
        }

        res = client.post("/party-budget", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_budget", data)
        self.assertIn("budget_breakdown", data)
        self.assertIn("calculation_table_inr", data)

    def test_05_jewelry_budget_planner(self):
        """Test jewelry recommendation generation"""
        res_login = client.post("/login", json={"username": "demo", "password": "demo123"})
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        form_data = {
            "total_budget": "15000",
            "occasion": "Wedding Reception",
            "preferences": "Rose gold minimal design with zirconia"
        }

        res = client.post("/jewelry-budget", data=form_data, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("jewelry_recommendations", data)
        self.assertIn("styling_tips", data)
        for item in data["jewelry_recommendations"]:
            self.assertIn("shopping_links", item)
            self.assertIn("tanishq", item["shopping_links"])

    def test_06_history_api(self):
        """Test history retrieval endpoint"""
        res_login = client.post("/login", json={"username": "demo", "password": "demo123"})
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = client.get("/recommendation-history", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("history", data)
        self.assertTrue(len(data["history"]) >= 1)

if __name__ == "__main__":
    unittest.main()
