"""
Unit tests for semantic cache with tenant isolation.
"""

import threading
import time

import pytest

from onyx.context.search.semantic_cache import (
    CacheEntry,
    CacheStats,
    SemanticCache,
)


class TestSemanticCache:
    """Tests for semantic cache functionality."""
    
    @pytest.fixture
    def cache(self) -> SemanticCache[list[str]]:
        return SemanticCache(max_size=100, default_ttl_seconds=60.0)
    
    def test_cache_miss_returns_none(self, cache: SemanticCache[list[str]]) -> None:
        """Cache miss should return None."""
        result = cache.get(
            query="test query",
            tenant_id="tenant_a",
            acl=["user:alice@a.com"],
        )
        assert result is None
    
    def test_cache_hit_returns_value(self, cache: SemanticCache[list[str]]) -> None:
        """Cache hit should return stored value."""
        cache.set(
            query="test query",
            tenant_id="tenant_a",
            acl=["user:alice@a.com"],
            value=["result1", "result2"],
        )
        
        result = cache.get(
            query="test query",
            tenant_id="tenant_a",
            acl=["user:alice@a.com"],
        )
        
        assert result == ["result1", "result2"]
    
    def test_tenant_isolation(self, cache: SemanticCache[list[str]]) -> None:
        """Different tenants should have isolated caches."""
        # Set value for tenant A
        cache.set(
            query="shared query",
            tenant_id="tenant_a",
            acl=["PUBLIC"],
            value=["tenant_a_results"],
        )
        
        # Set different value for tenant B
        cache.set(
            query="shared query",
            tenant_id="tenant_b",
            acl=["PUBLIC"],
            value=["tenant_b_results"],
        )
        
        # Each tenant should get their own results
        result_a = cache.get(
            query="shared query",
            tenant_id="tenant_a",
            acl=["PUBLIC"],
        )
        result_b = cache.get(
            query="shared query",
            tenant_id="tenant_b",
            acl=["PUBLIC"],
        )
        
        assert result_a == ["tenant_a_results"]
        assert result_b == ["tenant_b_results"]
    
    def test_acl_isolation(self, cache: SemanticCache[list[str]]) -> None:
        """Different ACLs should have isolated cache entries."""
        # Set value for user with full access
        cache.set(
            query="sensitive query",
            tenant_id="tenant_a",
            acl=["user:admin@a.com", "group:admins"],
            value=["full_results"],
        )
        
        # Set value for user with limited access
        cache.set(
            query="sensitive query",
            tenant_id="tenant_a",
            acl=["user:user@a.com"],
            value=["limited_results"],
        )
        
        # Admin gets full results
        admin_result = cache.get(
            query="sensitive query",
            tenant_id="tenant_a",
            acl=["user:admin@a.com", "group:admins"],
        )
        
        # Regular user gets limited results
        user_result = cache.get(
            query="sensitive query",
            tenant_id="tenant_a",
            acl=["user:user@a.com"],
        )
        
        assert admin_result == ["full_results"]
        assert user_result == ["limited_results"]
    
    def test_query_normalization(self, cache: SemanticCache[list[str]]) -> None:
        """Queries should be normalized (case-insensitive, trimmed)."""
        cache.set(
            query="Test Query",
            tenant_id="tenant_a",
            acl=["PUBLIC"],
            value=["results"],
        )
        
        # Same query with different case/whitespace should hit
        result = cache.get(
            query="  test query  ",
            tenant_id="tenant_a",
            acl=["PUBLIC"],
        )
        
        assert result == ["results"]
    
    def test_ttl_expiration(self) -> None:
        """Expired entries should return None."""
        cache: SemanticCache[list[str]] = SemanticCache(
            max_size=100,
            default_ttl_seconds=0.1,  # 100ms TTL
        )
        
        cache.set(
            query="test",
            tenant_id="tenant_a",
            acl=["PUBLIC"],
            value=["results"],
        )
        
        # Should hit immediately
        assert cache.get("test", "tenant_a", ["PUBLIC"]) == ["results"]
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Should miss after expiration
        assert cache.get("test", "tenant_a", ["PUBLIC"]) is None
    
    def test_custom_ttl(self, cache: SemanticCache[list[str]]) -> None:
        """Custom TTL should override default."""
        cache.set(
            query="short_lived",
            tenant_id="tenant_a",
            acl=["PUBLIC"],
            value=["results"],
            ttl_seconds=0.1,
        )
        
        time.sleep(0.15)
        
        result = cache.get("short_lived", "tenant_a", ["PUBLIC"])
        assert result is None
    
    def test_document_invalidation(self, cache: SemanticCache[list[str]]) -> None:
        """Invalidating a document should remove related cache entries."""
        cache.set(
            query="query1",
            tenant_id="tenant_a",
            acl=["PUBLIC"],
            value=["results1"],
            document_ids=["doc1", "doc2"],
        )
        
        cache.set(
            query="query2",
            tenant_id="tenant_a",
            acl=["PUBLIC"],
            value=["results2"],
            document_ids=["doc2", "doc3"],
        )
        
        # Invalidate doc1 - should only affect query1
        count = cache.invalidate_document("doc1", "tenant_a")
        assert count == 1
        
        assert cache.get("query1", "tenant_a", ["PUBLIC"]) is None
        assert cache.get("query2", "tenant_a", ["PUBLIC"]) == ["results2"]
    
    def test_tenant_invalidation(self, cache: SemanticCache[list[str]]) -> None:
        """Invalidating a tenant should remove all their entries."""
        cache.set("q1", "tenant_a", ["PUBLIC"], ["r1"])
        cache.set("q2", "tenant_a", ["PUBLIC"], ["r2"])
        cache.set("q1", "tenant_b", ["PUBLIC"], ["r3"])
        
        count = cache.invalidate_tenant("tenant_a")
        assert count == 2
        
        assert cache.get("q1", "tenant_a", ["PUBLIC"]) is None
        assert cache.get("q2", "tenant_a", ["PUBLIC"]) is None
        assert cache.get("q1", "tenant_b", ["PUBLIC"]) == ["r3"]
    
    def test_stats_tracking(self, cache: SemanticCache[list[str]]) -> None:
        """Cache should track hit/miss statistics."""
        cache.set("q1", "t1", ["PUBLIC"], ["r1"])
        
        # 2 hits
        cache.get("q1", "t1", ["PUBLIC"])
        cache.get("q1", "t1", ["PUBLIC"])
        
        # 1 miss
        cache.get("q2", "t1", ["PUBLIC"])
        
        stats = cache.get_stats()
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.hit_rate == pytest.approx(2/3)
    
    def test_max_size_eviction(self) -> None:
        """Cache should evict entries when max size is reached."""
        cache: SemanticCache[str] = SemanticCache(max_size=10)
        
        # Fill cache beyond max
        for i in range(15):
            cache.set(f"query{i}", "tenant", ["PUBLIC"], f"result{i}")
        
        stats = cache.get_stats()
        assert stats.size <= 10
        assert stats.evictions > 0
    
    def test_clear(self, cache: SemanticCache[list[str]]) -> None:
        """Clear should remove all entries."""
        cache.set("q1", "t1", ["PUBLIC"], ["r1"])
        cache.set("q2", "t1", ["PUBLIC"], ["r2"])
        
        cache.clear()
        
        assert cache.get("q1", "t1", ["PUBLIC"]) is None
        assert cache.get("q2", "t1", ["PUBLIC"]) is None
        assert cache.get_stats().size == 0
    
    def test_thread_safety(self) -> None:
        """Cache should be thread-safe."""
        cache: SemanticCache[int] = SemanticCache(max_size=1000)
        errors: list[Exception] = []
        
        def writer(thread_id: int) -> None:
            try:
                for i in range(100):
                    cache.set(
                        f"query_{thread_id}_{i}",
                        f"tenant_{thread_id % 3}",
                        ["PUBLIC"],
                        i,
                    )
            except Exception as e:
                errors.append(e)
        
        def reader(thread_id: int) -> None:
            try:
                for i in range(100):
                    cache.get(
                        f"query_{thread_id}_{i}",
                        f"tenant_{thread_id % 3}",
                        ["PUBLIC"],
                    )
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            threads.append(threading.Thread(target=writer, args=(i,)))
            threads.append(threading.Thread(target=reader, args=(i,)))
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0


