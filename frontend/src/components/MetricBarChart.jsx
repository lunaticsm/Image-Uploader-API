import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';

const MetricBarChart = ({ data }) => {
  const chartRef = useRef(null);
  const barRefs = useRef([]);

  useEffect(() => {
    if (!chartRef.current || !data) return;

    // Animate the bars
    barRefs.current.forEach((bar, index) => {
      if (bar) {
        const maxValue = Math.max(...data.map(item => item.value), 1);
        const percentage = (data[index]?.value / maxValue) * 100;
        
        gsap.fromTo(bar, 
          { height: 0, opacity: 0 },
          { 
            height: `${percentage}%`, 
            opacity: 1, 
            duration: 1.2, 
            ease: "bounce.out",
            delay: index * 0.1
          }
        );
      }
    });
  }, [data]);

  if (!data || data.length === 0) return null;

  return (
    <div className="relative h-48 bg-slate-900/50 rounded-xl p-4 mt-4">
      <div className="absolute inset-4 flex items-end justify-between gap-2">
        {data.map((item, index) => (
          <div 
            key={index}
            ref={el => barRefs.current[index] = el}
            className="w-1/4 bg-gradient-to-t from-[#fb7185] to-[#fbbf24] rounded-t-lg min-h-[5px] transition-all duration-500"
            style={{ height: '0%' }}
          >
            <div className="text-center text-xs -mt-6 text-slate-300 rotate-[-45deg] origin-top">
              {item.formatter ? item.formatter(item.value) : item.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MetricBarChart;