"""
Semantic Cache for RAG Retrieval - Enterprise-grade caching with tenant isolation.

Provides:
- Query result caching with tenant+ACL keys
- Configurable TTL and size limits
- Cache invalidation on document updates
- Metrics for cache hit/miss rates
"""

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Generic
from typing import TypeVar

from onyx.utils.logger import setup_logger

logger = setup_logger()

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """A cached entry with metadata."""
    value: T
    created_at: float
    ttl_seconds: float
    tenant_id: str
    acl_hash: str
    query_hash: str
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() - self.created_at > self.ttl_seconds


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for metrics export."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size": self.size,
            "hit_rate": self.hit_rate,
        }


class SemanticCache(Generic[T]):
    """
    Thread-safe semantic cache with tenant and ACL isolation.
    
    Cache keys are derived from:
    - Query text (hashed)
    - Tenant ID
    - User ACL (hashed)
    - Optional additional context
    
    This ensures that:
    1. Different tenants never share cache entries
    2. Users with different ACLs get different results
    3. Queries are efficiently deduplicated
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        default_ttl_seconds: float = 300.0,  # 5 minutes
        cleanup_interval_seconds: float = 60.0,
    ):
        self._cache: dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._default_ttl = default_ttl_seconds
        self._cleanup_interval = cleanup_interval_seconds
        self._last_cleanup = time.time()
        self._stats = CacheStats()
        
        # Document invalidation tracking
        # Maps document_id -> set of cache keys that depend on it
        self._doc_to_keys: dict[str, set[str]] = {}
    
    def _hash_query(self, query: str) -> str:
        """Create a hash of the query for cache key."""
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()[:32]
    
    def _hash_acl(self, acl: list[str]) -> str:
        """Create a hash of the ACL for cache key."""
        sorted_acl = sorted(set(acl))
        acl_str = "|".join(sorted_acl)
        return hashlib.sha256(acl_str.encode()).hexdigest()[:16]
    
    def _make_cache_key(
        self,
        query: str,
        tenant_id: str,
        acl: list[str],
        context: str | None = None,
    ) -> str:
        """
        Create a cache key from query, tenant, and ACL.
        
        The key structure ensures tenant and ACL isolation.
        """
        query_hash = self._hash_query(query)
        acl_hash = self._hash_acl(acl)
        
        key_parts = [tenant_id, query_hash, acl_hash]
        if context:
            key_parts.append(hashlib.sha256(context.encode()).hexdigest()[:8])
        
        return ":".join(key_parts)
    
    def _maybe_cleanup(self) -> None:
        """Run cleanup if enough time has passed."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = now
        self._cleanup_expired()
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            self._remove_entry(key)
            self._stats.evictions += 1
        
        if expired_keys:
            logger.debug(f"Semantic cache cleanup: removed {len(expired_keys)} expired entries")
    
    def _remove_entry(self, key: str) -> None:
        """Remove an entry and clean up document tracking."""
        if key in self._cache:
            del self._cache[key]
            self._stats.size = len(self._cache)
            
            # Clean up document tracking
            for doc_keys in self._doc_to_keys.values():
                doc_keys.discard(key)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries if cache is full."""
        if len(self._cache) < self._max_size:
            return
        
        # Sort by hit count and creation time (LRU-ish)
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: (x[1].hit_count, x[1].created_at),
        )
        
        # Remove bottom 10%
        num_to_remove = max(1, len(sorted_entries) // 10)
        for key, _ in sorted_entries[:num_to_remove]:
            self._remove_entry(key)
            self._stats.evictions += 1
    
    def get(
        self,
        query: str,
        tenant_id: str,
        acl: list[str],
        context: str | None = None,
    ) -> T | None:
        """
        Get a cached result if available.
        
        Args:
            query: The search query
            tenant_id: The tenant ID (required for isolation)
            acl: User's ACL entries (required for isolation)
            context: Optional additional context for key
            
        Returns:
            Cached value if hit, None if miss
        """
        key = self._make_cache_key(query, tenant_id, acl, context)
        
        with self._lock:
            self._maybe_cleanup()
            
            entry = self._cache.get(key)
            if entry is None:
                self._stats.misses += 1
                return None
            
            if entry.is_expired():
                self._remove_entry(key)
                self._stats.misses += 1
                return None
            
            # Cache hit
            entry.hit_count += 1
            self._stats.hits += 1
            
            logger.debug(
                f"Semantic cache hit: tenant={tenant_id} "
                f"query_hash={entry.query_hash[:8]} hits={entry.hit_count}"
            )
            
            return entry.value
    
    def set(
        self,
        query: str,
        tenant_id: str,
        acl: list[str],
        value: T,
        ttl_seconds: float | None = None,
        context: str | None = None,
        document_ids: list[str] | None = None,
    ) -> None:
        """
        Cache a result.
        
        Args:
            query: The search query
            tenant_id: The tenant ID
            acl: User's ACL entries
            value: The value to cache
            ttl_seconds: Optional custom TTL
            context: Optional additional context
            document_ids: Document IDs in the result (for invalidation)
        """
        key = self._make_cache_key(query, tenant_id, acl, context)
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        
        with self._lock:
            self._evict_lru()
            
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl_seconds=ttl,
                tenant_id=tenant_id,
                acl_hash=self._hash_acl(acl),
                query_hash=self._hash_query(query),
            )
            
            self._cache[key] = entry
            self._stats.size = len(self._cache)
            
            # Track document dependencies for invalidation
            if document_ids:
                for doc_id in document_ids:
                    if doc_id not in self._doc_to_keys:
                        self._doc_to_keys[doc_id] = set()
                    self._doc_to_keys[doc_id].add(key)
    
    def invalidate_document(self, document_id: str, tenant_id: str) -> int:
        """
        Invalidate all cache entries that include a specific document.
        
        Should be called when a document is updated or deleted.
        
        Args:
            document_id: The document that was changed
            tenant_id: The tenant ID (for logging/verification)
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_remove = self._doc_to_keys.get(document_id, set()).copy()
            
            count = 0
            for key in keys_to_remove:
                if key in self._cache:
                    # Verify tenant isolation
                    if self._cache[key].tenant_id == tenant_id:
                        self._remove_entry(key)
                        count += 1
            
            # Clean up document tracking
            if document_id in self._doc_to_keys:
                del self._doc_to_keys[document_id]
            
            if count > 0:
                logger.info(
                    f"Invalidated {count} cache entries for document "
                    f"{document_id} in tenant {tenant_id}"
                )
            
            return count
    
    def invalidate_tenant(self, tenant_id: str) -> int:
        """
        Invalidate all cache entries for a tenant.
        
        Useful for bulk operations or tenant-wide reindex.
        
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if entry.tenant_id == tenant_id
            ]
            
            for key in keys_to_remove:
                self._remove_entry(key)
            
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for tenant {tenant_id}")
            
            return len(keys_to_remove)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._doc_to_keys.clear()
            self._stats = CacheStats()
            logger.info("Semantic cache cleared")
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=len(self._cache),
            )


# Global cache instance for retrieval results
_retrieval_cache: SemanticCache | None = None


def get_retrieval_cache() -> SemanticCache:
    """Get the global retrieval cache instance."""
    global _retrieval_cache
    if _retrieval_cache is None:
        _retrieval_cache = SemanticCache(
            max_size=10000,
            default_ttl_seconds=300.0,
        )
    return _retrieval_cache


def invalidate_document_cache(document_id: str, tenant_id: str) -> None:
    """Invalidate cache entries for a document (call on document update/delete)."""
    cache = get_retrieval_cache()
    cache.invalidate_document(document_id, tenant_id)
