import pytest
import os
from unittest.mock import MagicMock
from backend import config


class TestKeyVaultSecretFallback:
    """Test suite for Azure Key Vault secret retrieval and graceful fallbacks."""

    def setup_method(self):
        """Clear cache and reset vault client before each test."""
        config._secret_cache.clear()
        config._vault_client = None

    def test_keyvault_retrieval_success(self, monkeypatch):
        """Test successful secret retrieval from Azure Key Vault."""
        mock_client = MagicMock()
        mock_secret = MagicMock()
        mock_secret.value = "kv-secret-value-12345"
        mock_client.get_secret.return_value = mock_secret

        monkeypatch.setattr(config, "get_key_vault_client", lambda: mock_client)

        secret = config.get_secret("TEST_SECRET_KEY")
        assert secret == "kv-secret-value-12345"
        mock_client.get_secret.assert_called_once_with("TEST-SECRET-KEY")
        assert config._secret_cache["TEST_SECRET_KEY"] == "kv-secret-value-12345"

    def test_keyvault_fallback_to_environment_variable(self, monkeypatch):
        """Test fallback to os.environ when Key Vault client raises an error or is unavailable."""
        mock_client = MagicMock()
        mock_client.get_secret.side_effect = Exception("Key Vault access denied or secret not found")

        monkeypatch.setattr(config, "get_key_vault_client", lambda: mock_client)
        monkeypatch.setenv("FALLBACK_ENV_SECRET", "env-secret-value-999")

        secret = config.get_secret("FALLBACK_ENV_SECRET")
        assert secret == "env-secret-value-999"
        assert config._secret_cache["FALLBACK_ENV_SECRET"] == "env-secret-value-999"

    def test_keyvault_fallback_to_default_value(self, monkeypatch):
        """Test fallback to provided default value when neither Key Vault nor environment var is present."""
        monkeypatch.setattr(config, "get_key_vault_client", lambda: None)
        if "NON_EXISTENT_KEY" in os.environ:
            monkeypatch.delenv("NON_EXISTENT_KEY")

        secret = config.get_secret("NON_EXISTENT_KEY", default="default-hardcoded-value")
        assert secret == "default-hardcoded-value"

    def test_underscore_to_hyphen_name_conversion(self, monkeypatch):
        """Test secret name conversion from underscore to hyphen format for Key Vault compatibility."""
        mock_client = MagicMock()
        mock_secret = MagicMock()
        mock_secret.value = "secret-val"
        mock_client.get_secret.return_value = mock_secret

        monkeypatch.setattr(config, "get_key_vault_client", lambda: mock_client)

        config.get_secret("AZURE_OPENAI_API_KEY")
        mock_client.get_secret.assert_called_once_with("AZURE-OPENAI-API-KEY")

    def test_secret_caching(self, monkeypatch):
        """Test cached secret is returned without re-querying Key Vault."""
        mock_client = MagicMock()
        mock_secret = MagicMock()
        mock_secret.value = "cached-secret"
        mock_client.get_secret.return_value = mock_secret

        monkeypatch.setattr(config, "get_key_vault_client", lambda: mock_client)

        # First call hits Key Vault
        val1 = config.get_secret("CACHED_KEY")
        assert val1 == "cached-secret"
        assert mock_client.get_secret.call_count == 1

        # Second call returns from cache
        val2 = config.get_secret("CACHED_KEY")
        assert val2 == "cached-secret"
        assert mock_client.get_secret.call_count == 1
