from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path


def generate_secret_key() -> str:
    return secrets.token_hex(32)


def generate_health_secret() -> str:
    return secrets.token_urlsafe(32)


def generate_metrics_secret() -> str:
    return secrets.token_urlsafe(32)


def resolve_secrets(inp: object, existing: dict[str, str] | None = None) -> dict[str, str]:
    existing = existing or {}
    result: dict[str, str] = {}

    result["SECRET_KEY"] = existing.get("SECRET_KEY") or generate_secret_key()
    admin_pw = getattr(inp, "admin_password", "") or ""
    result["ADMIN_PASSWORD"] = existing.get("ADMIN_PASSWORD") or str(admin_pw)

    if getattr(inp, "enable_newsletter", False) or getattr(inp, "smtp_host", ""):
        smtp_pw = getattr(inp, "smtp_password", "") or ""
        result["SMTP_PASSWORD"] = existing.get("SMTP_PASSWORD") or str(smtp_pw)

    result["HEALTH_CHECK_SECRET"] = existing.get("HEALTH_CHECK_SECRET") or generate_health_secret()
    result["METRICS_SECRET"] = existing.get("METRICS_SECRET") or generate_metrics_secret()

    if getattr(inp, "enable_backup_encryption", False):
        result["BACKUP_ENCRYPTION_KEY"] = existing.get(
            "BACKUP_ENCRYPTION_KEY"
        ) or secrets.token_hex(32)

    if getattr(inp, "storage_backend", "local") == "s3":
        s3_key = getattr(inp, "s3_access_key", "") or ""
        s3_secret = getattr(inp, "s3_secret_key", "") or ""
        result["S3_ACCESS_KEY"] = existing.get("S3_ACCESS_KEY") or str(s3_key)
        result["S3_SECRET_KEY"] = existing.get("S3_SECRET_KEY") or str(s3_secret)

    return result


def write_env_file(path: Path, secrets_dict: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"SECRET_KEY={secrets_dict.get('SECRET_KEY', '')}",
        f"ADMIN_PASSWORD={secrets_dict.get('ADMIN_PASSWORD', '')}",
    ]

    if secrets_dict.get("HEALTH_CHECK_SECRET"):
        lines.append(f"HEALTH_CHECK_SECRET={secrets_dict['HEALTH_CHECK_SECRET']}")
    if secrets_dict.get("METRICS_SECRET"):
        lines.append(f"METRICS_SECRET={secrets_dict['METRICS_SECRET']}")
    if secrets_dict.get("SMTP_PASSWORD"):
        lines.append(f"SMTP_PASSWORD={secrets_dict['SMTP_PASSWORD']}")
    if secrets_dict.get("BACKUP_ENCRYPTION_KEY"):
        lines.append(f"BACKUP_ENCRYPTION_KEY={secrets_dict['BACKUP_ENCRYPTION_KEY']}")
    if secrets_dict.get("S3_ACCESS_KEY"):
        lines.append(f"S3_ACCESS_KEY={secrets_dict['S3_ACCESS_KEY']}")
    if secrets_dict.get("S3_SECRET_KEY"):
        lines.append(f"S3_SECRET_KEY={secrets_dict['S3_SECRET_KEY']}")

    content = "\n".join(lines) + "\n"
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w") as f:
            f.write(content)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def read_env_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            elif len(value) >= 2 and value[0] == "'" and value[-1] == "'":
                value = value[1:-1]
            result[key] = value

    return result
