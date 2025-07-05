import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useRecommendationCache } from '../context/RecommendationCacheContext';

const BasedOnLikes = () => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const { getCachedData, setCachedData } = useRecommendationCache();

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const fetchRecommendations = async (forceRefresh = false) => {
    try {
      const cacheKey = 'based-on-likes';
      
      // Check cache first unless force refresh
      if (!forceRefresh) {
        const cachedData = getCachedData(cacheKey);
        if (cachedData) {
          setRecommendations(cachedData.recommendations || []);
          setLoading(false);
          return;
        }
      }

      const isRefreshing = forceRefresh;
      if (isRefreshing) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      
      setError(null);
      
      const token = localStorage.getItem('token');
      
      const cacheBuster = forceRefresh ? `?t=${Date.now()}` : '';
      const endpoint = forceRefresh
        ? 'http://localhost:5000/api/recommendations/based-on-likes/refresh'
        : 'http://localhost:5000/api/recommendations/based-on-likes';
      
      const method = forceRefresh ? 'POST' : 'GET';
      const fullUrl = endpoint + cacheBuster;
      
      const response = await axios({
        method: method,
        url: fullUrl,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Cache-Control': forceRefresh ? 'no-cache, no-store, must-revalidate' : 'max-age=300'
        }
      });

      if (response.data && response.data.recommendations) {
        setRecommendations(response.data.recommendations);
        
        // Cache the data
        setCachedData(cacheKey, response.data);
      } else {
        setRecommendations([]);
      }
      
    } catch (error) {
      console.error('Error fetching based-on-likes recommendations:', error);
      setError('Failed to load recommendations');
      setRecommendations([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    fetchRecommendations(true);
  };

  const handleBookInteraction = async (book, action) => {
    try {
      const token = localStorage.getItem('token');
      const payload = {
        book_name: book.name,
        book_author: book.author || '',
        book_genres: book.genres || ''
      };

      let endpoint = '';
      if (action === 'like') {
        endpoint = 'http://localhost:5000/api/books/like';
      } else if (action === 'dislike') {
        endpoint = 'http://localhost:5000/api/books/dislike';
      }

      await axios.post(endpoint, payload, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      // Optimistic update - mark book as interacted with immediately
      setRecommendations(prevRecs =>
        prevRecs.map(rec =>
          rec.name === book.name
            ? { ...rec, user_interaction: action }
            : rec
        )
      );
    } catch (error) {
      console.error('Interaction error:', error);
    }
  };

  const handleBuyBook = async (book) => {
    try {
      const token = localStorage.getItem('token');
      const payload = {
        book_name: book.name
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
          <span className="ml-3 text-[#4A4A4A]">Analyzing your reading preferences...</span>
        </div>
      </section>
    );
  }

  if (error || recommendations.length === 0) {
    return (
      <section className="px-6 py-4">
        <h2 className="text-lg font-semibold text-[#553B08] mb-2">🧠 Based On Your Liked Books</h2>
        <div className="bg-[#ECE5D4] rounded-md p-6 text-center">
          <p className="text-[#4A4A4A] mb-2">
            {error || 'Like some books to see personalized content-based recommendations!'}
          </p>
          <p className="text-[#6B6B6B] text-sm">
            Our AI analyzes the content patterns of all your liked books to find similar ones.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="px-6 py-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <h2 className="text-lg font-semibold text-[#553B08] mb-2">🧠 Based On Your Liked Books</h2>
          {recommendations.length > 0 && (
            <span className="ml-2 text-sm text-[#553B08] bg-[#ECE5D4] px-2 py-1 rounded-md">
              {recommendations.length} books
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
          title="Force refresh (recalculate recommendations)"
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

      <div className="flex overflow-x-auto space-x-4 scrollbar-hide">
        {recommendations
          .filter(book => !book.user_interaction)
          .reduce((unique, book) => {
            const isDuplicate = unique.some(existingBook => 
              existingBook.name.toLowerCase().trim() === book.name.toLowerCase().trim()
            );
            if (!isDuplicate) {
              unique.push(book);
            }
            return unique;
          }, [])
          .slice(0, 10)
          .map((book, index) => (
          <div 
            key={index} 
            className="w-72 h-56 bg-[#ECE5D4] rounded-md p-6 hover:scale-105 transition-transform duration-200 group relative flex-shrink-0 flex flex-col"
          >
            <div className="pr-8 mb-4 flex-grow">
              <h4 className="text-base font-semibold text-[#231F20] leading-tight mb-2 line-clamp-2" title={book.name}>
                {book.name}
              </h4>
              <p className="text-sm text-[#553B08] mb-3 line-clamp-1" title={book.author}>
                {book.author || 'Unknown Author'}
              </p>
              {book.user_interaction && (
                <div className="text-xs text-green-600 mb-2 flex items-center">
                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  You {book.user_interaction}d this
                </div>
              )}
            </div>

            {!book.user_interaction && (
              <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex space-x-2 mt-auto">
                <button
                  onClick={() => handleBookInteraction(book, 'like')}
                  className="flex-1 flex items-center justify-center px-2 py-2 rounded-md bg-green-500/20 text-green-600 hover:bg-green-500/30 transition-colors duration-200 text-sm font-medium"
                  title="Like this book"
                >
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.60L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 712-2h2.5" />
                  </svg>
                  Like
                </button>
                <button
                  onClick={() => handleBuyBook(book)}
                  className="flex-1 flex items-center justify-center px-2 py-2 rounded-md bg-blue-900/20 text-blue-900 hover:bg-blue-900/30 transition-colors duration-200 text-sm font-medium"
                  title="Buy this book"
                >
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-2.5 5M7 13l2.5 5m6.5-5v6a2 2 0 01-2 2H9a2 2 0 01-2-2v-6m6.5-5H9.5" />
                  </svg>
                  Buy
                </button>
                <button
                  onClick={() => handleBookInteraction(book, 'dislike')}
                  className="flex-1 flex items-center justify-center px-2 py-2 rounded-md bg-red-500/20 text-red-600 hover:bg-red-500/30 transition-colors duration-200 text-sm font-medium"
                  title="Pass on this book"
                >
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 718.736 3h4.018c.163 0 .326.20.485.60L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                  </svg>
                  Pass
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
};

export default BasedOnLikes;