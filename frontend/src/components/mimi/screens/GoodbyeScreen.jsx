import React, { useEffect } from 'react';
import { motion as Motion } from 'framer-motion';
import { Star } from 'lucide-react';

const GoodbyeScreen = ({
  studentName = "Friend",
  totalStars = 5,
  onComplete
}) => {

  useEffect(() => {
    const timer = setTimeout(() => {
      onComplete && onComplete();
    }, 5000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center overflow-hidden">

      {/* Floating hearts */}
      {[...Array(8)].map((_, i) => (
        <Motion.div
          key={i}
          className="absolute text-5xl pointer-events-none"
          style={{ left: `${8 + i * 11}%`, bottom: '0%' }}
          animate={{ y: [0, -500], opacity: [0, 1, 1, 0], rotate: [0, 360], scale: [0.5, 1, 0.5] }}
          transition={{ duration: 4, delay: i * 0.35, repeat: Infinity, repeatDelay: 0.5 }}
        >
          {i % 2 === 0 ? '💖' : '💝'}
        </Motion.div>
      ))}

      {/* Sun */}
      <Motion.div
        className="absolute top-8 right-12 text-8xl"
        animate={{ rotate: 360, scale: [1, 1.1, 1] }}
        transition={{
          rotate: { duration: 20, repeat: Infinity, ease: 'linear' },
          scale:  { duration: 2,  repeat: Infinity },
        }}
      >
        ☀️
      </Motion.div>

      {/* Big waving emoji */}
      <Motion.div
        className="text-[120px] mb-4 select-none"
        animate={{ rotate: [0, 15, -15, 15, -15, 0] }}
        transition={{ duration: 1.2, repeat: Infinity, repeatDelay: 1 }}
      >
        👋
      </Motion.div>

      {/* Goodbye message */}
      <Motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-3xl shadow-2xl px-10 py-6 text-center mb-6 mx-4"
      >
        <p className="text-3xl font-black text-purple-700 mb-1">
          Great job today, {studentName}! 🎉
        </p>
      </Motion.div>

      {/* Stars earned */}
      <Motion.div
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.5, type: 'spring' }}
        className="bg-white rounded-3xl shadow-2xl px-10 py-6 text-center mx-4"
      >
        <p className="text-xl text-gray-500 mb-3">You earned</p>
        <div className="flex items-center justify-center gap-3 mb-3">
          {[...Array(totalStars)].map((_, i) => (
            <Motion.div
              key={i}
              initial={{ opacity: 0, scale: 0, rotate: -180 }}
              animate={{ opacity: 1, scale: 1, rotate: 0 }}
              transition={{ delay: 0.8 + i * 0.12, type: 'spring' }}
            >
              <Star size={44} className="fill-yellow-400 text-yellow-400" />
            </Motion.div>
          ))}
        </div>
        <p className="text-5xl font-bold text-purple-600">{totalStars} Stars!</p>
      </Motion.div>

      {/* See you message */}
      <Motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.5 }}
        className="mt-6 text-center"
      >
        <p className="text-3xl font-bold text-gray-700">See you tomorrow! 👋</p>
        <p className="text-xl text-gray-500 mt-1">Keep being awesome!</p>
      </Motion.div>
    </div>
  );
};

export default GoodbyeScreen;
