import React from 'react';
import RecommendedSection from './RecommendedSection';
import BecauseYouLiked from './BecauseYouLiked';
import BooksAsThese from './BooksAsThese';
import BasedOnLikes from './BasedOnLikes';
import BestFromAuthor from './BestFromAuthor';
import ContinueReading from './ContinueReading';
import GenreDashboards from './GenreDashboards';
import PopularBooks from './PopularBooks';

const HomePage = () => {
  return (
    <div className="animate-slideUp">
      {/* Netflix-style Hero Section - Minimal and Clean */}
      <section className="px-6 py-8 mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-[#553B08] mb-2">
              Discover Your Next Great Find
            </h1>
            <p className="text-[#4A4A4A] text-base">
              Intelligent discoveries powered by Holmes AI
            </p>
          </div>
          <div className="hidden md:block">
            <div className="w-16 h-16 bg-gradient-to-br from-[#553B08] to-[#75420E] rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
          </div>
        </div>
      </section>

      {/* Netflix-style Content Sections - All using consistent w-64 cards */}
      <div className="space-y-8">
        {/* 1. Recommended for You */}
        <RecommendedSection />
        
        {/* 2. Because You Liked */}
        <BecauseYouLiked />
        
        {/* 2b. Books Such As These (Alternative Because You Liked) */}
        <BooksAsThese />
        
        {/* 3. Based on Your Reading Preferences */}
        <BasedOnLikes />
        
        {/* 4. Best From The Author */}
        <BestFromAuthor />
        
        {/* 5. Continue Reading */}
        <ContinueReading />
        
        {/* 6. Popular in Genres */}
        <GenreDashboards />
        
        {/* 7. Popular Books */}
        <PopularBooks />
      </div>
    </div>
  );
};

export default HomePage;