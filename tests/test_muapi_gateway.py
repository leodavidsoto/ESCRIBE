"""
Tests for Muapi unified provider gateway.
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from providers.muapi_gateway import MuapiGateway, GenerationResult


@pytest.fixture
def gateway():
    """Fixture for MuapiGateway."""
    with patch.dict("os.environ", {"MUAPI_KEY": "test_key"}):
        return MuapiGateway(api_key="test_key")


class TestGenerationResult:
    """Test suite for GenerationResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful result."""
        result = GenerationResult(
            success=True,
            output_path=Path("/tmp/image.png"),
            model="flux-pro",
        )
        assert result.success is True
        assert result.output_path == Path("/tmp/image.png")
        assert result.error is None
        assert result.model == "flux-pro"
        assert isinstance(result.metadata, dict)

    def test_error_result(self):
        """Test creating an error result."""
        result = GenerationResult(
            success=False,
            error="API timeout",
        )
        assert result.success is False
        assert result.error == "API timeout"
        assert result.output_path is None


class TestMuapiGatewayInit:
    """Test suite for MuapiGateway initialization."""

    def test_initialization_with_api_key(self):
        """Test initialization with explicit API key."""
        gateway = MuapiGateway(api_key="test_key")
        assert gateway.api_key == "test_key"
        assert "api.muapi.ai" in gateway.base_url

    def test_initialization_default_base_url(self):
        """Test initialization uses default base URL."""
        gateway = MuapiGateway(api_key="test_key")
        assert gateway.base_url == "https://api.muapi.ai/v1"

    def test_initialization_custom_base_url(self):
        """Test initialization with custom base URL."""
        gateway = MuapiGateway(
            api_key="test_key",
            base_url="https://custom.api.com"
        )
        assert gateway.base_url == "https://custom.api.com"

    def test_model_registrations(self):
        """Test model registrations are loaded."""
        gateway = MuapiGateway(api_key="test_key")
        assert len(gateway.TEXT_TO_IMAGE) > 0
        assert len(gateway.IMAGE_TO_IMAGE) > 0
        assert len(gateway.TEXT_TO_VIDEO) > 0
        assert len(gateway.IMAGE_TO_VIDEO) > 0


class TestMuapiGatewayImageGeneration:
    """Test suite for image generation."""

    @pytest.mark.asyncio
    async def test_generate_image_t2i_mode(self, gateway):
        """Test text-to-image generation."""
        with patch.object(gateway, "_invoke_t2i", new_callable=AsyncMock) as mock_t2i:
            mock_t2i.return_value = GenerationResult(
                success=True,
                output_path=Path("/tmp/image.png"),
                model="flux-pro",
            )

            result = await gateway.generate_image(
                prompt="A beautiful landscape",
                model="flux-pro",
            )

            assert result.success is True
            assert result.output_path == Path("/tmp/image.png")
            mock_t2i.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_image_i2i_mode(self, gateway, tmp_path):
        """Test image-to-image generation."""
        input_image = tmp_path / "input.png"
        input_image.write_text("fake image")

        with patch.object(gateway, "_invoke_i2i", new_callable=AsyncMock) as mock_i2i:
            mock_i2i.return_value = GenerationResult(
                success=True,
                output_path=Path("/tmp/image_i2i.png"),
                model="flux-pro-i2i",
            )

            result = await gateway.generate_image(
                prompt="Transform this",
                image_input=input_image,
            )

            assert result.success is True
            mock_i2i.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_image_missing_input(self, gateway):
        """Test image-to-image with missing input."""
        result = await gateway.generate_image(
            prompt="Transform this",
            image_input=Path("/nonexistent/image.png"),
        )

        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_generate_image_exception_handling(self, gateway):
        """Test exception handling in image generation."""
        with patch.object(gateway, "_invoke_t2i", side_effect=Exception("API error")):
            result = await gateway.generate_image(
                prompt="Test prompt",
            )

            assert result.success is False
            assert "API error" in result.error


class TestMuapiGatewayVideoGeneration:
    """Test suite for video generation."""

    @pytest.mark.asyncio
    async def test_generate_video_t2v_mode(self, gateway):
        """Test text-to-video generation."""
        with patch.object(gateway, "_invoke_t2v", new_callable=AsyncMock) as mock_t2v:
            mock_t2v.return_value = GenerationResult(
                success=True,
                output_path=Path("/tmp/video.mp4"),
                model="sora",
            )

            result = await gateway.generate_video(
                prompt="A cinematic landscape",
                model="sora",
                duration=5.0,
            )

            assert result.success is True
            assert result.output_path == Path("/tmp/video.mp4")
            mock_t2v.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_video_i2v_mode(self, gateway, tmp_path):
        """Test image-to-video generation."""
        input_image = tmp_path / "input.png"
        input_image.write_text("fake image")

        with patch.object(gateway, "_invoke_i2v", new_callable=AsyncMock) as mock_i2v:
            mock_i2v.return_value = GenerationResult(
                success=True,
                output_path=Path("/tmp/video_i2v.mp4"),
                model="runway-i2v",
            )

            result = await gateway.generate_video(
                image_input=input_image,
                model="runway-i2v",
            )

            assert result.success is True
            mock_i2v.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_video_t2v_missing_prompt(self, gateway):
        """Test text-to-video without prompt."""
        result = await gateway.generate_video(
            model="sora",
        )

        assert result.success is False
        assert "prompt required" in result.error

    @pytest.mark.asyncio
    async def test_generate_video_exception_handling(self, gateway):
        """Test exception handling in video generation."""
        with patch.object(gateway, "_invoke_t2v", side_effect=Exception("API error")):
            result = await gateway.generate_video(
                prompt="Test prompt",
            )

            assert result.success is False
            assert "API error" in result.error


class TestMuapiGatewayModelSelection:
    """Test suite for model selection."""

    def test_text_to_image_models(self):
        """Test T2I model availability."""
        gateway = MuapiGateway(api_key="test_key")
        assert "flux-pro" in gateway.TEXT_TO_IMAGE
        assert "dall-e-3" in gateway.TEXT_TO_IMAGE
        assert "midjourney" in gateway.TEXT_TO_IMAGE

    def test_text_to_video_models(self):
        """Test T2V model availability."""
        gateway = MuapiGateway(api_key="test_key")
        assert "sora" in gateway.TEXT_TO_VIDEO
        assert "kling" in gateway.TEXT_TO_VIDEO
        assert "veo" in gateway.TEXT_TO_VIDEO
        assert "runway-gen3" in gateway.TEXT_TO_VIDEO

    def test_image_to_video_models(self):
        """Test I2V model availability."""
        gateway = MuapiGateway(api_key="test_key")
        assert "runway-i2v" in gateway.IMAGE_TO_VIDEO
        assert "veo-i2v" in gateway.IMAGE_TO_VIDEO
        assert "kling-i2v" in gateway.IMAGE_TO_VIDEO
        assert "luma-dream" in gateway.IMAGE_TO_VIDEO


class TestMuapiGatewayJobPolling:
    """Test suite for job polling."""

    @pytest.mark.asyncio
    async def test_poll_job_completion(self, gateway):
        """Test job polling on successful completion."""
        with patch.object(gateway.client, "get", new_callable=AsyncMock) as mock_get:
            # Mock completed job
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "completed",
                "output_url": "https://example.com/video.mp4",
            }
            mock_get.return_value = mock_response

            result = await gateway._poll_job("test_job_id", "sora", timeout=30)
            assert result is not None
            assert "test_job_id" in str(result)

    @pytest.mark.asyncio
    async def test_poll_job_failure(self, gateway):
        """Test job polling on failure."""
        with patch.object(gateway.client, "get", new_callable=AsyncMock) as mock_get:
            # Mock failed job
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "failed",
                "error": "Out of memory",
            }
            mock_get.return_value = mock_response

            result = await gateway._poll_job("test_job_id", "sora", timeout=30)
            assert result is None

    @pytest.mark.asyncio
    async def test_poll_job_timeout(self, gateway):
        """Test job polling timeout."""
        with patch.object(gateway.client, "get", new_callable=AsyncMock) as mock_get:
            # Mock pending job (never completes)
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "pending",
            }
            mock_get.return_value = mock_response

            result = await gateway._poll_job("test_job_id", "sora", timeout=0.1)
            assert result is None


class TestMuapiGatewayAsyncContext:
    """Test suite for async context management."""

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing the HTTP client."""
        gateway = MuapiGateway(api_key="test_key")
        with patch.object(gateway.client, "aclose", new_callable=AsyncMock) as mock_close:
            await gateway.close()
            mock_close.assert_called_once()
