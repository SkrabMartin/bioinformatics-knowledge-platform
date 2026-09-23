class IntegrationError(RuntimeError):
    """A safe, provider-facing error suitable for CLI reporting."""

    code = "upstream_error"

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        self.message = message
        super().__init__(message)


class IntegrationConfigurationError(IntegrationError):
    code = "integration_configuration_error"


class UpstreamNotFoundError(IntegrationError):
    code = "upstream_record_not_found"


class UpstreamRateLimitError(IntegrationError):
    code = "upstream_rate_limited"


class UpstreamResponseError(IntegrationError):
    code = "upstream_response_error"


class UpstreamUnavailableError(IntegrationError):
    code = "upstream_unavailable"
