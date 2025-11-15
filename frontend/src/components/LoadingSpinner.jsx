import React from 'react';

const LoadingSpinner = ({ size = 'md', className = '', message = 'Loading...' }) => {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <div 
        className={`${sizeClasses[size]} animate-spin rounded-full border-4 border-slate-600 border-t-transparent`}
        role="status"
        aria-label="loading"
      />
      {message && <span className="text-slate-400 text-sm">{message}</span>}
    </div>
  );
};

export default LoadingSpinner;