# BeAstar.io - API Tests
# =====================
# Tests for FastAPI endpoints

import os
import sys
from datetime import date

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the app
from app.main import app

# Create test client
client = TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint"""
    
    def test_health_endpoint(self):
        """Test that health endpoint returns success"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "backend_configured" in data


class TestSignupEndpoint:
    """Tests for user signup endpoint"""
    
    def test_signup_without_backend(self):
        """Test signup when backend is not configured"""
        # This should fail with 503
        response = client.post(
            "/auth/signup",
            json={
                "email": "test@example.com",
                "display_name": "Test User",
                "date_of_birth": "2000-01-01",
                "country_code": "US",
            }
        )
        # Without backend configured, should return 503
        assert response.status_code == 503
    
    def test_signup_validation_age(self):
        """Test signup with underage user"""
        from datetime import date, datetime
        
        # Mock the backend to avoid 503
        with patch('app.main.get_supabase') as mock_get_supabase:
            mock_db = MagicMock()
            mock_get_supabase.return_value = mock_db
            
            # Test with underage user (12 years old)
            underage_dob = date.today().replace(
                year=date.today().year - 12
            )
            
            response = client.post(
                "/auth/signup",
                json={
                    "email": "underage@example.com",
                    "display_name": "Underage User",
                    "date_of_birth": underage_dob.isoformat(),
                    "country_code": "US",
                }
            )
            
            # Should fail with age validation
            assert response.status_code == 400
            assert "13 years old" in response.json()["detail"]
    
    def test_signup_validation_email(self):
        """Test signup with invalid email"""
        with patch('app.main.get_supabase') as mock_get_supabase:
            mock_db = MagicMock()
            mock_get_supabase.return_value = mock_db
            
            response = client.post(
                "/auth/signup",
                json={
                    "email": "invalid-email",
                    "display_name": "Test User",
                    "date_of_birth": "2000-01-01",
                    "country_code": "US",
                }
            )
            
            # Should fail with validation error
            assert response.status_code == 422


class TestGenerationEndpoint:
    """Tests for video generation endpoint"""
    
    def test_generation_without_authentication(self):
        """Test generation without user authentication"""
        with patch('app.main.get_supabase') as mock_get_supabase:
            mock_db = MagicMock()
            mock_get_supabase.return_value = mock_db
            
            response = client.post(
                "/generate",
                json={
                    "user_id": "non-existent-user",
                    "scenario_slug": "red-carpet-arrival",
                    "requested_resolution": "720p",
                    "image_url": "http://example.com/selfie.jpg",
                }
            )
            
            # Should fail with 404 (user not found)
            assert response.status_code == 404
    
    def test_generation_without_verification(self):
        """Test generation with unverified user"""
        with patch('app.main.get_supabase') as mock_get_supabase:
            mock_db = MagicMock()
            
            # Mock user as unverified
            mock_user = {
                "id": "test-user-id",
                "email": "test@example.com",
                "is_verified": False,
                "credits": 100,
            }
            
            mock_db.get_user.return_value = mock_user
            mock_db.get_user_tier.return_value = "free"
            mock_db.get_scenario_by_slug.return_value = {
                "id": "test-scenario-id",
                "slug": "red-carpet-arrival",
                "is_active": True,
            }
            
            mock_get_supabase.return_value = mock_db
            
            response = client.post(
                "/generate",
                json={
                    "user_id": "test-user-id",
                    "scenario_slug": "red-carpet-arrival",
                    "requested_resolution": "720p",
                    "image_url": "http://example.com/selfie.jpg",
                }
            )
            
            # Should fail with 403 (verification required)
            assert response.status_code == 403
            assert "Face verification required" in response.json()["detail"]


class TestLeaderboardEndpoint:
    """Tests for leaderboard endpoint"""
    
    def test_leaderboard_endpoint(self):
        """Test leaderboard endpoint"""
        with patch('app.main.get_supabase') as mock_get_supabase:
            mock_db = MagicMock()
            mock_db.get_leaderboard.return_value = [
                {
                    "user_id": "user-1",
                    "display_name": "Top User",
                    "country_code": "US",
                    "videos_created": 10,
                    "successful_referrals": 5,
                }
            ]
            mock_get_supabase.return_value = mock_db
            
            response = client.get("/leaderboard")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0


class TestQRCodeEndpoint:
    """Tests for QR code endpoint"""
    
    def test_qr_code_endpoint(self):
        """Test QR code generation endpoint"""
        with patch('app.main.get_supabase') as mock_get_supabase:
            mock_db = MagicMock()
            mock_user = {
                "id": "test-user-id",
                "referral_code": "TEST123",
            }
            mock_db.get_user.return_value = mock_user
            mock_get_supabase.return_value = mock_db
            
            response = client.get("/qr/test-user-id")
            
            # Should return PNG image
            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"


class TestChallengesEndpoint:
    """Tests for challenges endpoints"""
    
    def test_list_challenges(self):
        """Test listing active challenges"""
        with patch('app.main.get_supabase') as mock_get_supabase:
            mock_db = MagicMock()
            mock_db.list_active_challenges.return_value = [
                {
                    "id": "challenge-1",
                    "hashtag": "#StarMe",
                    "title": "Become a Star",
                    "scope": "global",
                    "starts_at": "2024-01-01T00:00:00Z",
                    "ends_at": "2024-12-31T23:59:59Z",
                }
            ]
            mock_get_supabase.return_value = mock_db
            
            response = client.get("/challenges")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


class TestDreamThreadsEndpoint:
    """Tests for dream threads endpoints"""
    
    def test_create_dream_thread(self):
        """Test creating a dream thread"""
        with patch('app.main.get_supabase') as mock_get_supabase:
            mock_db = MagicMock()
            mock_user = {
                "id": "test-user-id",
                "email": "test@example.com",
            }
            mock_db.get_user.return_value = mock_user
            mock_db.create_dream_thread.return_value = {
                "id": "thread-1",
                "user_id": "test-user-id",
                "goal_title": "My Dream",
                "goal_description": "Become a star",
                "created_at": "2024-01-01T00:00:00Z",
            }
            mock_get_supabase.return_value = mock_db
            
            response = client.post(
                "/dream-threads",
                json={
                    "user_id": "test-user-id",
                    "goal_title": "My Dream",
                    "goal_description": "Become a star",
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["goal_title"] == "My Dream"
            assert "display_note" in data


class TestFollowState:
    """Tests for follow state endpoint"""
    
    def test_check_follow_endpoint_missing(self):
        """Test that follow check endpoint exists (to be added)"""
        # This endpoint should be added to check if user follows a thread
        response = client.get("/users/test-user-id/follows/test-thread-id")
        # Currently returns 404 (not implemented)
        assert response.status_code == 404


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