class TestCacheEntry:
    """Tests for CacheEntry class."""
    
    def test_is_expired_false_when_fresh(self) -> None:
        """Fresh entry should not be expired."""
        entry = CacheEntry(
            value="test",
            created_at=time.time(),
            ttl_seconds=60.0,
            tenant_id="t1",
            acl_hash="abc",
            query_hash="xyz",
        )
        assert entry.is_expired() is False
    
    def test_is_expired_true_when_old(self) -> None:
        """Old entry should be expired."""
        entry = CacheEntry(
            value="test",
            created_at=time.time() - 100,
            ttl_seconds=60.0,
            tenant_id="t1",
            acl_hash="abc",
            query_hash="xyz",
        )
        assert entry.is_expired() is True


class TestCacheStats:
    """Tests for CacheStats class."""
    
    def test_hit_rate_zero_when_empty(self) -> None:
        """Hit rate should be 0 when no accesses."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0
    
    def test_hit_rate_calculation(self) -> None:
        """Hit rate should be correctly calculated."""
        stats = CacheStats(hits=75, misses=25)
        assert stats.hit_rate == 0.75
    
    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        stats = CacheStats(hits=10, misses=5, evictions=2, size=100)
        d = stats.to_dict()
        
        assert d["hits"] == 10
        assert d["misses"] == 5
        assert d["evictions"] == 2
        assert d["size"] == 100
        assert d["hit_rate"] == pytest.approx(10/15)
