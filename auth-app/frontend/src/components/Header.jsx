import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const Header = ({ onSearchSubmit, onNavigate, currentPage }) => {
  const { user, logout } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      onSearchSubmit(searchTerm);
      onNavigate('search');
    }
  };

  const handleLogout = () => {
    logout();
  };

  return (
    <header className="goodreads-card-white rounded-2xl p-6 mb-12 animate-fadeIn sticky top-4 z-50 shadow-lg">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-6 lg:space-y-0">
        {/* Logo and Navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center space-y-4 sm:space-y-0 sm:space-x-8">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-brand-primary hover:bg-brand-hover rounded-full flex items-center justify-center transition-colors duration-200">
              <span className="text-white font-bold text-xl leading-none" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
                {user?.username?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h1
                className="text-xl font-bold text-brand-primary cursor-pointer hover:text-brand-hover transition-colors"
                onClick={() => onNavigate('home')}
              >
                Holmes
              </h1>
              <p className="text-goodreads-text/80 text-sm">Welcome, {user?.username}!</p>
            </div>
          </div>

          {/* Navigation Menu */}
          <nav className="hidden md:flex space-x-4">
            <button
              onClick={() => onNavigate('home')}
              className={`nav-link px-4 py-2 rounded-lg transition-all duration-200 ${
                currentPage === 'home'
                  ? 'active bg-goodreads-cream text-brand-hover border border-brand-primary'
                  : ''
              }`}
            >
              Home
            </button>
            <button
              onClick={() => onNavigate('wishlist')}
              className={`nav-link px-4 py-2 rounded-lg transition-all duration-200 flex items-center ${
                currentPage === 'wishlist'
                  ? 'active bg-goodreads-cream text-brand-hover border border-brand-primary'
                  : ''
              }`}
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              Wishlist
            </button>
            <button
              onClick={() => onNavigate('profile')}
              className={`nav-link px-4 py-2 rounded-lg transition-all duration-200 ${
                currentPage === 'profile'
                  ? 'active bg-goodreads-cream text-brand-hover border border-brand-primary'
                  : ''
              }`}
            >
              My Profile
            </button>
          </nav>
        </div>

        {/* Search Bar */}
        <div className="flex-1 max-w-md mx-0 lg:mx-8 order-3 lg:order-2">
          <form onSubmit={handleSearchSubmit} className="relative flex">
            <div className="relative flex-1">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search and discover..."
                className="search-bar rounded-l-lg pl-10 pr-4"
              />
              <svg className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-goodreads-border" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <button
              type="submit"
              className="btn-primary rounded-l-none rounded-r-lg px-6 py-2 hover:bg-brand-hover transition-all duration-300"
            >
              Search
            </button>
          </form>
        </div>

        {/* User Actions */}
        <div className="flex items-center space-x-4">
          <button
            onClick={handleLogout}
            className="btn-primary px-5 py-2 flex items-center hover:bg-brand-hover transition-all duration-300"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Logout
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;