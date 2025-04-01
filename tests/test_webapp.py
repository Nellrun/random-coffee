import pytest
from fastapi.testclient import TestClient
import os
from dotenv import load_dotenv

# Load environment variables for testing
load_dotenv(".env.test", override=True)

from app.webapp.main import app

# Create test client
client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint returns the main page"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Random Coffee" in response.text
    assert "Connect with interesting people" in response.text

def test_profile_edit_endpoint():
    """Test the profile edit endpoint returns the edit page"""
    response = client.get("/profile/edit")
    assert response.status_code == 200
    assert "Edit Profile" in response.text
    assert "Tell us about yourself" in response.text

def test_profile_view_endpoint():
    """Test the profile view endpoint returns the view page"""
    # This test will fail if the user_id doesn't exist in the database
    # For testing purposes, we're just checking the page loads
    response = client.get("/profile/1")
    assert response.status_code == 200
    assert "Profile" in response.text

def test_api_user_profile_endpoint():
    """Test the API endpoint for user profiles"""
    # This test will fail if the user_id doesn't exist in the database
    # In a real test, we would mock the database response
    response = client.get("/api/user/profile/1")
    
    # We expect either a 200 OK with user data or a 404 Not Found
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        data = response.json()
        assert "id" in data
        assert "full_name" in data
        assert "interests" in data
    else:
        assert "detail" in response.json()
        assert "not found" in response.json()["detail"].lower()

def test_webapp_data_endpoint_invalid_data():
    """Test the webapp data endpoint with invalid data"""
    response = client.post(
        "/api/webapp/data",
        json={"action": "invalid_action"}
    )
    assert response.status_code == 400
    assert "Invalid action" in response.json()["detail"]

def test_static_files():
    """Test that static files are served correctly"""
    response = client.get("/static/css/styles.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]