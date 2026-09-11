# BeAstar.io - Backend Tests
# ==============================
# Test configuration and fixtures

import os
import sys
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment variables for testing
os.environ.update({
    "USE_REAL_BACKEND": "false",
    "SUPABASE_URL": "http://localhost:54321",
    "SUPABASE_KEY": "test-key",
    "REDIS_URL": "redis://localhost:6379/0",
    "RUNWAY_API_KEY": "test-runway-key",
    "KLING_API_KEY": "test-kling-key",
    "AWS_REGION": "us-east-1",
    "AWS_ACCESS_KEY_ID": "test-aws-key",
    "AWS_SECRET_ACCESS_KEY": "test-aws-secret",
    "STRIPE_WEBHOOK_SECRET": "test-stripe-secret",
    "PAYMONGO_SECRET_KEY": "test-paymongo-key",
    "PAYMONGO_WEBHOOK_SECRET": "test-paymongo-webhook-secret",
    "APP_BASE_URL": "http://localhost:8000",
})

# Create mock Supabase client for testing
def get_mock_supabase():
    """Get a mock Supabase client for testing"""
    mock = MagicMock()
    
    # Mock tables
    mock.users = MagicMock()
    mock.generation_jobs = MagicMock()
    mock.scenarios = MagicMock()
    mock.subscriptions = MagicMock()
    mock.dream_threads = MagicMock()
    mock.dream_updates = MagicMock()
    mock.challenges = MagicMock()
    mock.referrals = MagicMock()
    
    # Mock storage
    mock.storage = MagicMock()
    mock.storage.from_ = MagicMock()
    
    return mock

# Fixtures
class TestFixtures:
    """Test fixtures for BeAstar"""
    
    @staticmethod
    def get_test_user():
        """Get a test user object"""
        return {
            "id": "test-user-id",
            "email": "test@example.com",
            "display_name": "Test User",
            "date_of_birth": "2000-01-01",
            "country_code": "US",
            "referral_code": "TEST123",
            "referred_by_user_id": None,
            "face_embedding_id": "test-embedding-id",
            "is_verified": True,
            "credits": 100,
            "created_at": "2024-01-01T00:00:00Z",
        }
    
    @staticmethod
    def get_test_job():
        """Get a test generation job object"""
        return {
            "id": "test-job-id",
            "user_id": "test-user-id",
            "scenario_id": "test-scenario-id",
            "resolution": "720p",
            "status": "queued",
            "provider": None,
            "provider_job_id": None,
            "output_url": None,
            "render_cost_usd": None,
            "credits_charged": 1,
            "created_at": "2024-01-01T00:00:00Z",
            "completed_at": None,
        }
    
    @staticmethod
    def get_test_scenario():
        """Get a test scenario object"""
        return {
            "id": "test-scenario-id",
            "slug": "red-carpet-arrival",
            "name": "Red Carpet Arrival",
            "description": "Walk the red carpet as a star",
            "is_premium": False,
            "is_active": True,
        }

# Export fixtures
fixtures = TestFixtures()
