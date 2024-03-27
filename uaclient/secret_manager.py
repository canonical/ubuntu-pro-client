from typing import List


class SecretManager:
    def __init__(self):
        self._secrets = []

    def add_secret(self, secret: str) -> None:
        if secret:  # Add only non-empty secrets
            self._secrets.append(secret)

    @property
    def secrets(self) -> List[str]:
        return self._secrets

    def clear_secrets(self) -> None:
        self._secrets.clear()

    def redact_secrets(self, log_record: str) -> str:
        redacted_record = log_record
        for secret in self._secrets:
            redacted_record = redacted_record.replace(secret, "<REDACTED>")
        return redacted_record


secrets = SecretManager()
