import React, { createContext, useContext, useState, useCallback } from 'react';

const RecommendationCacheContext = createContext();

export const useRecommendationCache = () => {
  const context = useContext(RecommendationCacheContext);
  if (!context) {
    throw new Error('useRecommendationCache must be used within a RecommendationCacheProvider');
  }
  return context;
};

export const RecommendationCacheProvider = ({ children }) => {
  const [cache, setCache] = useState({});
  const [lastFetchTimes, setLastFetchTimes] = useState({});

  const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

  const getCachedData = useCallback((key) => {
    const now = Date.now();
    const lastFetch = lastFetchTimes[key];
    
    if (cache[key] && lastFetch && (now - lastFetch) < CACHE_DURATION) {
      console.log(`📂 Cache HIT for ${key} (age: ${Math.round((now - lastFetch) / 1000)}s)`);
      return cache[key];
    }
    
    console.log(`❌ Cache MISS for ${key} (${lastFetch ? 'expired' : 'not found'})`);
    return null;
  }, [cache, lastFetchTimes]);

  const setCachedData = useCallback((key, data) => {
    console.log(`💾 Caching data for ${key}`);
    setCache(prev => ({ ...prev, [key]: data }));
    setLastFetchTimes(prev => ({ ...prev, [key]: Date.now() }));
  }, []);

  const invalidateCache = useCallback((pattern) => {
    console.log(`🗑️ Invalidating cache for pattern: ${pattern}`);
    setCache(prev => {
      const newCache = { ...prev };
      Object.keys(newCache).forEach(key => {
        if (key.includes(pattern)) {
          delete newCache[key];
        }
      });
      return newCache;
    });
    setLastFetchTimes(prev => {
      const newTimes = { ...prev };
      Object.keys(newTimes).forEach(key => {
        if (key.includes(pattern)) {
          delete newTimes[key];
        }
      });
      return newTimes;
    });
  }, []);

  const clearAllCache = useCallback(() => {
    console.log('🗑️ Clearing all recommendation cache');
    setCache({});
    setLastFetchTimes({});
  }, []);

  const value = {
    getCachedData,
    setCachedData,
    invalidateCache,
    clearAllCache,
    cacheSize: Object.keys(cache).length
  };

  return (
    <RecommendationCacheContext.Provider value={value}>
      {children}
    </RecommendationCacheContext.Provider>
  );
};