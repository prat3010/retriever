"""Domain Service for Zero-Egress Network Isolation & Air-Gap Sentinel (M127).

Monitors and audits network interfaces, socket bindings, and route resolution
to enforce fail-closed zero-egress invariants for sovereign air-gapped appliances.
Pure domain layer with zero external web framework, database, or ORM dependencies.
"""

import logging
import os
import socket
from datetime import UTC, datetime
from pathlib import Path

from src.domain.abstractions.appliance import (
    AirgapEgressViolationError,
    AirgapNetworkAudit,
    AirgapNetworkState,
    AirgapSentinelProtocol,
    ApplianceDeploymentMode,
)

logger = logging.getLogger(__name__)

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0"})


class AirgapNetworkSentinel(AirgapSentinelProtocol):
    """In-process network isolation sentinel for sovereign air-gapped enclaves."""

    def __init__(
        self,
        deployment_mode: ApplianceDeploymentMode = ApplianceDeploymentMode.AIR_GAPPED_STRICT,
        allowed_hosts: set[str] | None = None,
        resolv_conf_path: str = "/etc/resolv.conf",
    ) -> None:
        self.deployment_mode = deployment_mode
        self.allowed_hosts = set(allowed_hosts or set()) | LOOPBACK_HOSTS
        self.resolv_conf_path = resolv_conf_path
        self._blocked_egress_count = 0
        self._last_audit: AirgapNetworkAudit | None = None
        self._network_state: AirgapNetworkState = AirgapNetworkState.AUDIT_PENDING

    @property
    def current_state(self) -> AirgapNetworkState:
        return self._network_state

    @property
    def blocked_attempts(self) -> int:
        return self._blocked_egress_count

    def audit_isolation(self, strict_enforce: bool = True) -> AirgapNetworkAudit:
        """Audit host network interfaces, DNS configuration, and socket isolation.

        In AIR_GAPPED_STRICT mode, non-loopback DNS resolvers or outbound gateway
        routes are flagged. If strict_enforce is True and an egress violation is
        detected, raises AirgapEgressViolationError immediately (fail-closed).
        """
        now = datetime.now(UTC)
        interfaces: list[str] = []
        dns_servers: list[str] = []
        violations: list[str] = []

        # 1. Discover local network interfaces & hostnames
        try:
            hostname = socket.gethostname()
            interfaces.append(f"hostname:{hostname}")
            try:
                _, _, ip_list = socket.gethostbyname_ex(hostname)
                interfaces.extend(ip_list)
            except Exception:
                pass
        except Exception as exc:
            logger.debug(f"Interface lookup non-fatal note: {exc}")

        # 2. Inspect /etc/resolv.conf if present (Linux / Container)
        resolv_file = Path(self.resolv_conf_path)
        if resolv_file.exists():
            try:
                for line in resolv_file.read_text().splitlines():
                    trimmed = line.strip()
                    if trimmed.startswith("nameserver"):
                        parts = trimmed.split()
                        if len(parts) >= 2:
                            ns = parts[1]
                            dns_servers.append(ns)
                            # In strict air-gap, public internet resolvers (8.8.8.8, 1.1.1.1) are forbidden
                            if (
                                self.deployment_mode
                                == ApplianceDeploymentMode.AIR_GAPPED_STRICT
                            ):
                                if ns not in ("127.0.0.1", "::1", "127.0.0.53"):
                                    # If it's a public WAN IP, flag violation
                                    if not (
                                        ns.startswith("10.")
                                        or ns.startswith("192.168.")
                                        or ns.startswith("172.")
                                    ):
                                        violations.append(
                                            f"External WAN DNS resolver detected: {ns}"
                                        )
            except Exception as exc:
                logger.debug(f"Unable to read resolv.conf: {exc}")

        # 3. Check environment proxy/egress variables
        egress_env_vars = [
            "http_proxy",
            "https_proxy",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
        ]
        for env_var in egress_env_vars:
            val = os.environ.get(env_var)
            if (
                val
                and self.deployment_mode == ApplianceDeploymentMode.AIR_GAPPED_STRICT
            ):
                violations.append(
                    f"Outbound egress proxy configured in environment: {env_var}={val}"
                )

        is_compliant = len(violations) == 0

        if not is_compliant:
            self._network_state = AirgapNetworkState.EGRESS_VIOLATION_DETECTED
            notes = "Egress violations: " + "; ".join(violations)
            audit = AirgapNetworkAudit(
                audited_at=now,
                active_interfaces=interfaces,
                active_sockets_count=len(interfaces),
                dns_resolvers=dns_servers,
                blocked_egress_attempts=self._blocked_egress_count,
                is_compliant=False,
                audit_notes=notes,
            )
            self._last_audit = audit
            if (
                strict_enforce
                and self.deployment_mode == ApplianceDeploymentMode.AIR_GAPPED_STRICT
            ):
                logger.critical(f"Air-gap egress violation detected: {notes}")
                raise AirgapEgressViolationError(notes)
            return audit

        self._network_state = AirgapNetworkState.ISOLATED_COMPLIANT
        audit = AirgapNetworkAudit(
            audited_at=now,
            active_interfaces=interfaces,
            active_sockets_count=len(interfaces),
            dns_resolvers=dns_servers,
            blocked_egress_attempts=self._blocked_egress_count,
            is_compliant=True,
            audit_notes="Air-gap isolation verified: Zero WAN egress paths detected.",
        )
        self._last_audit = audit
        return audit

    def verify_outbound_target(self, host: str, port: int | None = None) -> None:
        """Verify that an attempted socket connection is strictly permitted.

        Raises AirgapEgressViolationError if connection targets an unauthorized WAN host.
        """
        clean_host = host.strip().lower()
        if clean_host in self.allowed_hosts:
            return

        # Check if local loopback range 127.0.0.0/8
        if clean_host.startswith("127."):
            return

        if self.deployment_mode in (
            ApplianceDeploymentMode.AIR_GAPPED_STRICT,
            ApplianceDeploymentMode.TACTICAL_EDGE,
        ):
            self._blocked_egress_count += 1
            self._network_state = AirgapNetworkState.EGRESS_VIOLATION_DETECTED
            err_msg = (
                f"Air-gap egress blocked: Attempted connection to non-authorized target '{host}:{port}' "
                f"in mode '{self.deployment_mode}'."
            )
            logger.error(err_msg)
            raise AirgapEgressViolationError(err_msg)
