import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'

// ── Available videos (transparent background .webm) ──────────────────────────
import mimiIdleVideo from '../../assets/images/mimi/mimiidell_nobg.webm'
import mimiWaveVideo from '../../assets/images/mimi/mimiwavehand_nobg.webm'
// Add these imports once you create the files:
// import mimiThinkingVideo    from '../../assets/images/mimi/mimithinking_nobg.webm'
// import mimiTalkingVideo     from '../../assets/images/mimi/mimitalking_nobg.webm'
// import mimiListeningVideo   from '../../assets/images/mimi/mimilistening_nobg.webm'
// import mimiExcitedVideo     from '../../assets/images/mimi/mimiexcited_nobg.webm'
// import mimiCelebratingVideo from '../../assets/images/mimi/mimicelebrating_nobg.webm'

// ── Fallbacks until new videos are ready ─────────────────────────────────────
const mimiThinkingVideo    = mimiIdleVideo
const mimiTalkingVideo     = mimiIdleVideo
const mimiListeningVideo   = mimiWaveVideo
const mimiExcitedVideo     = mimiWaveVideo
const mimiCelebratingVideo = mimiWaveVideo

// ── State → video map ─────────────────────────────────────────────────────────
const VIDEO_MAP = {
  idle:          mimiIdleVideo,
  listening:     mimiListeningVideo,
  user_speaking: mimiExcitedVideo,
  thinking:      mimiThinkingVideo,
  mimi_speaking: mimiTalkingVideo,
  interrupted:   mimiExcitedVideo,
}

const getVideo = (vadStatus, sessionState, isSpeaking) => {
  if (sessionState !== 'running') return mimiIdleVideo
  return VIDEO_MAP[vadStatus] || mimiIdleVideo
}

// ── Glow colour per state ─────────────────────────────────────────────────────
const GLOW = {
  idle:          'rgba(196,181,253,0.30)',
  listening:     'rgba(74,222,128,0.40)',
  user_speaking: 'rgba(251,146,60,0.45)',
  thinking:      'rgba(250,204,21,0.40)',
  mimi_speaking: 'rgba(167,139,250,0.50)',
  interrupted:   'rgba(56,189,248,0.55)',
}

// ── Subtle body pulse per state (no vertical bounce) ─────────────────────────
const BODY = {
  idle:          { scale: [1, 1.012, 1],  transition: { duration: 4,   repeat: Infinity, ease: 'easeInOut' } },
  listening:     { scale: [1, 1.015, 1],  transition: { duration: 2.5, repeat: Infinity, ease: 'easeInOut' } },
  user_speaking: { scale: [1, 1.03,  1],  transition: { duration: 1.2, repeat: Infinity, ease: 'easeInOut' } },
  thinking:      { rotate: [0, -2, 2, 0], transition: { duration: 4,   repeat: Infinity, ease: 'easeInOut' } },
  mimi_speaking: { scale: [1, 1.02,  1],  transition: { duration: 0.9, repeat: Infinity, ease: 'easeInOut' } },
  interrupted:   { scale: [1, 1.08,  1],  transition: { duration: 0.4, ease: 'easeOut' } },
}

// ── Thinking bubble ───────────────────────────────────────────────────────────
const ThinkingBubble = () => (
  <motion.div
    initial={{ opacity: 0, scale: 0, y: 10 }}
    animate={{ opacity: 1, scale: 1, y: 0 }}
    exit={{ opacity: 0, scale: 0, y: 10 }}
    transition={{ duration: 0.25 }}
    className="absolute -top-2 right-2 bg-white rounded-2xl rounded-br-sm px-4 py-3 shadow-xl border border-purple-100 z-30"
    style={{ filter: 'drop-shadow(0 4px 12px rgba(167,139,250,0.3))' }}
  >
    <div className="flex gap-1.5 items-end">
      {[0, 1, 2].map(i => (
        <motion.div
          key={i}
          className="w-3 h-3 rounded-full bg-purple-400"
          animate={{ y: [0, -9, 0] }}
          transition={{ duration: 0.55, repeat: Infinity, delay: i * 0.18, ease: 'easeInOut' }}
        />
      ))}
    </div>
    <div className="absolute -bottom-2 right-4 w-4 h-4 bg-white border-r border-b border-purple-100 rotate-45" />
  </motion.div>
)

