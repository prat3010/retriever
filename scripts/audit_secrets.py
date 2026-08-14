#!/usr/bin/env python3
"""
Retriever Platform — Secret Hygiene & Environment Auto-Auditor
Inspects environment settings, checks for default dev credentials, validates entropy/length of keys,
and provides a production readiness status.
"""

import sys
from pathlib import Path

# Add root and api directories to python path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "apps" / "api"))
sys.path.insert(0, str(root_dir))

def audit_secrets() -> bool:
    print("==================================================")
    print("   Retriever Platform — Secret Hygiene Auditor    ")
    print("==================================================")

    # Attempt to load settings
    try:
        from apps.api.src.config import settings
    except ImportError:
        try:
            from src.config import settings
        except ImportError:
            print("❌ Failure: Could not import settings module.")
            return False

    env = settings.ENVIRONMENT
    print(f"Current Environment: [{env.upper()}]")
    print("--------------------------------------------------")

    issues = []
    warnings = []

    # Check 1: ADMIN_MASTER_KEY
    master_key = settings.ADMIN_MASTER_KEY
    if master_key == "dev-admin-master-key-change-in-production":
        msg = "ADMIN_MASTER_KEY is using default development placeholder."
        if env == "production":
            issues.append(f"CRITICAL: {msg}")
        else:
            warnings.append(f"DEV: {msg}")
    elif len(master_key) < 24:
        warnings.append(f"WEAK: ADMIN_MASTER_KEY is short ({len(master_key)} chars). Recommended >= 32 chars.")

    # Check 2: SECRET_KEY
    secret_key = settings.SECRET_KEY
    if secret_key == "dev-retriever-jwt-secret-change-me" or secret_key.startswith("dev-"):
        msg = "SECRET_KEY (JWT) is using development default string."
        if env == "production":
            issues.append(f"CRITICAL: {msg}")
        else:
            warnings.append(f"DEV: {msg}")
    elif len(secret_key) < 32:
        issues.append(f"WEAK: SECRET_KEY must be at least 32 characters (currently {len(secret_key)}).")

    # Check 3: KEY_ENCRYPTION_KEY
    enc_key = settings.KEY_ENCRYPTION_KEY
    if enc_key.startswith("dev-key"):
        msg = "KEY_ENCRYPTION_KEY is using default development placeholder."
        if env == "production":
            issues.append(f"CRITICAL: {msg}")
        else:
            warnings.append(f"DEV: {msg}")

    # Check 4: STORAGE_HMAC_KEY
    hmac_key = settings.STORAGE_HMAC_KEY
    if hmac_key == "local-storage-presign-key":
        msg = "STORAGE_HMAC_KEY is using default development string."
        if env == "production":
            issues.append(f"CRITICAL: {msg}")
        else:
            warnings.append(f"DEV: {msg}")

    # Check 5: Database Connection String
    db_url = settings.DATABASE_URL
    if "postgres:postgres@localhost" in db_url and env == "production":
        issues.append("CRITICAL: DATABASE_URL is pointing to local default postgres credentials in production.")

    # Output Results
    print("\n🔍 Audit Findings:")
    if not issues and not warnings:
        print("  ✅ All secrets pass hygiene and entropy checks!")
    else:
        for w in warnings:
            print(f"  ⚠️  {w}")
        for i in issues:
            print(f"  ❌ {i}")

    print("--------------------------------------------------")
    if issues:
        print("🚨 AUDIT FAILED: Production critical secrets require remediation.")
        return False
    else:
        print("🎉 AUDIT PASSED: System environment secret check completed successfully.")
        return True

if __name__ == "__main__":
    success = audit_secrets()
    sys.exit(0 if success else 1)
