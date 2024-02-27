import re


class SecretManager:
    def __init__(self):
        self._secrets = []

    def add_secret(self, secret: str) -> None:
        self._secrets.append(secret)

    @property
    def secrets(self) -> list[str]:
        return self._secrets

    def clear_secrets(self) -> None:
        self._secrets.clear()

    def redact_secrets(self, log_record: str) -> str:
        redacted_record = log_record
        for secret in self._secrets:
            redacted_record = re.sub(
                f"({re.escape(secret)})", "<REDACTED>", redacted_record
            )
        return redacted_record


secrets = SecretManager()
