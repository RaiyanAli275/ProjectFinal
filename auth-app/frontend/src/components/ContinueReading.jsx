import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useRecommendationCache } from '../context/RecommendationCacheContext';

const ContinueReading = () => {
  const { token } = useAuth();
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const { getCachedData, setCachedData, invalidateCache } = useRecommendationCache();

  useEffect(() => {
    fetchRecommendations(false); // Use cache first on mount
  }, []);

  const fetchRecommendations = async (forceRefresh = false) => {
    try {
      const cacheKey = 'continue-reading';
      
      // Check cache first unless force refresh
      if (!forceRefresh) {
        const cachedData = getCachedData(cacheKey);
        if (cachedData) {
          console.log('Continue Reading: Using cached data:', cachedData);
          setRecommendations(cachedData.recommendations || []);
          setLoading(false);
          return;
        }
      }

      setLoading(true);
      setError(null);
      
      const endpoint = forceRefresh
        ? 'http://localhost:5000/api/continue-reading/refresh'
        : 'http://localhost:5000/api/continue-reading/';
      
      const method = forceRefresh ? 'POST' : 'GET';
      
      const cacheBuster = forceRefresh ? `?t=${Date.now()}` : '';
      const fullUrl = endpoint + cacheBuster;
      
      const response = await fetch(fullUrl, {
        method: method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Cache-Control': forceRefresh ? 'no-cache, no-store, must-revalidate' : 'max-age=300'
        }
      });

      const data = await response.json();
      
      if (response.ok) {
        console.log('Continue Reading: API response:', data);
        setRecommendations(data.recommendations || []);
        setError(null);
        
        // Cache the data
        setCachedData(cacheKey, data);
      } else {
        console.error('Continue Reading: API error:', data);
        setError(data.message || 'Failed to load recommendations');
        setRecommendations([]);
      }
    } catch (err) {
      setError('Network error occurred');
      setRecommendations([]);
      console.error('Continue reading fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    // Clear cache for this section
    invalidateCache('continue-reading');
    await fetchRecommendations(true);
    setRefreshing(false);
  };

  const handleBookInteraction = async (bookName, action) => {
    try {
      const endpoint = action === 'like' ? '/api/books/like' : '/api/books/dislike';
      
      const response = await fetch(`http://localhost:5000${endpoint}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          book_name: bookName,
          book_author: '',
          book_genres: ''
        })
      });

      if (response.ok) {
        // Use optimistic update instead of full refetch
        // Remove the book from recommendations since user interacted with it
        setRecommendations(prev => prev.filter(rec => rec.next_book.title !== bookName));
      }
    } catch (err) {
      console.error('Interaction error:', err);
    }
  };

  const handleBuyBook = async (bookName) => {
    try {
      const payload = {
        book_name: bookName
      };

      const response = await axios.post('http://localhost:5000/api/books/buy', payload, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.data.url) {
        // Open the book URL in a new tab
        window.open(response.data.url, '_blank');
      } else {
        alert('Book purchase URL not available');
      }

    } catch (error) {
      console.error('Buy book error:', error);
      alert('Unable to get book purchase link');
    }
  };

  if (loading) {
    return (
      <section className="px-6 py-4">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#553B08]"></div>
          <span className="ml-3 text-[#4A4A4A]">Loading series recommendations...</span>
        </div>
      </section>
    );
  }

  if (error && recommendations.length === 0) {
    return (
      <section className="px-6 py-4">
        <h2 className="text-lg font-semibold text-[#553B08] mb-2">📚 Continue Reading</h2>
        <div className="bg-[#ECE5D4] rounded-md p-6 text-center">
          <p className="text-[#4A4A4A] mb-2">No series found</p>
          <p className="text-[#6B6B6B] text-sm">Like some books from series to see continue reading recommendations!</p>
        </div>
      </section>
    );
  }

  return (
    <section className="px-6 py-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <h2 className="text-lg font-semibold text-[#553B08] mb-2">📚 Continue Reading</h2>
          {recommendations.length > 0 && (
            <span className="ml-2 text-sm text-[#553B08] bg-[#ECE5D4] px-2 py-1 rounded-md">
              {recommendations.length} Series
            </span>
          )}
          {refreshing && (
            <span className="ml-2 text-sm text-[#553B08] bg-[#ECE5D4] px-2 py-1 rounded-md flex items-center">
              <div className="animate-spin rounded-full h-3 w-3 border-b border-[#553B08] mr-1"></div>
              Refreshing
            </span>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className={`text-[#6B6B6B] hover:text-[#553B08] transition-colors duration-200 p-1 ${
            refreshing ? 'opacity-50 cursor-not-allowed' : ''
          }`}
          title="Refresh recommendations"
        >
          <svg
            className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {recommendations.length === 0 ? (
        <div className="bg-[#ECE5D4] rounded-md p-6 text-center">
          <p className="text-[#4A4A4A]">No series found</p>
          <p className="text-[#6B6B6B] text-sm">Like some books from series to see continue reading recommendations!</p>
        </div>
      ) : (
        <div className="flex overflow-x-auto space-x-4 scrollbar-hide">
          {recommendations.map((rec, index) => (
            <ContinueReadingCard
              key={index}
              recommendation={rec}
              onInteraction={handleBookInteraction}
              onBuy={handleBuyBook}
            />
          ))}
        </div>
      )}
    </section>
  );
};

const ContinueReadingCard = ({ recommendation, onInteraction, onBuy }) => {
  const { next_book, attribution, series_name, verification_status } = recommendation;

  const getVerificationBadge = () => {
    if (verification_status === 'verified') {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded text-xs bg-green-500/20 text-green-600">
          ✓ Verified
        </span>
      );
    }
    return null;
  };

  return (
    <div className="w-72 h-56 bg-[#ECE5D4] rounded-md p-6 hover:scale-105 transition-transform duration-200 group relative flex-shrink-0 flex flex-col">
      <div className="mb-4 flex-grow">
        <h4 className="text-base font-semibold text-[#231F20] leading-tight mb-2 line-clamp-2" title={next_book.title}>
          {next_book.title}
        </h4>
        <p className="text-sm text-[#553B08] mb-2 line-clamp-1" title={next_book.author}>
          by {next_book.author}
        </p>
        <p className="text-sm text-green-600 mb-2 font-medium">{attribution}</p>
        
        <div className="flex items-center gap-2 mb-3">
          <span className="bg-[#F3EDE3] text-[#553B08] px-2 py-1 rounded text-xs">
            {series_name}
          </span>
          {getVerificationBadge()}
        </div>
      </div>

      <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex space-x-2 mt-auto">
        <button
          onClick={() => onInteraction(next_book.title, 'like')}
          className="flex-1 flex items-center justify-center px-2 py-2 rounded-md bg-green-500/20 text-green-600 hover:bg-green-500/30 transition-colors duration-200 text-sm font-medium"
          title="Like this book"
        >
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.60L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 712-2h2.5" />
          </svg>
          Like
        </button>
        <button
          onClick={() => onBuy(next_book.title)}
          className="flex-1 flex items-center justify-center px-2 py-2 rounded-md bg-blue-900/20 text-blue-900 hover:bg-blue-900/30 transition-colors duration-200 text-sm font-medium"
          title="Buy this book"
        >
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-2.5 5M7 13l2.5 5m6.5-5v6a2 2 0 01-2 2H9a2 2 0 01-2-2v-6m6.5-5H9.5" />
          </svg>
          Buy
        </button>
        <button
          onClick={() => onInteraction(next_book.title, 'dislike')}
          className="flex-1 flex items-center justify-center px-2 py-2 rounded-md bg-red-500/20 text-red-600 hover:bg-red-500/30 transition-colors duration-200 text-sm font-medium"
          title="Pass on this book"
        >
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 718.736 3h4.018c.163 0 .326.20.485.60L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 712 2v6a2 2 0 01-2 2h-2.5" />
          </svg>
          Pass
        </button>
      </div>
    </div>
  );
};

export default ContinueReading;