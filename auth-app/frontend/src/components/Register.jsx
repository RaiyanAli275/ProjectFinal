import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const Register = ({ onToggleMode }) => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [focusedField, setFocusedField] = useState({});
  const [errors, setErrors] = useState({});
  const { register, loading } = useAuth();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });

    // Clear errors as user types
    if (errors[name]) {
      setErrors({
        ...errors,
        [name]: ''
      });
    }

    // Real-time password confirmation validation
    if (name === 'confirmPassword' || (name === 'password' && formData.confirmPassword)) {
      const password = name === 'password' ? value : formData.password;
      const confirmPassword = name === 'confirmPassword' ? value : formData.confirmPassword;
      
      if (confirmPassword && password !== confirmPassword) {
        setErrors(prev => ({
          ...prev,
          confirmPassword: 'Passwords do not match'
        }));
      } else {
        setErrors(prev => ({
          ...prev,
          confirmPassword: ''
        }));
      }
    }
  };

  const handleFocus = (field) => {
    setFocusedField({ ...focusedField, [field]: true });
  };

  const handleBlur = (field, value) => {
    if (!value) {
      setFocusedField({ ...focusedField, [field]: false });
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters';
    }

    if (!formData.email.includes('@')) {
      newErrors.email = 'Please enter a valid email';
    }

    if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }

    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;

    if (!validateForm()) return;

    const result = await register(formData.username, formData.email, formData.password);
    if (result.success) {
      // AuthContext will handle navigation via user state change
    }
  };

  return (
    <div className="glass-card rounded-2xl p-8 w-full max-w-md animate-slideUp">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-amber-700 to-amber-800 rounded-full mb-4 animate-glow">
          <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
          </svg>
        </div>
        <h2 className="text-3xl font-bold text-stone-800">
          Create Account
        </h2>
        <p className="text-stone-600 mt-2">Join our community today</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="relative">
          <input
            type="text"
            name="username"
            value={formData.username}
            onChange={handleChange}
            onFocus={() => handleFocus('username')}
            onBlur={(e) => handleBlur('username', e.target.value)}
            className={`glass-input w-full px-4 py-3 rounded-lg text-stone-800 placeholder-transparent focus:outline-none ${errors.username ? 'border-red-500' : ''}`}
            placeholder="Username"
            required
          />
          <label className={`form-floating-label ${focusedField.username || formData.username ? 'active' : ''}`}>
            Username
          </label>
          {errors.username && (
            <p className="text-red-500 text-sm mt-1">{errors.username}</p>
          )}
        </div>

        <div className="relative">
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            onFocus={() => handleFocus('email')}
            onBlur={(e) => handleBlur('email', e.target.value)}
            className={`glass-input w-full px-4 py-3 rounded-lg text-stone-800 placeholder-transparent focus:outline-none ${errors.email ? 'border-red-500' : ''}`}
            placeholder="Email"
            required
          />
          <label className={`form-floating-label ${focusedField.email || formData.email ? 'active' : ''}`}>
            Email
          </label>
          {errors.email && (
            <p className="text-red-500 text-sm mt-1">{errors.email}</p>
          )}
        </div>

        <div className="relative">
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            onFocus={() => handleFocus('password')}
            onBlur={(e) => handleBlur('password', e.target.value)}
            className={`glass-input w-full px-4 py-3 rounded-lg text-stone-800 placeholder-transparent focus:outline-none ${errors.password ? 'border-red-500' : ''}`}
            placeholder="Password"
            required
          />
          <label className={`form-floating-label ${focusedField.password || formData.password ? 'active' : ''}`}>
            Password
          </label>
          {errors.password && (
            <p className="text-red-500 text-sm mt-1">{errors.password}</p>
          )}
        </div>

        <div className="relative">
          <input
            type="password"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            onFocus={() => handleFocus('confirmPassword')}
            onBlur={(e) => handleBlur('confirmPassword', e.target.value)}
            className={`glass-input w-full px-4 py-3 rounded-lg text-stone-800 placeholder-transparent focus:outline-none ${errors.confirmPassword ? 'border-red-500' : ''}`}
            placeholder="Confirm Password"
            required
          />
          <label className={`form-floating-label ${focusedField.confirmPassword || formData.confirmPassword ? 'active' : ''}`}>
            Confirm Password
          </label>
          {errors.confirmPassword && (
            <p className="text-red-500 text-sm mt-1">{errors.confirmPassword}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="glass-button w-full py-3 px-4 rounded-lg text-white font-semibold focus:outline-none focus:ring-2 focus:ring-amber-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Creating account<span className="loading-dots">...</span>
            </span>
          ) : (
            'Create Account'
          )}
        </button>
      </form>

      <div className="mt-8 text-center">
        <p className="text-stone-600">
          Already have an account?{' '}
          <button
            onClick={onToggleMode}
            className="text-amber-700 hover:text-amber-800 font-semibold transition-colors duration-200 focus:outline-none focus:underline"
          >
            Sign in
          </button>
        </p>
      </div>

      <div className="mt-6 flex items-center justify-center">
        <div className="flex space-x-4">
          <div className="w-2 h-2 bg-amber-600 rounded-full animate-pulse"></div>
          <div className="w-2 h-2 bg-amber-700 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
          <div className="w-2 h-2 bg-amber-800 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
        </div>
      </div>
    </div>
  );
};

export default Register;
