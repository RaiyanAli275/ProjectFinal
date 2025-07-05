import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

const UserPreferences = () => {
  const { user, token } = useAuth();
  const [likedBooks, setLikedBooks] = useState([]);
  const [dislikedBooks, setDislikedBooks] = useState([]);
  const [favoriteGenres, setFavoriteGenres] = useState([]);
  const [favoriteAuthors, setFavoriteAuthors] = useState([]);
  const [stats, setStats] = useState({ likes: 0, dislikes: 0, totalInteractions: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchUserData();
  }, []);

  const fetchUserData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('🔍 Fetching user interactions...', {
        url: 'http://localhost:5000/api/books/user-interactions',
        hasToken: !!token
      });
      
      // Fetch user interactions
      const interactionsResponse = await fetch('http://localhost:5000/api/books/user-interactions', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      console.log('📡 API Response:', {
        status: interactionsResponse.status,
        statusText: interactionsResponse.statusText,
        ok: interactionsResponse.ok
      });

      if (interactionsResponse.ok) {
        const interactionsData = await interactionsResponse.json();
        console.log('✅ Data received:', interactionsData);
        
        // The response structure is { interactions: [...], count: number }
        const allInteractions = interactionsData.interactions || [];
        
        // Separate liked and disliked books
        const liked = allInteractions.filter(book => book.action === 'like');
        const disliked = allInteractions.filter(book => book.action === 'dislike');
        
        console.log('📊 Processing results:', {
          totalInteractions: allInteractions.length,
          liked: liked.length,
          disliked: disliked.length
        });
        
        setLikedBooks(liked);
        setDislikedBooks(disliked);
        setStats({
          likes: liked.length,
          dislikes: disliked.length,
          totalInteractions: liked.length + disliked.length
        });

        // Extract favorite genres and authors
        const genreCount = {};
        const authorCount = {};
        
        liked.forEach(book => {
          // Count genres with proper type checking
          if (book.book_genres) {
            let genres = [];
            
            if (typeof book.book_genres === 'string') {
              // If it's a string, split by comma
              genres = book.book_genres.split(',').map(g => g.trim());
            } else if (Array.isArray(book.book_genres)) {
              // If it's already an array, use it directly
              genres = book.book_genres.map(g => String(g).trim());
            } else {
              // If it's something else, convert to string and split
              genres = String(book.book_genres).split(',').map(g => g.trim());
            }
            
            genres.forEach(genre => {
              if (genre && genre !== 'null' && genre !== 'undefined') {
                genreCount[genre] = (genreCount[genre] || 0) + 1;
              }
            });
          }
          
          // Count authors with proper type checking
          if (book.book_author && book.book_author !== 'null' && book.book_author !== 'undefined') {
            const authorName = String(book.book_author).trim();
            if (authorName) {
              authorCount[authorName] = (authorCount[authorName] || 0) + 1;
            }
          }
        });

        // Sort and get top genres/authors
        const topGenres = Object.entries(genreCount)
          .sort(([,a], [,b]) => b - a)
          .slice(0, 10)
          .map(([genre, count]) => ({ genre, count }));
          
        const topAuthors = Object.entries(authorCount)
          .sort(([,a], [,b]) => b - a)
          .slice(0, 8)
          .map(([author, count]) => ({ author, count }));

        setFavoriteGenres(topGenres);
        setFavoriteAuthors(topAuthors);
      } else {
        const errorData = await interactionsResponse.text();
        console.error('❌ API Error:', {
          status: interactionsResponse.status,
          statusText: interactionsResponse.statusText,
          errorData
        });
        setError(`Failed to load user data: ${interactionsResponse.status} ${interactionsResponse.statusText}`);
      }
    } catch (err) {
      console.error('💥 Network error:', err);
      setError(`Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveInteraction = async (book) => {
    try {
      const response = await fetch('http://localhost:5000/api/books/remove-interaction', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          book_name: book.book_name,
          book_author: book.book_author || '',
          book_genres: book.book_genres || '',
          action: book.action // Pass whether it was liked or disliked
        })
      });

      if (response.ok) {
        // Update local state to remove the book from liked or disliked list
        setLikedBooks(prev => prev.filter(b => b.book_name !== book.book_name));
        setDislikedBooks(prev => prev.filter(b => b.book_name !== book.book_name));
        
        // Update stats
        setStats(prev => ({
          ...prev,
          likes: book.action === 'like' ? prev.likes - 1 : prev.likes,
          dislikes: book.action === 'dislike' ? prev.dislikes - 1 : prev.dislikes,
          totalInteractions: prev.totalInteractions - 1
        }));
      }
    } catch (error) {
      console.error('Error removing interaction:', error);
    }
  };

  const BookCard = ({ book, isLiked = true }) => (
    <div className="w-72 h-56 bg-[#ECE5D4] rounded-md p-6 hover:scale-105 transition-transform duration-200 group relative flex-shrink-0 flex flex-col">
      {/* Remove interaction button */}
      <button
        onClick={() => handleRemoveInteraction(book)}
        className="absolute top-2 right-2 p-2 rounded-full bg-red-500/20 text-red-600 hover:bg-red-500/30 transition-colors"
        title="Remove interaction"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <div className="pr-8 mb-4 flex-grow">
        <h4 className="text-base font-semibold text-[#231F20] leading-tight mb-2 line-clamp-2" title={book.book_name}>
          {book.book_name}
        </h4>
        <p className="text-sm text-[#553B08] mb-3 line-clamp-1" title={book.book_author}>
          {book.book_author || 'Unknown Author'}
        </p>
        {book.book_genres && (
          <p className="text-xs text-[#6B6B6B] line-clamp-2">
            {book.book_genres}
          </p>
        )}
      </div>
      
      <div className="flex items-center text-xs">
        <div className={`w-3 h-3 rounded-full mr-2 ${isLiked ? 'bg-green-500' : 'bg-red-500'}`}></div>
        <span className={`font-medium ${isLiked ? 'text-green-600' : 'text-red-600'}`}>
          {isLiked ? 'Liked' : 'Disliked'}
        </span>
        {book.timestamp && (
          <span className="text-[#6B6B6B] ml-auto">
            {new Date(book.timestamp).toLocaleDateString()}
          </span>
        )}
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="animate-slideUp">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#553B08]"></div>
          <span className="ml-3 text-[#4A4A4A]">Loading your reading profile...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="animate-slideUp">
        <div className="bg-[#ECE5D4] rounded-md p-8 text-center">
          <h2 className="text-2xl font-semibold text-[#553B08] mb-4">Error Loading Profile</h2>
          <p className="text-[#4A4A4A] mb-4">{error}</p>
          <button
            onClick={fetchUserData}
            className="px-6 py-2 bg-[#553B08] text-white rounded-md hover:bg-[#75420E] transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-slideUp">
      {/* Header */}
      <section className="px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-[#553B08] mb-2">
              📚 Your Reading Profile
            </h1>
            <p className="text-[#4A4A4A] text-base">
              Discover your reading preferences and history
            </p>
          </div>
          <div className="hidden md:block">
            <div className="w-16 h-16 bg-gradient-to-br from-[#553B08] to-[#75420E] rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
          </div>
        </div>
      </section>

      {/* User Info & Stats */}
      <section className="px-6 py-4">
        <div className="bg-[#ECE5D4] rounded-md p-6">
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-semibold text-[#553B08] mb-4">Profile Information</h3>
              <div className="space-y-2">
                <p className="text-[#4A4A4A]"><span className="font-medium">Username:</span> {user?.username}</p>
                <p className="text-[#4A4A4A]"><span className="font-medium">Email:</span> {user?.email}</p>
              </div>
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-[#553B08] mb-4">Reading Statistics</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center bg-green-500/20 rounded-md p-3">
                  <p className="text-2xl font-bold text-green-600">{stats.likes}</p>
                  <p className="text-sm text-green-600">Liked</p>
                </div>
                <div className="text-center bg-red-500/20 rounded-md p-3">
                  <p className="text-2xl font-bold text-red-600">{stats.dislikes}</p>
                  <p className="text-sm text-red-600">Disliked</p>
                </div>
                <div className="text-center bg-[#553B08]/20 rounded-md p-3">
                  <p className="text-2xl font-bold text-[#553B08]">{stats.totalInteractions}</p>
                  <p className="text-sm text-[#553B08]">Total</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Liked Books */}
      {likedBooks.length > 0 && (
        <section className="px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-[#553B08]">💚 Books You Loved</h2>
            <span className="text-sm text-[#553B08] bg-[#ECE5D4] px-2 py-1 rounded-md">
              {likedBooks.length} books
            </span>
          </div>
          <div className="flex overflow-x-auto space-x-4 scrollbar-hide">
            {likedBooks.map((book, index) => (
              <BookCard key={index} book={book} isLiked={true} />
            ))}
          </div>
        </section>
      )}

      {/* Disliked Books */}
      {dislikedBooks.length > 0 && (
        <section className="px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-[#553B08]">👎 Books You Passed On</h2>
            <span className="text-sm text-[#553B08] bg-[#ECE5D4] px-2 py-1 rounded-md">
              {dislikedBooks.length} books
            </span>
          </div>
          <div className="flex overflow-x-auto space-x-4 scrollbar-hide">
            {dislikedBooks.map((book, index) => (
              <BookCard key={index} book={book} isLiked={false} />
            ))}
          </div>
        </section>
      )}

      {/* Favorite Genres */}
      {favoriteGenres.length > 0 && (
        <section className="px-6 py-4">
          <h2 className="text-lg font-semibold text-[#553B08] mb-4">🎭 Your Favorite Genres</h2>
          <div className="flex flex-wrap gap-3">
            {favoriteGenres.map((genre, index) => (
              <span
                key={index}
                className="px-4 py-2 bg-[#ECE5D4] text-[#553B08] rounded-full text-sm font-medium hover:bg-[#F3EDE3] transition-colors"
              >
                {genre.genre} ({genre.count})
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Favorite Authors */}
      {favoriteAuthors.length > 0 && (
        <section className="px-6 py-4">
          <h2 className="text-lg font-semibold text-[#553B08] mb-4">👨‍🎨 Your Favorite Authors</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {favoriteAuthors.map((author, index) => (
              <div key={index} className="bg-[#ECE5D4] rounded-md p-4 hover:bg-[#F3EDE3] transition-colors">
                <h3 className="font-semibold text-[#553B08] mb-1">{author.author}</h3>
                <p className="text-sm text-[#6B6B6B]">{author.count} books liked</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Empty State */}
      {stats.totalInteractions === 0 && (
        <section className="px-6 py-4">
          <div className="bg-[#ECE5D4] rounded-md p-8 text-center">
            <svg className="w-16 h-16 text-[#6B6B6B] mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            <h2 className="text-xl font-semibold text-[#553B08] mb-2">Start Building Your Reading Profile</h2>
            <p className="text-[#4A4A4A] mb-4">Like and dislike books to see your personalized preferences!</p>
          </div>
        </section>
      )}
    </div>
  );
};

export default UserPreferences;
