"""
RAG Security Module - Enterprise-grade security controls for the RAG pipeline.

Provides:
- Prompt injection detection and prevention
- Canary token detection for data exfiltration
- Content sanitization
- Audit logging for sensitive data access
"""

import hashlib
import re
import time
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any

from onyx.utils.logger import setup_logger

logger = setup_logger()


class ThreatLevel(Enum):
    """Threat severity levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Represents a security event for audit logging."""
    event_type: str
    threat_level: ThreatLevel
    description: str
    tenant_id: str | None = None
    user_id: str | None = None
    request_id: str | None = None
    source_content_hash: str | None = None  # Hash of content, not actual content
    matched_pattern: str | None = None
    timestamp: float = field(default_factory=time.time)
    
    def to_audit_log(self) -> dict[str, Any]:
        """Convert to audit log format (safe for logging, no PII/content)."""
        return {
            "event_type": self.event_type,
            "threat_level": self.threat_level.value,
            "description": self.description,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "content_hash": self.source_content_hash,
            "matched_pattern": self.matched_pattern,
            "timestamp": self.timestamp,
        }


@dataclass
class InjectionDetectionResult:
    """Result of prompt injection detection."""
    is_malicious: bool
    threat_level: ThreatLevel
    matched_patterns: list[str]
    sanitized_text: str | None = None
    
    
# Prompt injection patterns - ordered by severity
# These patterns detect common prompt injection attacks
INJECTION_PATTERNS: list[tuple[str, ThreatLevel, str]] = [
    # Critical - Direct instruction override attempts
    (
        r"(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|context)",
        ThreatLevel.CRITICAL,
        "instruction_override",
    ),
    (
        r"(?i)disregard\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?)",
        ThreatLevel.CRITICAL,
        "instruction_override",
    ),
    (
        r"(?i)forget\s+(everything|all|what)\s+(you\s+)?(know|learned|were\s+told)",
        ThreatLevel.CRITICAL,
        "memory_wipe",
    ),
    (
        r"(?i)you\s+are\s+now\s+(a|an)\s+(?!assistant|helpful)",
        ThreatLevel.CRITICAL,
        "role_hijack",
    ),
    (
        r"(?i)new\s+instructions?:\s*",
        ThreatLevel.CRITICAL,
        "instruction_injection",
    ),
    (
        r"(?i)\[\s*system\s*\]",
        ThreatLevel.CRITICAL,
        "system_prompt_injection",
    ),
    (
        r"(?i)<\s*system\s*>",
        ThreatLevel.CRITICAL,
        "system_prompt_injection",
    ),
    
    # High - Jailbreak attempts
    (
        r"(?i)pretend\s+(you\s+)?(are|to\s+be)\s+(not\s+)?(an?\s+)?AI",
        ThreatLevel.HIGH,
        "jailbreak_pretend",
    ),
    (
        r"(?i)act\s+as\s+(if\s+)?(you\s+)?(are\s+)?(not\s+)?bound",
        ThreatLevel.HIGH,
        "jailbreak_unbind",
    ),
    (
        r"(?i)bypass\s+(your\s+)?(safety|security|content)\s+(filters?|guidelines?)",
        ThreatLevel.HIGH,
        "filter_bypass",
    ),
    (
        r"(?i)developer\s+mode",
        ThreatLevel.HIGH,
        "developer_mode",
    ),
    (
        r"(?i)DAN\s+mode",
        ThreatLevel.HIGH,
        "dan_jailbreak",
    ),
    
    # Medium - Suspicious patterns
    (
        r"(?i)reveal\s+(your\s+)?(system\s+)?(prompt|instructions?)",
        ThreatLevel.MEDIUM,
        "prompt_extraction",
    ),
    (
        r"(?i)show\s+(me\s+)?(your\s+)?(original|initial|system)\s+(prompt|instructions?)",
        ThreatLevel.MEDIUM,
        "prompt_extraction",
    ),
    (
        r"(?i)what\s+(are|were)\s+(your\s+)?(original|initial|system)\s+(instructions?|prompts?)",
        ThreatLevel.MEDIUM,
        "prompt_extraction",
    ),
    (
        r"(?i)output\s+(the\s+)?(text|content)\s+(above|before)\s+this",
        ThreatLevel.MEDIUM,
        "context_extraction",
    ),
    
    # Low - Potential manipulation
    (
        r"(?i)you\s+must\s+(always|never)\s+",
        ThreatLevel.LOW,
        "behavior_override",
    ),
    (
        r"(?i)from\s+now\s+on\s*,?\s*(you\s+)?(will|must|should)",
        ThreatLevel.LOW,
        "persistent_override",
    ),
]

