import React from 'react';
import { motion as Motion } from 'framer-motion';
import MimiCharacter from '../MimiCharacter';
import MimiDialogue from '../MimiDialogue';

const IdleScreen = () => {
  return (
    <div className="relative w-full h-screen">
      
      {/* Mimi Character - gentle breathing */}
      <MimiCharacter
        expression="happy"
        animation="idle"
        position="center"
        size="large"
      />
      
      {/* Welcome Message */}
      <div className="absolute top-[20%] left-1/2 -translate-x-1/2 w-full max-w-3xl px-4">
        <MimiDialogue
          text="Hi there! I'm Mimi! 👋"
          position="bottom"
        />
      </div>
      
      {/* Instruction Text */}
      <Motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="absolute bottom-[20%] left-1/2 -translate-x-1/2 text-center"
      >
        <p className="text-3xl font-semibold text-text mb-4">
          Come closer so I can see you! 😊
        </p>
        <Motion.div
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-6xl"
        >
          👀
        </Motion.div>
      </Motion.div>
      
      {/* Decorative elements */}
      <Motion.div
        className="absolute top-20 left-20 text-6xl"
        animate={{ rotate: 360 }}
        transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
      >
        ⭐
      </Motion.div>
      
      <Motion.div
        className="absolute top-40 right-32 text-5xl"
        animate={{ y: [0, -20, 0] }}
        transition={{ duration: 3, repeat: Infinity }}
      >
        ☁️
      </Motion.div>
      
      <Motion.div
        className="absolute bottom-40 left-40 text-5xl"
        animate={{ rotate: [0, 15, 0, -15, 0] }}
        transition={{ duration: 4, repeat: Infinity }}
      >
        🌟
      </Motion.div>
    </div>
  );
};

export default IdleScreen;