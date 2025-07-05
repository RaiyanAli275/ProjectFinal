import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import Header from './Header';
import HomePage from './HomePage';
import SearchResultsPage from './SearchResultsPage';
import UserPreferences from './UserPreferences';
import Wishlist from './Wishlist';

const Dashboard = () => {
  const { user } = useAuth();
  const [currentTime, setCurrentTime] = useState(new Date());
  const [currentPage, setCurrentPage] = useState('home');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const handleSearchSubmit = (term) => {
    setSearchTerm(term);
    setCurrentPage('search');
  };

  const handleNavigate = (page) => {
    setCurrentPage(page);
    if (page !== 'search') {
      setSearchTerm('');
    }
  };

  const formatDate = (date) => {
    return new Intl.DateTimeFormat('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }).format(date);
  };

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'home':
        return <HomePage />;
      case 'search':
        return <SearchResultsPage searchTerm={searchTerm} onNavigate={handleNavigate} />;
      case 'wishlist':
        return <Wishlist />;
      case 'profile':
        return <UserPreferences />;
      default:
        return <HomePage />;
    }
  };

  return (
    <div className="min-h-screen">
      {/* Floating background shapes */}
      <div className="floating-shapes">
        <div className="shape"></div>
        <div className="shape"></div>
        <div className="shape"></div>
      </div>

      <div className="relative z-10 container mx-auto px-4 py-8">
        {/* Header with Search */}
        <Header
          onSearchSubmit={handleSearchSubmit}
          onNavigate={handleNavigate}
          currentPage={currentPage}
        />

        {/* Page Content */}
        {renderCurrentPage()}
      </div>
    </div>
  );
};

export default Dashboard;