# Canary token patterns - detect data exfiltration markers
CANARY_PATTERNS: list[tuple[str, str]] = [
    (r"CANARY_[A-Z0-9]{8,}", "canary_token"),
    (r"EXFIL_[A-Z0-9]{8,}", "exfil_marker"),
    (r"MARKER_[A-Z0-9]{8,}", "marker_token"),
    # Base64-like suspicious payloads in document content
    (r"(?<!\w)(?:[A-Za-z0-9+/]{50,})(?:={0,2})(?!\w)", "potential_encoded_payload"),
]


class RAGSecurityScanner:
    """
    Scans content for prompt injection attacks and other security threats.
    
    Thread-safe and designed for high-throughput scanning during RAG retrieval.
    """
    
    def __init__(
        self,
        enable_canary_detection: bool = True,
        enable_sanitization: bool = True,
        log_security_events: bool = True,
    ):
        self.enable_canary_detection = enable_canary_detection
        self.enable_sanitization = enable_sanitization
        self.log_security_events = log_security_events
        
        # Pre-compile patterns for performance
        self._injection_patterns = [
            (re.compile(pattern), level, name)
            for pattern, level, name in INJECTION_PATTERNS
        ]
        self._canary_patterns = [
            (re.compile(pattern), name)
            for pattern, name in CANARY_PATTERNS
        ]
    
    def _hash_content(self, content: str) -> str:
        """Create a safe hash of content for logging (no actual content)."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def scan_query(
        self,
        query: str,
        tenant_id: str | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
    ) -> InjectionDetectionResult:
        """
        Scan a user query for prompt injection attacks.
        
        Args:
            query: The user's query text
            tenant_id: Tenant ID for audit logging
            user_id: User ID for audit logging
            request_id: Request ID for tracing
            
        Returns:
            InjectionDetectionResult with threat assessment
        """
        matched_patterns: list[str] = []
        max_threat = ThreatLevel.NONE
        
        for pattern, threat_level, pattern_name in self._injection_patterns:
            if pattern.search(query):
                matched_patterns.append(pattern_name)
                if threat_level.value > max_threat.value or (
                    list(ThreatLevel).index(threat_level) > list(ThreatLevel).index(max_threat)
                ):
                    max_threat = threat_level
        
        is_malicious = max_threat in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)
        
        if matched_patterns and self.log_security_events:
            event = SecurityEvent(
                event_type="prompt_injection_detected",
                threat_level=max_threat,
                description=f"Detected {len(matched_patterns)} suspicious patterns in query",
                tenant_id=tenant_id,
                user_id=user_id,
                request_id=request_id,
                source_content_hash=self._hash_content(query),
                matched_pattern=", ".join(matched_patterns[:3]),  # Limit for log size
            )
            logger.warning(f"Security event: {event.to_audit_log()}")
        
        # Optionally sanitize the query
        sanitized = None
        if self.enable_sanitization and is_malicious:
            sanitized = self._sanitize_text(query)
        
        return InjectionDetectionResult(
            is_malicious=is_malicious,
            threat_level=max_threat,
            matched_patterns=matched_patterns,
            sanitized_text=sanitized,
        )
    
    def scan_chunk(
        self,
        chunk_content: str,
        document_id: str | None = None,
        tenant_id: str | None = None,
        request_id: str | None = None,
    ) -> InjectionDetectionResult:
        """
        Scan a retrieved chunk for embedded injection attacks or canary tokens.
        
        This detects attacks where malicious content is embedded in documents
        to manipulate the RAG system when retrieved.
        
        Args:
            chunk_content: The chunk text content
            document_id: Source document ID for audit
            tenant_id: Tenant ID for audit logging
            request_id: Request ID for tracing
            
        Returns:
            InjectionDetectionResult with threat assessment
        """
        matched_patterns: list[str] = []
        max_threat = ThreatLevel.NONE
        
        # Check for injection patterns in chunk content
        for pattern, threat_level, pattern_name in self._injection_patterns:
            if pattern.search(chunk_content):
                matched_patterns.append(f"chunk:{pattern_name}")
                if list(ThreatLevel).index(threat_level) > list(ThreatLevel).index(max_threat):
                    max_threat = threat_level
        
        # Check for canary tokens (potential data exfiltration markers)
        if self.enable_canary_detection:
            for pattern, pattern_name in self._canary_patterns:
                if pattern.search(chunk_content):
                    matched_patterns.append(f"canary:{pattern_name}")
                    # Canary tokens are always high severity
                    if list(ThreatLevel).index(ThreatLevel.HIGH) > list(ThreatLevel).index(max_threat):
                        max_threat = ThreatLevel.HIGH
        
        is_malicious = max_threat in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)
        
        if matched_patterns and self.log_security_events:
            event = SecurityEvent(
                event_type="malicious_chunk_detected",
                threat_level=max_threat,
                description=f"Detected suspicious content in chunk from doc {document_id}",
                tenant_id=tenant_id,
                request_id=request_id,
                source_content_hash=self._hash_content(chunk_content),
                matched_pattern=", ".join(matched_patterns[:3]),
            )
            logger.warning(f"Security event: {event.to_audit_log()}")
        
        sanitized = None
        if self.enable_sanitization and is_malicious:
            sanitized = self._sanitize_text(chunk_content)
        
        return InjectionDetectionResult(
            is_malicious=is_malicious,
            threat_level=max_threat,
            matched_patterns=matched_patterns,
            sanitized_text=sanitized,
        )
    
    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize text by removing or neutralizing injection patterns.
        
        This is a best-effort sanitization - when in doubt, the text
        should be rejected rather than sanitized.
        """
        sanitized = text
        
        # Remove system prompt injection markers
        sanitized = re.sub(r"(?i)\[\s*system\s*\]", "[filtered]", sanitized)
        sanitized = re.sub(r"(?i)<\s*system\s*>", "<filtered>", sanitized)
        
        # Neutralize instruction overrides
        sanitized = re.sub(
            r"(?i)(ignore|disregard|forget)\s+(all\s+)?(previous|prior)",
            "[instruction filtered]",
            sanitized,
        )
        
        return sanitized
    
    def scan_batch(
        self,
        chunks: list[tuple[str, str | None]],  # (content, document_id)
        tenant_id: str | None = None,
        request_id: str | None = None,
    ) -> list[tuple[int, InjectionDetectionResult]]:
        """
        Scan a batch of chunks efficiently.
        
        Returns list of (index, result) for chunks with threats detected.
        Only returns entries for chunks with non-NONE threat levels.
        """
        results: list[tuple[int, InjectionDetectionResult]] = []
        
        for idx, (content, doc_id) in enumerate(chunks):
            result = self.scan_chunk(
                chunk_content=content,
                document_id=doc_id,
                tenant_id=tenant_id,
                request_id=request_id,
            )
            if result.threat_level != ThreatLevel.NONE:
                results.append((idx, result))
        
        return results


