import React, { useState } from 'react';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import { RecommendationCacheProvider } from './context/RecommendationCacheContext';
import Login from './components/Login';
import Register from './components/Register';
import Dashboard from './components/Dashboard';

const AuthPage = () => {
  const [isLogin, setIsLogin] = useState(true);

  const toggleMode = () => {
    setIsLogin(!isLogin);
  };

  return (
    <div className="auth-container">
      {/* Floating background shapes */}
      <div className="floating-shapes">
        <div className="shape"></div>
        <div className="shape"></div>
        <div className="shape"></div>
      </div>

      {/* Main content */}
      <div className="relative z-10 w-full max-w-md">
        {isLogin ? (
          <Login onToggleMode={toggleMode} />
        ) : (
          <Register onToggleMode={toggleMode} />
        )}
      </div>
    </div>
  );
};

const AppContent = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card rounded-2xl p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-600 mx-auto mb-4"></div>
          <p className="text-stone-800">Loading<span className="loading-dots">...</span></p>
        </div>
      </div>
    );
  }

  return user ? <Dashboard /> : <AuthPage />;
};

function App() {
  return (
    <AuthProvider>
      <RecommendationCacheProvider>
        <div className="App">
          <AppContent />
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: 'rgba(255, 255, 255, 0.95)',
                color: '#44403c',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(168, 162, 158, 0.3)',
              },
              success: {
                iconTheme: {
                  primary: '#059669',
                  secondary: '#fff',
                },
              },
              error: {
                iconTheme: {
                  primary: '#DC2626',
                  secondary: '#fff',
                },
              },
            }}
          />
        </div>
      </RecommendationCacheProvider>
    </AuthProvider>
  );
}

export default App;
