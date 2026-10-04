'use client';

import React, { useState } from 'react';
import { Zap, Loader2 } from 'lucide-react';

export default function DemoButton() {
  const [isRunning, setIsRunning] = useState(false);
  
  const handleDemo = async () => {
    setIsRunning(true);
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    setIsRunning(false);
    
    // In a real implementation, we would call the triggerDemo API here
    // and maybe show a success toast or dispatch an event to refresh components
    alert('Demo pipeline triggered! 5 new emails processed.');
  };

  return (
    <div className="fixed bottom-8 right-8 z-50">
      <button 
        onClick={handleDemo}
        disabled={isRunning}
        className={`flex items-center gap-2 px-6 py-3 rounded-full font-bold text-white shadow-lg transition-all transform hover:scale-105 active:scale-95 ${
          isRunning 
            ? 'bg-blue-600/80 cursor-not-allowed' 
            : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:shadow-[0_0_20px_rgba(59,130,246,0.5)]'
        }`}
      >
        {isRunning ? (
          <>
            <Loader2 size={20} className="animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <Zap size={20} className="fill-white" />
            Run Demo
          </>
        )}
      </button>
    </div>
  );
}
