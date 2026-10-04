import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("orbit.config")

# Azure Key Vault Configuration
AZURE_KEY_VAULT_NAME = os.getenv("AZURE_KEY_VAULT_NAME", "orbit-vault-3207")
AZURE_KEY_VAULT_URI = os.getenv("AZURE_KEY_VAULT_URI", f"https://{AZURE_KEY_VAULT_NAME}.vault.azure.net/")

_vault_client = None
_secret_cache = {}

def get_key_vault_client():
    """Initializes Azure Key Vault SecretClient using DefaultAzureCredential with graceful fallback."""
    global _vault_client
    if _vault_client is None:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            credential = DefaultAzureCredential()
            _vault_client = SecretClient(vault_url=AZURE_KEY_VAULT_URI, credential=credential)
            logger.info("Azure Key Vault SecretClient initialized for %s", AZURE_KEY_VAULT_URI)
        except Exception as e:
            logger.warning("Azure Key Vault SecretClient initialization skipped: %s", e)
            _vault_client = False
    return _vault_client if _vault_client is not False else None

def get_secret(secret_name: str, default: str = None) -> str:
    """
    Fetches secret from Azure Key Vault first; falls back to environment variable, then default.
    Converts underscore names to hyphens (e.g., AZURE_OPENAI_KEY -> AZURE-OPENAI-KEY).
    """
    if secret_name in _secret_cache:
        return _secret_cache[secret_name]

    # 1. Try Azure Key Vault if configured
    client = get_key_vault_client()
    if client:
        kv_name = secret_name.replace("_", "-")
        try:
            val = client.get_secret(kv_name).value
            if val:
                _secret_cache[secret_name] = val
                return val
        except Exception as err:
            logger.debug("Key Vault secret lookup for '%s' bypassed: %s", kv_name, err)

    # 2. Fall back to local environment variable
    env_val = os.getenv(secret_name)
    if env_val:
        _secret_cache[secret_name] = env_val
        return env_val

    # 3. Fall back to default
    if default is not None:
        return default

    return ""

# Core Services & Credentials (resolved via Azure Key Vault / Environment)
AZURE_OPENAI_ENDPOINT = get_secret("AZURE_OPENAI_ENDPOINT", "https://mailmind-openai-3207.openai.azure.com/")
AZURE_OPENAI_KEY = get_secret("AZURE_OPENAI_KEY", "")
AZURE_OPENAI_DEPLOYMENT = get_secret("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

AZURE_SEARCH_ENDPOINT = get_secret("AZURE_SEARCH_ENDPOINT", "https://mailmind-search-3207.search.windows.net")
AZURE_SEARCH_KEY = get_secret("AZURE_SEARCH_KEY", "")

AZURE_COSMOS_ENDPOINT = get_secret("AZURE_COSMOS_ENDPOINT", "https://mailmind-cosmos-3209.documents.azure.com:443/")
AZURE_COSMOS_KEY = get_secret("AZURE_COSMOS_KEY", "")
COSMOS_DATABASE = get_secret("COSMOS_DATABASE", "mailminddb")

GRAPH_CLIENT_ID = get_secret("GRAPH_CLIENT_ID", "")
GRAPH_CLIENT_SECRET = get_secret("GRAPH_CLIENT_SECRET", "")
GRAPH_TENANT_ID = get_secret("GRAPH_TENANT_ID", "")

TEAMS_WEBHOOK_URL = get_secret("TEAMS_WEBHOOK_URL", "https://societegenerale.webhook.office.com/webhookb2/mock-approval")

RISK_THRESHOLD = float(get_secret("RISK_THRESHOLD", "0.7"))

