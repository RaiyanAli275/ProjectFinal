import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BecauseYouLiked = () => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isNewUser, setIsNewUser] = useState(false);
  const [suggestion, setSuggestion] = useState('');
  const [basedOnBook, setBasedOnBook] = useState('');
  const [interactionCount, setInteractionCount] = useState(0);

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const fetchRecommendations = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:5000/api/recommendations/content-based', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = response.data;
      setRecommendations(data.recommendations || []);
      setIsNewUser(data.is_new_user || false);
      setSuggestion(data.suggestion || '');
      setBasedOnBook(data.based_on_book || '');
      setInteractionCount(data.interaction_count || 0);
      setError(null);
    } catch (error) {
      console.error('Error fetching content-based recommendations:', error);
      setError('Failed to load content-based recommendations');
    } finally {
      setLoading(false);
    }
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

      fetchRecommendations();
    } catch (error) {
      console.error('Interaction error:', error);
    }
  };

  const handleWishlistToggle = async (book) => {
    try {
      const token = localStorage.getItem('token');
      const payload = {
        book_name: book.name,
        book_author: book.author || '',
        book_genres: book.genres || ''
      };

      await axios.post('http://localhost:5000/api/wishlist/toggle', payload, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      fetchRecommendations();
    } catch (error) {
      console.error('Wishlist error:', error);
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
          <span className="ml-3 text-[#4A4A4A]">Loading content recommendations...</span>
        </div>
      </section>
    );
  }

  if (isNewUser) {
    return (
      <section className="px-6 py-4">
        <h2 className="text-lg font-semibold text-[#553B08] mb-4">❤️ Because You Liked</h2>
        <div className="bg-[#ECE5D4] rounded-md p-6 text-center">
          <div className="mb-6">
            <svg className="w-16 h-16 text-[#553B08] mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
          </div>
          <p className="text-[#231F20] mb-3 text-lg font-medium">
            Start liking books to discover similar content!
          </p>
          <p className="text-[#4A4A4A] mb-6">
            {suggestion}
          </p>
        </div>
      </section>
    );
  }

  if (error || recommendations.length === 0) {
    return (
      <section className="px-6 py-4">
        <h2 className="text-lg font-semibold text-[#553B08] mb-2">❤️ Because You Liked</h2>
        <div className="bg-[#ECE5D4] rounded-md p-6 text-center">
          <p className="text-[#4A4A4A] mb-2">
            {error || 'Like some books to get content-based recommendations!'}
          </p>
          <p className="text-[#6B6B6B] text-sm">
            Find books with similar content, genres, and themes to your favorites.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="px-6 py-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <h2 className="text-lg font-semibold text-[#553B08] mb-2">❤️ Because You Liked</h2>
          {basedOnBook && (
            <span className="text-lg font-semibold text-[#553B08] ml-2">
              "{basedOnBook}"
            </span>
          )}
        </div>
        <button
          onClick={fetchRecommendations}
          className="text-[#6B6B6B] hover:text-[#553B08] transition-colors duration-200 p-1"
          title="Refresh recommendations"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      <div className="flex overflow-x-auto space-x-4 scrollbar-hide">
        {recommendations.map((book, index) => (
          <div 
            key={index} 
            className="w-72 h-56 bg-[#ECE5D4] rounded-md p-6 hover:scale-105 transition-transform duration-200 group relative flex-shrink-0 flex flex-col"
          >
            <button
              onClick={() => handleWishlistToggle(book)}
              className={`absolute top-2 right-2 p-1.5 rounded-full transition-all duration-200 ${
                book.in_wishlist
                  ? 'bg-yellow-500/30 text-yellow-600'
                  : 'bg-black/10 text-gray-600 hover:bg-yellow-500/30 hover:text-yellow-600'
              }`}
              title={book.in_wishlist ? 'Remove from wishlist' : 'Add to wishlist'}
            >
              <svg className="w-4 h-4" fill={book.in_wishlist ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
            </button>

            <div className="pr-8 mb-4 flex-grow">
              <h4 className="text-base font-semibold text-[#231F20] leading-tight mb-2 line-clamp-2" title={book.name}>
                {book.name}
              </h4>
              <p className="text-sm text-[#553B08] mb-3 line-clamp-1" title={book.author}>
                {book.author || 'Unknown Author'}
              </p>
            </div>

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
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 718.736 3h4.018c.163 0 .326.20.485.60L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 712 2v6a2 2 0 01-2 2h-2.5" />
                </svg>
                Pass
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

export default BecauseYouLiked;