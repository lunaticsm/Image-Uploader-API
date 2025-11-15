import React, { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';

const AdvancedMetricVisualization = ({ data }) => {
  const containerRef = useRef(null);
  const [particles, setParticles] = useState([]);
  const [orbits, setOrbits] = useState([]);
  
  useEffect(() => {
    if (!data || data.length === 0) return;

    // Animate the entire container with holographic effect
    if (containerRef.current) {
      gsap.fromTo(containerRef.current, 
        { 
          opacity: 0, 
          scale: 0.8, 
          rotationY: -10,
          rotationX: 10,
        },
        { 
          opacity: 1, 
          scale: 1, 
          rotationY: 0,
          rotationX: 0,
          duration: 1.5, 
          ease: "power3.out",
          onUpdate: () => {
            // Add subtle continuous rotation
            if (containerRef.current) {
              const time = Date.now() * 0.001;
              containerRef.current.style.transform += ` rotateX(${Math.sin(time * 0.3) * 0.2}deg) rotateY(${Math.cos(time * 0.2) * 0.3}deg)`;
            }
          }
        }
      );
    }

    // Create complex particle system
    const newParticles = [];
    for (let i = 0; i < 30; i++) {
      newParticles.push({
        id: i,
        size: Math.random() * 3 + 1,
        color: i % 4 === 0 ? 'from-cyan-400 to-blue-400' :
               i % 4 === 1 ? 'from-emerald-400 to-green-400' :
               i % 4 === 2 ? 'from-pink-400 to-rose-400' : 'from-yellow-400 to-amber-400',
        x: Math.random() * 100,
        y: Math.random() * 100,
        duration: Math.random() * 8 + 4,
        delay: Math.random() * 3,
        shape: Math.random() > 0.5 ? 'circle' : 'square'
      });
    }
    setParticles(newParticles);

    // Create orbit paths for each metric
    const newOrbits = [];
    for (let i = 0; i < 4; i++) {
      newOrbits.push({
        id: i,
        radiusX: 25 + i * 15,
        radiusY: 15 + i * 10,
        duration: 15 + i * 3,
        delay: i * 2,
        color: i === 0 ? 'from-blue-500/30 to-cyan-500/30' :
                 i === 1 ? 'from-green-500/30 to-emerald-500/30' :
                 i === 2 ? 'from-rose-500/30 to-pink-500/30' : 'from-yellow-500/30 to-amber-500/30'
      });
    }
    setOrbits(newOrbits);

  }, [data]);

  if (!data || data.length === 0) return null;

  return (
    <div 
      ref={containerRef} 
      className="relative w-full h-80 rounded-2xl bg-gradient-to-br from-slate-900/90 to-slate-800/80 border border-white/10 p-6 overflow-hidden"
      style={{ 
        transformStyle: 'preserve-3d',
        perspective: '1000px'
      }}
    >
      {/* Holographic grid background */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(59,130,246,0.1)_1px,transparent_1px),linear-gradient(to_bottom,rgba(59,130,246,0.1)_1px,transparent_1px)] bg-[size:40px_40px]"></div>
      </div>
      
      {/* Animated particles */}
      <div className="absolute inset-0 overflow-hidden">
        {particles.map((particle) => (
          <div
            key={particle.id}
            className={`absolute ${particle.shape === 'circle' ? 'rounded-full' : 'rounded-sm'} bg-gradient-to-r ${particle.color} opacity-30`}
            style={{
              width: `${particle.size}px`,
              height: `${particle.size}px`,
              left: `${particle.x}%`,
              top: `${particle.y}%`,
              animation: `float-pulse-advanced ${particle.duration}s infinite ${particle.delay}s ease-in-out`
            }}
          ></div>
        ))}
      </div>
      
      {/* Orbital paths */}
      <div className="absolute inset-0 flex items-center justify-center">
        {orbits.map((orbit) => (
          <div
            key={orbit.id}
            className={`absolute rounded-full border bg-gradient-to-r ${orbit.color} opacity-20`}
            style={{
              width: `${orbit.radiusX * 2}%`,
              height: `${orbit.radiusY * 2}%`,
              borderWidth: '1px',
              animation: `orbit-rotate ${orbit.duration}s linear infinite ${orbit.delay}s`
            }}
          ></div>
        ))}
      </div>
      
      {/* Orbiting elements for each metric */}
      <div className="absolute inset-0 flex items-center justify-center">
        {data.map((item, index) => {
          const orbit = orbits[index];
          if (!orbit) return null;
          
          return (
            <div
              key={`orbiter-${index}`}
              className="absolute w-3 h-3 rounded-full bg-gradient-to-r from-white to-cyan-300 shadow-lg shadow-cyan-500/50"
              style={{
                width: '12px',
                height: '12px',
                transformOrigin: `${orbit.radiusX}% 50%`,
                animation: `orbiter-travel ${orbit.duration}s linear infinite ${orbit.delay}s`,
              }}
            >
              <div className="absolute inset-0 rounded-full bg-cyan-300 animate-ping opacity-70"></div>
            </div>
          );
        })}
      </div>
      
      <div className="relative z-10 h-full flex flex-col">
        <h3 className="text-xl font-bold text-center mb-6 bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
          Metrics
        </h3>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 flex-1">
          {data.map((item, index) => {
            const percentage = Math.min((item.value / 100000) * 100, 100); // Scale for demo
            return (
              <div 
                key={index} 
                className="bg-white/5 backdrop-blur-sm rounded-xl p-4 border border-white/10 hover:border-white/30 transition-all duration-500 hover:scale-[1.03] group relative overflow-hidden"
              >
                {/* Animated background for each card */}
                <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                
                <div className="relative z-10">
                  <div className="flex items-center gap-2 mb-3">
                    <div className={`p-2 rounded-lg group-hover:scale-125 transition-transform duration-300 ${
                      index === 0 ? 'bg-blue-500/20 text-blue-300' : 
                      index === 1 ? 'bg-green-500/20 text-green-300' : 
                      index === 2 ? 'bg-rose-500/20 text-rose-300' : 'bg-yellow-500/20 text-yellow-300'
                    }`}>
                      <span className="text-xl">{item.icon}</span>
                    </div>
                    <span className="text-xs text-slate-400">{item.label}</span>
                  </div>
                  
                  <div className="text-lg font-bold truncate group-hover:text-white transition-colors duration-300 mb-2">
                    {item.formatter ? item.formatter(item.value) : item.value}
                  </div>
                  
                  <div className="w-full bg-slate-700/50 rounded-full h-2.5 overflow-hidden">
                    <div 
                      className={`h-full rounded-full bg-gradient-to-r ${
                        index === 0 ? 'from-blue-500 to-cyan-400' : 
                        index === 1 ? 'from-green-500 to-emerald-400' : 
                        index === 2 ? 'from-rose-500 to-pink-400' : 'from-yellow-500 to-amber-400'
                      }`}
                      style={{ 
                        width: `${percentage}%`,
                        transition: 'width 1.5s cubic-bezier(0.22, 0.61, 0.36, 1)'
                      }}
                    ></div>
                  </div>
                  
                  {/* Animated percentage indicator */}
                  <div className="text-xs mt-1 text-slate-400 text-right">
                    {percentage.toFixed(0)}%
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      
      {/* Corner accents with enhanced glow */}
      <div className="absolute top-3 left-3 w-6 h-6 border-l-2 border-t-2 border-cyan-400/50 rounded-tl-lg blur-sm"></div>
      <div className="absolute bottom-3 right-3 w-6 h-6 border-r-2 border-b-2 border-purple-400/50 rounded-br-lg blur-sm"></div>
      
      {/* Scanning line effect */}
      <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-scan"></div>
    </div>
  );
};

// Add advanced CSS animations
const style = document.createElement('style');
style.innerHTML = `
  @keyframes float-pulse-advanced {
    0%, 100% { 
      transform: translate(0, 0) scale(1); 
      opacity: 0.2; 
    }
    50% { 
      transform: translate(${Math.random() * 30 - 15}px, ${Math.random() * 30 - 15}px) scale(1.5); 
      opacity: 0.4; 
    }
  }
  
  @keyframes orbit-rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  
  @keyframes orbiter-travel {
    from { transform: rotate(0deg) translateX(0) rotate(0deg); }
    to { transform: rotate(360deg) translateX(0) rotate(-360deg); }
  }
  
  @keyframes scan {
    0% { transform: translateY(0); opacity: 0; }
    10% { opacity: 0.8; }
    90% { opacity: 0.8; }
    100% { transform: translateY(100vh); opacity: 0; }
  }
  
  .animate-scan {
    animation: scan 4s linear infinite;
  }
`;
if (!document.querySelector('#advanced-viz-animations')) {
  style.id = 'advanced-viz-animations';
  document.head.appendChild(style);
}

export default AdvancedMetricVisualization;