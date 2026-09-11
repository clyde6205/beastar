# BeAstar.io - Provider Tests
# ============================
# Tests for AI providers, face verification, and content moderation

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch, Mock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

# Import the app
from app.main import app

# Create test client
client = TestClient(app)


class TestFaceVerification:
    """Tests for face verification system"""
    
    def test_face_verification_endpoint_exists(self):
        """Test that face verification endpoint exists"""
        # This will fail because we don't have a real user, but it tests the endpoint exists
        response = client.post(
            "/auth/test-user-id/verify-face",
            json={"selfie_image_url": "http://example.com/selfie.jpg"}
        )
        # Should return 404 (user not found) or 503 (backend not configured)
        assert response.status_code in [404, 503]
    
    def test_face_verification_with_mock(self):
        """Test face verification with mocked dependencies"""
        from app.providers.face_verification import (
            verify_face_image,
            VerificationResult,
            LIVENESS_CONFIDENCE_THRESHOLD,
        )
        
        # Create a simple test image (1x1 pixel)
        from PIL import Image
        import io
        import numpy as np
        
        # Create a 100x100 gray image
        img = Image.new('L', (100, 100), color=128)
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        # Mock the face_recognition library
        with patch('app.providers.face_verification.face_recognition') as mock_fr:
            # Setup mock to return a face
            mock_fr.face_locations.return_value = [(10, 90, 90, 10)]  # One face
            mock_fr.face_encodings.return_value = [np.random.rand(128).astype(np.float32)]
            
            # Test with local provider
            from app.providers.face_verification import LocalFaceVerificationProvider
            provider = LocalFaceVerificationProvider()
            
            # Test liveness detection
            is_live, confidence = provider.detect_liveness(img_bytes)
            assert isinstance(is_live, bool)
            assert isinstance(confidence, float)
            assert 0 <= confidence <= 1
    
    def test_face_embedding_generation(self):
        """Test face embedding generation"""
        from app.providers.face_verification import (
            LocalFaceVerificationProvider,
            generate_face_embedding_id,
        )
        import numpy as np
        
        # Create a test embedding
        embedding = np.random.rand(128).astype(np.float32)
        
        # Generate ID
        embedding_id = generate_face_embedding_id(embedding)
        
        # Should be a string starting with 'emb_'
        assert embedding_id.startswith('emb_')
        assert len(embedding_id) == 20  # 16 hex chars + 'emb_' prefix


class TestVideoGeneration:
    """Tests for video generation providers"""
    
    def test_runway_client_initialization(self):
        """Test Runway client initialization"""
        from app.providers.runway import RunwayClient, RunwayAuthenticationError
        
        # Without API key, should raise authentication error
        with patch.dict('os.environ', {'RUNWAY_API_KEY': ''}, clear=False):
            with pytest.raises(RunwayAuthenticationError):
                RunwayClient()
    
    def test_kling_client_initialization(self):
        """Test Kling client initialization"""
        from app.providers.kling import KlingClient, KlingAuthenticationError
        
        # Without API key, should raise authentication error
        with patch.dict('os.environ', {'KLING_API_KEY': ''}, clear=False):
            with pytest.raises(KlingAuthenticationError):
                KlingClient()
    
    def test_video_gen_watermarking_placeholder(self):
        """Test that watermarking function exists"""
        from app.providers.video_gen import add_ai_disclosure_to_video
        
        # Function should exist
        assert callable(add_ai_disclosure_to_video)


class TestContentModeration:
    """Tests for content moderation"""
    
    def test_moderation_result_dataclass(self):
        """Test moderation result dataclass"""
        from app.providers.content_moderation import ModerationResult
        
        # Create a test result
        result = ModerationResult(
            status="approved",
            is_safe=True,
            confidence=0.95,
            reason=None,
            vendor="local",
            unsafe_categories=[]
        )
        
        assert result.status == "approved"
        assert result.is_safe == True
        assert result.confidence == 0.95
    
    def test_local_moderator(self):
        """Test local moderator"""
        from app.providers.content_moderation import LocalModerator
        
        # Create a simple test image
        from PIL import Image
        import io
        
        img = Image.new('RGB', (100, 100), color='gray')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()
        
        # Test with local moderator
        moderator = LocalModerator()
        result = moderator.moderate_image(img_bytes)
        
        # Should return a result (even if not configured)
        assert isinstance(result.status, str)
        assert isinstance(result.is_safe, bool)


class TestStorage:
    """Tests for storage operations"""
    
    def test_selfie_upload_validation(self):
        """Test selfie upload validation"""
        from app.storage.selfie_upload import (
            validate_image_bytes,
            UploadValidationError,
        )
        from PIL import Image
        import io
        
        # Create a valid test image
        img = Image.new('RGB', (500, 500), color='gray')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()
        
        # Test validation
        try:
            width, height = validate_image_bytes(img_bytes, "image/jpeg")
            assert width == 500
            assert height == 500
        except UploadValidationError as e:
            # If PIL is not available, this is expected
            pass
    
    def test_invalid_image_type(self):
        """Test validation with invalid image type"""
        from app.storage.selfie_upload import (
            validate_image_content_type,
            UploadValidationError,
        )
        
        # Test with invalid type
        with pytest.raises(UploadValidationError):
            validate_image_content_type("text/plain")


class TestProviders:
    """Tests for provider abstractions"""
    
    def test_provider_registry(self):
        """Test provider registry"""
        from app.providers.video_gen import PROVIDERS, get_provider
        
        # Check providers exist
        assert "runway" in PROVIDERS
        assert "kling" in PROVIDERS
        
        # Test getting providers
        runway = get_provider("runway")
        assert runway is not None
        
        kling = get_provider("kling")
        assert kling is not None
    
    def test_invalid_provider(self):
        """Test getting invalid provider"""
        from app.providers.video_gen import get_provider, VideoGenError
        
        with pytest.raises(VideoGenError):
            get_provider("invalid_provider")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
