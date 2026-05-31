# Encryption Services

Exception classes and encryption modules used across the codebase.

## Exception Classes

### `EncryptionError` (`app/services/encryption.py:16-19`)

Raised when AES-256-GCM encryption or decryption fails for TOTP secret protection.

```python
class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""
    pass
```

**Used by:** `app/services/encryption.py` functions (`encrypt_secret()`, `decrypt_secret()`) when the encryption key cannot be loaded from `SECRET_KEY` config or crypto operations fail.

### `WebhookEncryptionError` (`app/webhook_encryption.py:16-19`)

Raised when AES-256-GCM encryption or decryption fails for webhook secret protection.

```python
class WebhookEncryptionError(Exception):
    """Raised when encryption or decryption fails."""
    pass
```

**Used by:** `app/webhook_encryption.py` functions (`encrypt_webhook_secret()`, `decrypt_webhook_secret()`) when `WEBHOOK_ENCRYPTION_KEY` is not configured, is invalid length, or crypto operations fail.

### `ConfigurationError` (`app/services/search/__init__.py:7-10`)

Raised when the search provider is misconfigured.

```python
class ConfigurationError(Exception):
    """Raised when search provider is misconfigured."""
    pass
```

**Used by:** Search provider factory when `SEARCH_PROVIDER` config references a non-existent provider class or required configuration is missing.

## Encryption Modules

| Module | Purpose | Key Source | Cipher |
|--------|---------|------------|--------|
| `app/backup_encryption.py` | Backup file encryption | `BACKUP_ENCRYPTION_KEY` env var | AES-256-GCM with PBKDF2 (600K iterations) |
| `app/services/encryption.py` | TOTP secret encryption | `SECRET_KEY` config | AES-256-GCM (direct key) |
| `app/webhook_encryption.py` | Webhook secret encryption | `WEBHOOK_ENCRYPTION_KEY` env var | AES-256-GCM (direct key) |

See [Backup Service](backup.md) for detailed encryption parameter specifications.

## See Also
- [Backup Service](backup.md) — Backup encryption implementation
- [Configuration](../core/configuration.md) — Encryption key configuration
