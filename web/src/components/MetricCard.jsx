import React, { useState, useEffect } from 'react';

export function MetricCard({ title, icon, value, sub, progress, color }) {
  const [displayValue, setDisplayValue] = useState(0);
  const stringValue = String(value);
  const numericValue = parseFloat(stringValue.replace(/[^0-9.]/g, '')) || 0;
  const suffix = stringValue.replace(/[0-9.]/g, '');

  useEffect(() => {
    let start = 0;
    const end = numericValue;
    const duration = 1000;
    const increment = end / (duration / 16);
    
    const timer = setInterval(() => {
      start += increment;
      if (start >= end) {
        setDisplayValue(end);
        clearInterval(timer);
      } else {
        setDisplayValue(start);
      }
    }, 16);
    
    return () => clearInterval(timer);
  }, [numericValue]);

  const formattedValue = suffix === 's' 
    ? displayValue.toFixed(2) + suffix 
    : Math.round(displayValue) + suffix;

  return (
    <div className="bg-zinc-900/40 p-10 rounded-[2.5rem] border border-zinc-800 relative group overflow-hidden">
      <div className="absolute top-8 right-10 text-white/5 group-hover:text-white/10 transition-colors">{icon}</div>
      <div className="text-zinc-500 text-[10px] font-black uppercase tracking-[0.2em] mb-4">{title}</div>
      <div className="text-7xl font-black mb-2">{formattedValue}</div>
      <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
        <div 
          className={`h-full ${color} transition-all duration-1000 ease-out`} 
          style={{ width: `${progress}%` }}
        ></div>
      </div>
      <p className="text-zinc-500 text-xs mt-4 font-bold">{sub}</p>
    </div>
  );
}