class AuditLogger:
    """
    Secure audit logging for RAG data access.
    
    Logs access events without exposing sensitive content.
    """
    
    def __init__(self) -> None:
        self._logger = setup_logger(name="onyx.security.audit")
    
    def log_retrieval(
        self,
        tenant_id: str,
        user_id: str | None,
        request_id: str,
        query_hash: str,
        num_chunks_retrieved: int,
        document_ids: list[str],
        latency_ms: float,
    ) -> None:
        """Log a retrieval event for audit purposes."""
        self._logger.info(
            f"AUDIT:RETRIEVAL tenant={tenant_id} user={user_id or 'anonymous'} "
            f"request={request_id} query_hash={query_hash} "
            f"chunks={num_chunks_retrieved} docs={len(document_ids)} "
            f"latency_ms={latency_ms:.1f}"
        )
    
    def log_acl_check(
        self,
        tenant_id: str,
        user_id: str | None,
        document_id: str,
        access_granted: bool,
        acl_reason: str,
    ) -> None:
        """Log an ACL check for audit purposes."""
        action = "GRANTED" if access_granted else "DENIED"
        self._logger.info(
            f"AUDIT:ACL:{action} tenant={tenant_id} user={user_id or 'anonymous'} "
            f"doc={document_id} reason={acl_reason}"
        )
    
    def log_security_event(self, event: SecurityEvent) -> None:
        """Log a security event."""
        self._logger.warning(f"AUDIT:SECURITY {event.to_audit_log()}")


# Global scanner instance
_default_scanner: RAGSecurityScanner | None = None


def get_security_scanner() -> RAGSecurityScanner:
    """Get the global security scanner instance."""
    global _default_scanner
    if _default_scanner is None:
        _default_scanner = RAGSecurityScanner()
    return _default_scanner


def get_audit_logger() -> AuditLogger:
    """Get the audit logger instance."""
    return AuditLogger()