// ── Sound bars (speaking) ─────────────────────────────────────────────────────
const SoundBars = () => (
  <motion.div
    initial={{ opacity: 0, x: 10 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: 10 }}
    className="absolute top-1/3 -right-6 flex gap-1 items-center z-30"
  >
    {[18, 32, 24, 38, 20, 30].map((h, i) => (
      <motion.div
        key={i}
        className="w-2 rounded-full bg-purple-400"
        animate={{ height: [`${h * 0.5}px`, `${h}px`, `${h * 0.7}px`, `${h}px`, `${h * 0.5}px`] }}
        transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.07, ease: 'easeInOut' }}
      />
    ))}
  </motion.div>
)

// ── Floating sparkles ─────────────────────────────────────────────────────────
const Sparkles = ({ emojis, trigger }) => (
  <AnimatePresence>
    {trigger && emojis.map((emoji, i) => (
      <motion.div
        key={`${emoji}-${i}`}
        className="absolute pointer-events-none select-none z-40 text-xl"
        style={{ left: `${15 + i * 25}%`, top: `${8 + (i % 3) * 10}%` }}
        initial={{ opacity: 0, y: 0, scale: 0.4 }}
        animate={{ opacity: [0, 1, 1, 0], y: -40, scale: [0.4, 1.3, 1.1, 0.6] }}
        exit={{ opacity: 0 }}
        transition={{ duration: 1.4, repeat: Infinity, delay: i * 0.28, ease: 'easeOut' }}
      >
        {emoji}
      </motion.div>
    ))}
  </AnimatePresence>
)


// ── Main component ────────────────────────────────────────────────────────────
const MimiCharacter = ({ vadStatus = 'idle', isSpeaking = false, sessionState = 'idle' }) => {
  const videoSrc = getVideo(vadStatus, sessionState, isSpeaking)
  const glow     = GLOW[vadStatus] || GLOW.idle
  const bodyAnim = BODY[vadStatus] || BODY.idle

  return (
    <div className="relative z-20 flex-shrink-0 select-none" style={{ width: '420px', height: '520px' }}>

      {/* ── Ambient glow ── */}
      <motion.div
        className="absolute inset-8 rounded-full pointer-events-none"
        animate={{
          boxShadow: [`0 0 50px 25px ${glow}`, `0 0 90px 50px ${glow}`, `0 0 50px 25px ${glow}`]
        }}
        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* ── Sparkles ── */}
      <Sparkles emojis={['⭐', '✨', '💫']} trigger={vadStatus === 'user_speaking'} />
      <Sparkles emojis={['🎉', '🌟', '✨']} trigger={vadStatus === 'mimi_speaking' && isSpeaking} />

      {/* ── Character body with subtle pulse ── */}
      <motion.div className="w-full h-full relative" animate={bodyAnim}>

        {/* ── Video crossfade: AnimatePresence mode="sync" overlays old+new ── */}
        <div className="absolute inset-0">
          <AnimatePresence mode="sync">
            <motion.video
              key={videoSrc}
              src={videoSrc}
              autoPlay
              loop
              muted
              playsInline
              className="absolute inset-0 w-full h-full object-contain"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35, ease: 'easeInOut' }}
              style={{
                filter: vadStatus === 'mimi_speaking'
                  ? 'drop-shadow(0 0 14px rgba(167,139,250,0.55))'
                  : 'none'
              }}
            />
          </AnimatePresence>
        </div>

        {/* ── State overlays ── */}

        <AnimatePresence>
          {vadStatus === 'thinking' && <ThinkingBubble key="think" />}
        </AnimatePresence>

        <AnimatePresence>
          {vadStatus === 'mimi_speaking' && <SoundBars key="bars" />}
        </AnimatePresence>

        {/* Idle sparkle (occasional) */}
        <AnimatePresence>
          {(!sessionState === 'running' || vadStatus === 'idle') && (
            <motion.div
              key="idle-star"
              className="absolute top-6 left-8 text-3xl pointer-events-none"
              animate={{ scale: [0, 1.1, 1, 0], opacity: [0, 1, 1, 0] }}
              transition={{ duration: 2, repeat: Infinity, repeatDelay: 4 }}
            >
              ✨
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}

export default MimiCharacter
