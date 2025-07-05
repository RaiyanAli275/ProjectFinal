import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const Login = ({ onToggleMode }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [focusedField, setFocusedField] = useState({});
  const { login, loading } = useAuth();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleFocus = (field) => {
    setFocusedField({ ...focusedField, [field]: true });
  };

  const handleBlur = (field, value) => {
    if (!value) {
      setFocusedField({ ...focusedField, [field]: false });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;

    const result = await login(formData.email, formData.password);
    if (result.success) {
      // AuthContext will handle navigation via user state change
    }
  };

  return (
    <div className="goodreads-card-white rounded-2xl p-8 w-full max-w-md animate-slideUp">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-brand-primary to-brand-hover rounded-full mb-4 animate-glow">
          <svg className="w-8 h-8 text-goodreads-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
          </svg>
        </div>
        <h2 className="book-title text-3xl mb-2">
          Welcome Back
        </h2>
        <p className="book-description mt-2">Sign in to your account</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="relative">
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            onFocus={() => handleFocus('email')}
            onBlur={(e) => handleBlur('email', e.target.value)}
            className="input-goodreads w-full placeholder-transparent focus:outline-none"
            placeholder="Email"
            required
          />
          <label className={`form-floating-label ${focusedField.email || formData.email ? 'active' : ''}`}>
            Email
          </label>
        </div>

        <div className="relative">
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            onFocus={() => handleFocus('password')}
            onBlur={(e) => handleBlur('password', e.target.value)}
            className="input-goodreads w-full placeholder-transparent focus:outline-none"
            placeholder="Password"
            required
          />
          <label className={`form-floating-label ${focusedField.password || formData.password ? 'active' : ''}`}>
            Password
          </label>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full focus:outline-none focus:ring-2 focus:ring-brand-primary/50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-goodreads-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Signing in<span className="loading-dots">...</span>
            </span>
          ) : (
            'Sign In'
          )}
        </button>
      </form>

      <div className="mt-8 text-center">
        <p className="book-description">
          Don't have an account?{' '}
          <button
            onClick={onToggleMode}
            className="author-name font-semibold transition-colors duration-200 focus:outline-none focus:underline"
          >
            Sign up
          </button>
        </p>
      </div>

      <div className="mt-6 flex items-center justify-center">
        <div className="flex space-x-4">
          <div className="w-2 h-2 bg-brand-primary rounded-full animate-pulse"></div>
          <div className="w-2 h-2 bg-brand-hover rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
          <div className="w-2 h-2 bg-brand-primary rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
        </div>
      </div>
    </div>
  );
};

export default Login;
