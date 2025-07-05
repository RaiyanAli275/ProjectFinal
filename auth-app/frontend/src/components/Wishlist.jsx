import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Wishlist = () => {
  const [wishlist, setWishlist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [removeLoading, setRemoveLoading] = useState({});
  const [statistics, setStatistics] = useState(null);
  const [showStatistics, setShowStatistics] = useState(false);

  // Load wishlist on component mount
  useEffect(() => {
    loadWishlist();
    loadStatistics();
  }, []);

  const loadWishlist = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:5000/api/wishlist/', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setWishlist(response.data.wishlist || []);
    } catch (error) {
      console.error('Error loading wishlist:', error);
      setWishlist([]);
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:5000/api/wishlist/statistics', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setStatistics(response.data.statistics);
    } catch (error) {
      console.error('Error loading wishlist statistics:', error);
    }
  };

  const handleRemoveFromWishlist = async (book) => {
    const bookKey = `${book.book_name}-${book.book_author}`;
    setRemoveLoading(prev => ({ ...prev, [bookKey]: true }));

    try {
      const token = localStorage.getItem('token');
      const payload = {
        book_name: book.book_name
      };

      await axios.post('http://localhost:5000/api/wishlist/remove', payload, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      // Remove book from local state
      setWishlist(prevWishlist => 
        prevWishlist.filter(b => b.book_name !== book.book_name)
      );

      // Reload statistics
      loadStatistics();
    } catch (error) {
      console.error('Error removing from wishlist:', error);
    } finally {
      setRemoveLoading(prev => ({ ...prev, [bookKey]: false }));
    }
  };


  const handleClearWishlist = async () => {
    if (!window.confirm('Are you sure you want to clear your entire wishlist? This action cannot be undone.')) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.post('http://localhost:5000/api/wishlist/clear?confirm=true', {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      setWishlist([]);
      setStatistics(null);
    } catch (error) {
      console.error('Error clearing wishlist:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#553B08]"></div>
        <span className="ml-3 text-[#4A4A4A]">Loading your wishlist...</span>
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Header */}
      <section className="px-6 py-4">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-[#553B08] mb-2">📚 My Wishlist</h1>
            <p className="text-[#6B6B6B] text-sm">Books you want to read later</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowStatistics(!showStatistics)}
              className="px-4 py-2 bg-[#ECE5D4] text-[#553B08] border border-[#553B08]/20 rounded-md hover:bg-[#553B08]/10 transition-colors duration-200 text-sm"
            >
              {showStatistics ? 'Hide Stats' : 'Show Stats'}
            </button>
            {wishlist.length > 0 && (
              <button
                onClick={handleClearWishlist}
                className="px-4 py-2 bg-red-500/20 text-red-600 border border-red-500/30 rounded-md hover:bg-red-500/30 transition-colors duration-200 text-sm"
              >
                Clear All
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Statistics */}
      {showStatistics && statistics && (
        <section className="px-6 py-4">
          <div className="bg-[#ECE5D4] rounded-md p-6 mb-6">
            <h2 className="text-lg font-semibold text-[#553B08] mb-4">Wishlist Statistics</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-[#553B08] mb-2">{statistics.total_count}</div>
                <div className="text-[#6B6B6B] text-sm">Total Books</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-[#553B08] mb-2">{statistics.genre_distribution.length}</div>
                <div className="text-[#6B6B6B] text-sm">Different Genres</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-[#553B08] mb-2">{statistics.recent_additions.length}</div>
                <div className="text-[#6B6B6B] text-sm">Recent Additions</div>
              </div>
            </div>

            {/* Genre Distribution */}
            {statistics.genre_distribution.length > 0 && (
              <div className="mt-6">
                <h3 className="text-base font-semibold text-[#553B08] mb-3">Top Genres</h3>
                <div className="flex flex-wrap gap-2">
                  {statistics.genre_distribution.slice(0, 10).map((genre, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-[#553B08]/20 text-[#553B08] rounded-full text-sm"
                    >
                      {genre.genre} ({genre.count})
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Empty State */}
      {wishlist.length === 0 && (
        <section className="px-6 py-4">
          <div className="bg-[#ECE5D4] rounded-md p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-[#6B6B6B] mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
            <h3 className="text-lg font-semibold text-[#553B08] mb-2">Your wishlist is empty</h3>
            <p className="text-[#6B6B6B] mb-4 text-sm">Start adding books you want to read later!</p>
            <p className="text-[#6B6B6B] text-xs">Use the star icon when browsing books to add them to your wishlist.</p>
          </div>
        </section>
      )}

      {/* Wishlist Items */}
      {wishlist.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {wishlist.map((book, index) => (
            <div key={`${book.book_name}-${index}`} className="glass-card rounded-2xl p-6 hover:shadow-xl transition-all duration-300">
              <div className="flex flex-col h-full">
                {/* Book Info */}
                <div className="mb-4">
                  <h3 className="text-base font-semibold text-[#231F20] leading-tight mb-2 line-clamp-2">{book.book_name}</h3>
                  <p className="text-sm text-[#553B08] mb-3 line-clamp-1">by {book.book_author || 'Unknown Author'}</p>
                  <p className="text-xs text-[#6B6B6B] line-clamp-2">{book.book_genres || 'No genres specified'}</p>
                  
                  {/* Added Date */}
                  <div className="flex items-center mt-2 text-xs text-[#6B6B6B]">
                    <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Added {new Date(book.added_at).toLocaleDateString()}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 mt-auto">
                  {/* Like Button */}
                  <button
                    onClick={async () => {
                      try {
                        const token = localStorage.getItem('token');
                        const endpoint = 'like';

                        const response = await axios.post(`http://localhost:5000/api/books/${endpoint}`, {
                          book_name: book.book_name,
                          book_author: book.book_author || '',
                          book_genres: book.book_genres || ''
                        }, {
                          headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                          }
                        });

                        // Refresh wishlist to update the UI
                        loadWishlist();
                      } catch (error) {
                        console.error('Like error:', error);
                      }
                    }}
                    className={`flex-1 flex items-center justify-center px-3 py-2 rounded-lg font-medium transition-all duration-200 ${
                      book.user_interaction === 'like'
                        ? 'bg-green-500/20 text-green-400 border border-green-500'
                        : 'bg-white/10 text-gray-300 border border-white/20 hover:bg-green-500/20 hover:text-green-400 hover:border-green-500'
                    }`}
                  >
                    {false ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                    ) : (
                      <>
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                        </svg>
                        <span>Like</span>
                      </>
                    )}
                  </button>

                  {/* Dislike Button */}
                  <button
                    onClick={async () => {
                      try {
                        const token = localStorage.getItem('token');
                        const endpoint = 'dislike';

                        const response = await axios.post(`http://localhost:5000/api/books/${endpoint}`, {
                          book_name: book.book_name,
                          book_author: book.book_author || '',
                          book_genres: book.book_genres || ''
                        }, {
                          headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                          }
                        });

                        // Refresh wishlist to update the UI
                        loadWishlist();
                      } catch (error) {
                        console.error('Dislike error:', error);
                      }
                    }}
                    className={`flex-1 flex items-center justify-center px-3 py-2 rounded-lg font-medium transition-all duration-200 ${
                      book.user_interaction === 'dislike'
                        ? 'bg-red-500/20 text-red-400 border border-red-500'
                        : 'bg-white/10 text-gray-300 border border-white/20 hover:bg-red-500/20 hover:text-red-400 hover:border-red-500'
                    }`}
                  >
                    {false ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                    ) : (
                      <>
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018c.163 0 .326.02.485.06L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                        </svg>
                        <span>Pass</span>
                      </>
                    )}
                  </button>

                  {/* Remove from Wishlist Button */}
                  <button
                    onClick={() => handleRemoveFromWishlist(book)}
                    disabled={removeLoading[`${book.book_name}-${book.book_author}`]}
                    className="flex items-center justify-center px-3 py-2 rounded-lg font-medium transition-all duration-200 bg-purple-500/20 text-purple-400 border border-purple-500 hover:bg-purple-500/30 disabled:opacity-50"
                    title="Remove from wishlist"
                  >
                    {removeLoading[`${book.book_name}-${book.book_author}`] ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                    ) : (
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                      </svg>
                    )}
                  </button>
                </div>

                {/* User Interaction Indicator */}
                {book.user_interaction && book.user_interaction !== 'rating' && (
                  <div className="flex items-center justify-center mt-3">
                    <span className={`text-xs px-3 py-1 rounded-full ${
                      book.user_interaction === 'like' 
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      You {book.user_interaction}d this book
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Wishlist;
