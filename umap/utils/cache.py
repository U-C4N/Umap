"""Caching system for Umap data."""
import os
import pickle
import hashlib
import time
from pathlib import Path
from typing import Dict, Optional, Any
import geopandas as gp


class UmapCache:
    """Cache system for storing and retrieving map data."""
    
    def __init__(self, cache_dir: Optional[str] = None, max_age_days: int = 7):
        """Initialize cache system.
        
        Args:
            cache_dir: Directory to store cache files. Defaults to ~/.umap_cache
            max_age_days: Maximum age of cached data in days
        """
        if cache_dir is None:
            cache_dir = os.path.expanduser("~/.umap_cache")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age_seconds = max_age_days * 24 * 3600
    
    def _get_cache_key(self, location: Any, radius: float, layers: Dict) -> str:
        """Generate cache key from parameters."""
        # Convert location to string representation
        if isinstance(location, tuple):
            loc_str = f"{location[0]:.6f},{location[1]:.6f}"
        else:
            loc_str = str(location)
        
        # Create hash from parameters
        key_data = f"{loc_str}_{radius}_{str(sorted(layers.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for given key."""
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file is still valid (not too old)."""
        if not cache_path.exists():
            return False
        
        file_age = time.time() - cache_path.stat().st_mtime
        return file_age < self.max_age_seconds
    
    def get_cached_data(self, location: Any, radius: float, layers: Dict) -> Optional[Dict[str, gp.GeoDataFrame]]:
        """Retrieve cached data if available and valid.
        
        Args:
            location: Location (coordinates or address)
            radius: Radius in meters
            layers: Layer configuration
            
        Returns:
            Cached GeoDataFrames or None if not available
        """
        cache_key = self._get_cache_key(location, radius, layers)
        cache_path = self._get_cache_path(cache_key)
        
        if not self._is_cache_valid(cache_path):
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)
                return cached_data
        except Exception as e:
            print(f"Cache read error: {e}")
            # Remove corrupted cache file
            try:
                cache_path.unlink()
            except:
                pass
            return None
    
    def cache_data(self, location: Any, radius: float, layers: Dict, data: Dict[str, gp.GeoDataFrame]) -> None:
        """Store data in cache.
        
        Args:
            location: Location (coordinates or address)
            radius: Radius in meters
            layers: Layer configuration
            data: GeoDataFrames to cache
        """
        cache_key = self._get_cache_key(location, radius, layers)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Cache write error: {e}")
    
    def clear_cache(self, older_than_days: Optional[int] = None) -> int:
        """Clear cache files.
        
        Args:
            older_than_days: Only clear files older than this many days.
                           If None, clear all cache files.
                           
        Returns:
            Number of files removed
        """
        removed_count = 0
        cutoff_time = None
        
        if older_than_days is not None:
            cutoff_time = time.time() - (older_than_days * 24 * 3600)
        
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                if cutoff_time is None or cache_file.stat().st_mtime < cutoff_time:
                    cache_file.unlink()
                    removed_count += 1
            except Exception as e:
                print(f"Error removing cache file {cache_file}: {e}")
        
        return removed_count
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cache usage.
        
        Returns:
            Dictionary with cache statistics
        """
        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'cache_dir': str(self.cache_dir),
            'file_count': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'max_age_days': self.max_age_seconds / (24 * 3600)
        }


# Global cache instance
_cache_instance = None


def get_cache() -> UmapCache:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = UmapCache()
    return _cache_instance


def clear_cache(older_than_days: Optional[int] = None) -> int:
    """Clear cache files. Convenience function."""
    return get_cache().clear_cache(older_than_days)


def get_cache_info() -> Dict[str, Any]:
    """Get cache information. Convenience function."""
    return get_cache().get_cache_info() 