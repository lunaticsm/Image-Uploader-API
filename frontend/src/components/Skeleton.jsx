import React from 'react';

const Skeleton = ({ className = '', count = 1 }) => {
  const skeletons = Array.from({ length: count }, (_, index) => (
    <div 
      key={index}
      className={`rounded-lg bg-white/5 animate-pulse ${className}`}
    />
  ));

  return <>{skeletons}</>;
};

export default Skeleton;