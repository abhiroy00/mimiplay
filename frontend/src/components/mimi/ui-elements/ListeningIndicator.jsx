import React from 'react';
import { motion as Motion } from 'framer-motion';
import { Mic } from 'lucide-react';

const ListeningIndicator = ({ isListening = true, className = '' }) => {
  return (
    <Motion.div
      initial={{ opacity: 0, scale: 0 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0 }}
      className={`fixed bottom-10 left-1/2 -translate-x-1/2 ${className}`}
      style={{ zIndex: 50 }}
    >
      <div className="relative">
        {/* Pulsing circles */}
        {isListening && (
          <>
            <Motion.div
              className="absolute inset-0 bg-primary-400 rounded-full"
              animate={{
                scale: [1, 1.5, 1],
                opacity: [0.6, 0, 0.6],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
            <Motion.div
              className="absolute inset-0 bg-primary-400 rounded-full"
              animate={{
                scale: [1, 2, 1],
                opacity: [0.4, 0, 0.4],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
                delay: 0.5
              }}
            />
          </>
        )}
        
        {/* Main microphone button */}
        <Motion.div
          className="relative bg-gradient-to-br from-primary-400 to-primary-600 rounded-full p-8 shadow-2xl"
          animate={isListening ? {
            scale: [1, 1.1, 1],
          } : {}}
          transition={{
            duration: 1,
            repeat: isListening ? Infinity : 0,
            ease: "easeInOut"
          }}
        >
          <Mic size={48} className="text-white" />
        </Motion.div>
        
        {/* Listening text */}
        {isListening && (
          <Motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute -bottom-12 left-1/2 -translate-x-1/2 whitespace-nowrap"
          >
            <p className="text-xl font-bold text-text">Listening...</p>
          </Motion.div>
        )}
      </div>
    </Motion.div>
  );
};

export default ListeningIndicator;