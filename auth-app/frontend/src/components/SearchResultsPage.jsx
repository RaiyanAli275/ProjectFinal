import React, { useState, useEffect } from 'react';
import axios from 'axios';

const SearchResultsPage = ({ searchTerm, onNavigate }) => {
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [interactionLoading, setInteractionLoading] = useState({});
  const [sortBy, setSortBy] = useState('relevance');
  const [filterBy, setFilterBy] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  useEffect(() => {
    if (searchTerm) {
      performSearch(searchTerm);
    }
  }, [searchTerm, sortBy, filterBy]);

  const performSearch = async (term, page = 1, isLoadMore = false) => {
    if (term.trim().length < 2) {
      setSearchResults([]);
      return;
    }

    if (isLoadMore) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }

    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`http://localhost:5000/api/books/search?q=${encodeURIComponent(term)}&page=${page}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      let newResults = response.data.books || [];

      // Apply sorting
      newResults = sortResults(newResults, sortBy);

      // Apply filtering
      newResults = filterResults(newResults, filterBy);

      // Update search results
      setSearchResults(prev => isLoadMore ? [...prev, ...newResults] : newResults);
      setHasMore(response.data.has_more);
      setCurrentPage(page);

    } catch (error) {
      console.error('Search error:', error);
      if (!isLoadMore) {
        setSearchResults([]);
      }
    } finally {
      if (isLoadMore) {
        setLoadingMore(false);
      } else {
        setLoading(false);
      }
    }
  };

  const handleLoadMore = () => {
    performSearch(searchTerm, currentPage + 1, true);
  };

  const sortResults = (results, sortBy) => {
    switch (sortBy) {
      case 'rating':
        return [...results].sort((a, b) => (b.star_rating || 0) - (a.star_rating || 0));
      case 'popularity':
        return [...results].sort((a, b) => (b.num_ratings || 0) - (a.num_ratings || 0));
      case 'title':
        return [...results].sort((a, b) => a.name.localeCompare(b.name));
      case 'author':
        return [...results].sort((a, b) => (a.author || '').localeCompare(b.author || ''));
      default:
        return results;
    }
  };

  const filterResults = (results, filterBy) => {
    switch (filterBy) {
      case 'liked':
        return results.filter(book => book.user_interaction === 'like');
      case 'rated':
        return results.filter(book => book.user_rating > 0);
      case 'unrated':
        return results.filter(book => !book.user_rating);
      default:
        return results;
    }
  };

  const handleInteraction = async (book, action) => {
    const bookKey = `${book.name}-${book.author}`;
    setInteractionLoading(prev => ({ ...prev, [bookKey]: true }));

    try {
      const token = localStorage.getItem('token');
      const endpoint = action === 'remove' 
        ? 'http://localhost:5000/api/books/remove-interaction'
        : `http://localhost:5000/api/books/${action}`;

      const payload = {
        book_name: book.name,
        book_author: book.author || 'Unknown',
        book_genres: book.genres || ''
      };

      const response = await axios.post(endpoint, payload, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      // Update the book in search results
      setSearchResults(prevResults => 
        prevResults.map(b => 
          b.name === book.name && b.author === book.author
            ? { 
                ...b, 
                user_interaction: response.data.action,
                likes: response.data.likes,
                dislikes: response.data.dislikes
              }
            : b
        )
      );
    } catch (error) {
      console.error('Interaction error:', error);
    } finally {
      setInteractionLoading(prev => ({ ...prev, [bookKey]: false }));
    }
  };

  // Handle wishlist toggle
  const handleWishlistToggle = async (book) => {
    const bookKey = `wishlist-${book.name}-${book.author}`;
    setInteractionLoading(prev => ({ ...prev, [bookKey]: true }));

    try {
      const token = localStorage.getItem('token');
      const payload = {
        book_name: book.name,
        book_author: book.author || 'Unknown',
        book_genres: book.genres || ''
      };

      console.log('🔄 Toggling wishlist for:', book.name);
      console.log('📤 Payload:', payload);

      const response = await axios.post('http://localhost:5000/api/wishlist/toggle', payload, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      console.log('✅ Wishlist toggle response:', response.data);

      // Update the book in search results
      setSearchResults(prevResults =>
        prevResults.map(b =>
          b.name === book.name && b.author === book.author
            ? {
                ...b,
                in_wishlist: response.data.in_wishlist
              }
            : b
        )
      );

      console.log('📋 Updated search results for:', book.name, 'New wishlist status:', response.data.in_wishlist);
    } catch (error) {
      console.error('❌ Wishlist error:', error);
      console.error('📄 Error response:', error.response?.data);
    } finally {
      setInteractionLoading(prev => ({ ...prev, [bookKey]: false }));
    }
  };

  return (
    <div className="animate-slideUp">
      {/* Header */}
      <section className="px-6 py-4">
        <div className="bg-[#ECE5D4] rounded-md p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => onNavigate('home')}
                className="flex items-center text-[#6B6B6B] hover:text-[#553B08] transition-colors"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to Home
              </button>
              <div className="h-6 border-l border-[#6B6B6B]"></div>
              <h1 className="text-xl font-semibold text-[#553B08]">🔍 Search Results</h1>
            </div>
            <div className="text-[#6B6B6B] text-sm">
              {loading ? 'Searching...' : `${searchResults.length} results for "${searchTerm}"`}
            </div>
          </div>

          {/* Search Controls */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center space-x-2">
              <label className="text-[#6B6B6B] text-sm">Sort by:</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-white border border-[#553B08]/20 rounded-md px-3 py-1 text-[#231F20] text-sm focus:outline-none focus:ring-2 focus:ring-[#553B08]"
              >
                <option value="relevance">Relevance</option>
                <option value="rating">Rating</option>
                <option value="popularity">Popularity</option>
                <option value="title">Title</option>
                <option value="author">Author</option>
              </select>
            </div>
            
            <div className="flex items-center space-x-2">
              <label className="text-[#6B6B6B] text-sm">Filter by:</label>
              <select
                value={filterBy}
                onChange={(e) => setFilterBy(e.target.value)}
                className="bg-white border border-[#553B08]/20 rounded-md px-3 py-1 text-[#231F20] text-sm focus:outline-none focus:ring-2 focus:ring-[#553B08]"
              >
                <option value="all">All Books</option>
                <option value="liked">Liked Books</option>
                <option value="rated">Rated Books</option>
                <option value="unrated">Unrated Books</option>
              </select>
            </div>
          </div>
        </div>
      </section>

      {/* Loading State */}
      {loading && (
        <section className="px-6 py-4">
          <div className="flex justify-center items-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#553B08]"></div>
            <span className="ml-3 text-[#4A4A4A]">Searching for books...</span>
          </div>
        </section>
      )}

      {/* No Results */}
      {!loading && searchTerm && searchResults.length === 0 && (
        <section className="px-6 py-4">
          <div className="bg-[#ECE5D4] rounded-md p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-[#6B6B6B] mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 20h.01M12 4h.01M20 12h.01M4 12h.01M16.364 7.636a4 4 0 00-5.656 0M7.636 16.364a4 4 0 005.656 0" />
            </svg>
            <h3 className="text-lg font-semibold text-[#553B08] mb-2">No books found</h3>
            <p className="text-[#6B6B6B] text-base mb-4">No books found for "{searchTerm}"</p>
            <p className="text-[#6B6B6B] text-sm mb-6">Try adjusting your search terms or filters</p>
            <button
              onClick={() => onNavigate('home')}
              className="bg-[#553B08] hover:bg-[#553B08]/90 text-white px-6 py-2 rounded-md transition-colors text-sm"
            >
              Browse Recommendations
            </button>
          </div>
        </section>
      )}

      {/* Search Results */}
      {searchResults.length > 0 && (
        <section className="px-6 py-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {searchResults.map((book, index) => (
              <div key={`${book.name}-${book.author}-${index}`} className="bg-[#ECE5D4] rounded-md p-6 hover:scale-105 transition-transform duration-200 group relative flex flex-col h-64">
                {/* Wishlist Star Button - Top Right Corner */}
                <button
                  onClick={() => handleWishlistToggle(book)}
                  disabled={interactionLoading[`wishlist-${book.name}-${book.author}`]}
                  className={`absolute top-2 right-2 p-1.5 rounded-full transition-all duration-200 ${
                    book.in_wishlist
                      ? 'bg-yellow-500/30 text-yellow-600'
                      : 'bg-[#553B08]/20 text-[#553B08] hover:bg-yellow-500/30 hover:text-yellow-600'
                  } disabled:opacity-50`}
                  title={book.in_wishlist ? 'Remove from wishlist' : 'Add to wishlist'}
                >
                  {interactionLoading[`wishlist-${book.name}-${book.author}`] ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                  ) : (
                    <svg className="w-4 h-4" fill={book.in_wishlist ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                    </svg>
                  )}
                </button>

                <div className="pr-8 mb-4 flex-grow">
                  <h4 className="text-base font-semibold text-[#231F20] leading-tight mb-2 line-clamp-2" title={book.name}>
                    {book.name}
                  </h4>
                  <p className="text-sm text-[#553B08] mb-3 line-clamp-1" title={book.author}>
                    {book.author || 'Unknown Author'}
                  </p>
                  {book.genres && (
                    <p className="text-xs text-[#6B6B6B] line-clamp-2">
                      {book.genres}
                    </p>
                  )}
                </div>

                {/* User Interaction Indicator */}
                {book.user_interaction && book.user_interaction !== 'rating' && (
                  <div className="mb-3">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      book.user_interaction === 'like' 
                        ? 'bg-green-500/20 text-green-600' 
                        : 'bg-red-500/20 text-red-600'
                    }`}>
                      You {book.user_interaction}d this
                    </span>
                  </div>
                )}

                {/* Action Buttons */}
                {!book.user_interaction && (
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex space-x-3 mt-auto">
                    <button
                      onClick={() => handleInteraction(book, 'like')}
                      disabled={interactionLoading[`${book.name}-${book.author}`]}
                      className="flex-1 flex items-center justify-center px-3 py-2 rounded-md bg-green-500/20 text-green-600 hover:bg-green-500/30 transition-colors duration-200 text-sm font-medium disabled:opacity-50"
                    >
                      {interactionLoading[`${book.name}-${book.author}`] ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                      ) : (
                        <>
                          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.60L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 712-2h2.5" />
                          </svg>
                          Like
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => handleInteraction(book, 'dislike')}
                      disabled={interactionLoading[`${book.name}-${book.author}`]}
                      className="flex-1 flex items-center justify-center px-3 py-2 rounded-md bg-red-500/20 text-red-600 hover:bg-red-500/30 transition-colors duration-200 text-sm font-medium disabled:opacity-50"
                    >
                      {interactionLoading[`${book.name}-${book.author}`] ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                      ) : (
                        <>
                          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 718.736 3h4.018c.163 0 .326.20.485.60L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 712 2v6a2 2 0 01-2 2h-2.5" />
                          </svg>
                          Pass
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Load More Button */}
          {hasMore && (
            <div className="mt-8 flex justify-center">
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="bg-[#553B08] hover:bg-[#553B08]/90 text-white px-6 py-3 rounded-md transition-colors text-sm flex items-center space-x-2"
              >
                {loadingMore ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Loading more books...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                    <span>Load More Books</span>
                  </>
                )}
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
};

export default SearchResultsPage;
