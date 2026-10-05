from typing import Dict, Any
from .circuit_breaker import CircuitBreaker, CircuitState


class ResilienceRegistry:
    """
    Central registry for managing Circuit Breakers across external integrations:
    - Azure OpenAI
    - Azure AI Search
    - Microsoft Graph API
    - Microsoft Teams Webhook
    - Azure Cosmos DB
    """

    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {
            "azure_openai": CircuitBreaker(
                name="azure_openai",
                failure_threshold=3,
                recovery_timeout=15.0,
                half_open_max_calls=2,
            ),
            "azure_search": CircuitBreaker(
                name="azure_search",
                failure_threshold=3,
                recovery_timeout=15.0,
                half_open_max_calls=2,
            ),
            "graph_api": CircuitBreaker(
                name="graph_api",
                failure_threshold=3,
                recovery_timeout=20.0,
                half_open_max_calls=2,
            ),
            "teams_webhook": CircuitBreaker(
                name="teams_webhook",
                failure_threshold=3,
                recovery_timeout=20.0,
                half_open_max_calls=2,
            ),
            "cosmos_db": CircuitBreaker(
                name="cosmos_db",
                failure_threshold=4,
                recovery_timeout=15.0,
                half_open_max_calls=2,
            ),
        }

    def get_breaker(self, service_name: str) -> CircuitBreaker:
        """Retrieves or creates a named Circuit Breaker."""
        if service_name not in self.breakers:
            self.breakers[service_name] = CircuitBreaker(name=service_name)
        return self.breakers[service_name]

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Returns status map of all registered circuit breakers for health probes."""
        return {name: breaker.get_status() for name, breaker in self.breakers.items()}

    def reset_all(self) -> None:
        """Resets all registered circuit breakers to CLOSED."""
        for breaker in self.breakers.values():
            breaker.reset()


# Global singleton registry instance
resilience_registry = ResilienceRegistry()
