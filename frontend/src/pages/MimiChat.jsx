// import React, { useState, useEffect, useRef } from 'react'
// import axios from 'axios'
// import { motion as Motion, AnimatePresence } from 'framer-motion'
// import { API_ENDPOINTS } from '../config'

// import bgImage from '../assets/images/mimi/bg.jpg'
// import mimiIdleVideo from '../assets/images/mimi/mimiidell_nobg.webm'
// import mimiWaveVideo from '../assets/images/mimi/mimiwavehand_nobg.webm'

// const MimiChat = () => {
//   const [sessionState, setSessionState] = useState('idle')
//   const [mimiText, setMimiText] = useState('')
//   const [imageUrl, setImageUrl] = useState(null)
//   const [ytVideo, setYtVideo] = useState(null)
//   const [playing, setPlaying] = useState(false)
//   const [displayedText, setDisplayedText] = useState('')
//   const [isTyping, setIsTyping] = useState(false)
//   // no explicit pixel shift state; we animate left/x directly

//   const pollingRef = useRef(null)

//   const startSession = async () => {
//     try {
//       await axios.get(API_ENDPOINTS.START_MIMI_SESSION)
//       setSessionState('running')
//       startPolling()
//     } catch (e) {
//       console.error(e)
//     }
//   }

//   const startPolling = () => {
//     if (pollingRef.current) return
//     pollingRef.current = setInterval(async () => {
//       try {
//         const res = await axios.get(API_ENDPOINTS.GET_MIMI_STATUS)
//         const d = res.data
//         // setMimiText(d.text)
//         // setImageUrl(d.image_url)
//         // setYtVideo(d.yt_video)
//         // setSessionState(d.action || 'idle')
//         if (d.text === "Thinking..." || !d.text) {
//             // Wait for LLM to finish
//         } else {
//             // 2. Sirf tab update karo jab naya text aaye
//             setMimiText(d.text);
//             setImageUrl(d.image_url);
//             setYtVideo(d.yt_video);
//             setSessionState(d.action || 'idle');
//         }
//         if (d.action === 'playing_video' && d.yt_video) setPlaying(true)
//       } catch (e) {
//         console.error('Mimi poll error', e)
//       }
//     }, 500)
//   }

//   // Typewriter effect: reveal mimiText progressively
//   useEffect(() => {
//     if (!mimiText) {
//       setDisplayedText('')
//       setIsTyping(false)
//       return
//     }

//     setDisplayedText('')
//     setIsTyping(true)
//     const chars = Array.from(mimiText)
//     let i = 0
//     const speed = 30 // ms per char; adjust for slower/faster
//     const t = setInterval(() => {
//       i += 1
//       setDisplayedText(chars.slice(0, i).join(''))
//       if (i >= chars.length) {
//         clearInterval(t)
//         setIsTyping(false)
//       }
//     }, speed)

//     return () => clearInterval(t)
//   }, [mimiText])

//   // Speak the full response using browser TTS once typing finishes
//   useEffect(() => {
//     if (!displayedText || isTyping) return
//     try {
//       if ('speechSynthesis' in window) {
//         window.speechSynthesis.cancel()
//         const u = new SpeechSynthesisUtterance(mimiText || displayedText)
//         u.lang = 'en-US'
//         u.rate = 0.95
//         // window.speechSynthesis.speak(u)
//       }
//     } catch (e) {
//       console.warn('Browser TTS failed', e)
//     }
//   }, [displayedText, isTyping, mimiText])

//   // no explicit shift calculation; animate left/x directly for full-left effect

//   useEffect(() => {
//     return () => {
//       if (pollingRef.current) clearInterval(pollingRef.current)
//     }
//   }, [])

//   return (
//     <div className="relative min-h-screen w-full bg-cover bg-center overflow-hidden" style={{ backgroundImage: `url(${bgImage})` }}>
//       <div className="absolute top-8 right-8 z-50 flex items-center gap-2">
//         <Motion.button
//           onClick={startSession}
//           disabled={sessionState !== 'idle'}
//           className={`px-6 py-3 rounded-full text-white bg-indigo-600`}
//         >
//           {sessionState === 'idle' ? 'Start Mimi Chat' : 'Session Running'}
//         </Motion.button>

//         <Motion.button
//           onClick={() => {
//             // Demo response for preview
//             setSessionState('running')
//             setMimiText('The sun is big and bright. It gives us light and keeps us warm.')
//             setImageUrl('https://via.placeholder.com/600x360?text=Sun+Image')
//             setYtVideo('https://www.youtube.com/watch?v=ysz5S6PUM-U')
//             setPlaying(false)
//           }}
//           className="px-4 py-2 rounded-full bg-white border border-gray-200 text-gray-800 shadow-sm"
//         >
//           Demo Response
//         </Motion.button>
//       </div>

//       {/* Mimi video (animates left when showing a response) */}
//       <Motion.div
//         className="absolute bottom-0 z-50 w-[520px] h-[520px]"
//         animate={mimiText ? { left: '12px', x: 0 } : { left: '50%', x: '-50%' }}
//         transition={{ type: 'spring', stiffness: 120, damping: 18 }}
//         style={{ position: 'absolute' }}
//       >
//         <video
//           src={mimiText ? mimiIdleVideo : (sessionState === 'running' ? mimiWaveVideo : mimiIdleVideo)}
//           autoPlay
//           loop
//           muted
//           playsInline
//           className="w-full h-full object-contain"
//         />
//       </Motion.div>

//       {/* White response box */}
//       <div className="absolute top-32 left-[440px] z-40 w-[700px] pointer-events-none">
//         <AnimatePresence>
//           {(mimiText || imageUrl || ytVideo) && (
//             <Motion.div
//               initial={{ opacity: 0, y: -20, scale: 0.98 }}
//               animate={{ opacity: 1, y: 0, scale: 1 }}
//               exit={{ opacity: 0, y: -10 }}
//               transition={{ duration: 0.35 }}
//               className="bg-white rounded-2xl p-6 shadow-2xl pointer-events-auto"
//             >
//               <p className="text-2xl font-semibold text-gray-800 min-h-[64px]">
//                 {displayedText}
//                 <span className={`ml-1 text-gray-700 ${isTyping ? 'animate-pulse' : ''}`}> {isTyping ? '|' : ''}</span>
//               </p>
//               {imageUrl && (
//                 <div className="mt-4">
//                   <img src={imageUrl} alt="mimi result" referrerPolicy="no-referrer" className="max-h-64 mx-auto rounded-md"  />
//                 </div>
//               )}
//               {ytVideo && (
//                 <div className="mt-4">
//                   {!playing ? (
//                     <button onClick={() => setPlaying(true)} className="px-4 py-2 bg-blue-600 text-white rounded">Play Video</button>
//                   ) : (
//                     <div className="aspect-w-16 aspect-h-9">
//                       <iframe
//                         src={`https://www.youtube.com/embed/${extractYoutubeId(ytVideo)}?autoplay=1`}
//                         title="YouTube video"
//                         allow="autoplay; encrypted-media"
//                         className="w-full h-64"
//                       />
//                     </div>
//                   )}
//                 </div>
//               )}
//             </Motion.div>
//           )}
//         </AnimatePresence>
//       </div>
//     </div>
//   )
// }

// function extractYoutubeId(url) {
//   if (!url) return ''
//   const m = url.match(/(youtu\.be\/|v=|embed\/)([A-Za-z0-9_-]{6,})/)
//   return m ? m[2] : url
// }

// export default MimiChat

// ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
import React, { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import { motion as Motion, AnimatePresence } from 'framer-motion'
import { API_ENDPOINTS } from '../config'
import GoodbyeScreen from '../components/mimi/screens/GoodbyeScreen'

import bgImage from '../assets/images/mimi/bg.jpg'
import MimiCharacter from '../components/mimi/MimiCharacter'

const MOTIVATIONAL_QUOTES = [
  "You're a star! 🌟 Keep shining bright!",
  "Every day you learn something new – that's amazing! 🚀",
  "You're growing smarter and smarter! See you next time! 👋",
  "Remember, you can do anything you put your mind to! 💪",
  "Learning is an adventure, and you're the best explorer! 🗺️",
  "You're so curious – that's the best superpower! 🦸",
  "Keep asking questions – that's how we learn! ❓",
  "You made today awesome! Come back soon! 🎉",
]
const getGoodbyeQuote = () =>
  MOTIVATIONAL_QUOTES[Math.floor(Math.random() * MOTIVATIONAL_QUOTES.length)]

const MimiChat = () => {

  const [sessionState,  setSessionState]  = useState('idle')
  const [showGoodbye,   setShowGoodbye]   = useState(false)
  const [studentName,   setStudentName]   = useState('')
  const [_sessionId,    setSessionId]     = useState('')
  const [mimiText,      setMimiText]      = useState('')
  const [imageUrl,      setImageUrl]      = useState(null)
  const [ytVideo,       setYtVideo]       = useState(null)
  const [playing,       setPlaying]       = useState(false)

  // Image → then Video sequence:
  // If response has both image and video → show image first, auto-play video after 5s.
  // If only video → play immediately.
  useEffect(() => {
    setPlaying(false)
    if (!ytVideo) return
    const delay = imageUrl ? 5000 : 500
    const t = setTimeout(() => setPlaying(true), delay)
    return () => clearTimeout(t)
  }, [ytVideo, imageUrl])
  const [displayedText, setDisplayedText] = useState('')
  const [isTyping,      setIsTyping]      = useState(false)
  const [isSpeaking,    setIsSpeaking]    = useState(false) // ← Mimi bol rahi hai?
  const [chatHistory,   setChatHistory]   = useState([])
  const [_lastQuestion, setLastQuestion]  = useState('') // ← current question track

  const videoRef        = useRef(null)
  const canvasRef       = useRef(null)
  const [webcamActive,  setWebcamActive] = useState(false)
  const [showManualEntry, setShowManualEntry] = useState(false)
  const [manualName,    setManualName]   = useState('')

  // VAD status: 'idle' | 'listening' | 'user_speaking' | 'thinking' | 'mimi_speaking'
  const [vadStatus,     setVadStatus]     = useState('idle')
  const [topicsList,    setTopicsList]    = useState([])   // topics discussed this session
  const [showTopics,    setShowTopics]    = useState(false)

  const pollingRef           = useRef(null)
  const facePollingRef       = useRef(null)
  const faceTimeoutRef       = useRef(null)
  const faceHitCountRef      = useRef(0)    // consecutive successful recognitions
  const lastFaceNameRef      = useRef(null) // name from last frame — resets streak on mismatch
  const lastAnswerRef    = useRef('')
  const lastActionRef    = useRef('')
  const chatHistoryRef   = useRef([])
  const _mediaRecorderRef = useRef(null)
  const _audioChunksRef   = useRef([])
  const sessionIdRef     = useRef('')
  const studentNameRef   = useRef('')
  const topicsListRef    = useRef([])   // mirrors topicsList state for use inside stable callbacks
  useEffect(() => { topicsListRef.current = topicsList }, [topicsList])
  // VAD refs
  const audioContextRef   = useRef(null)
  const analyserRef       = useRef(null)
  const micStreamRef      = useRef(null)
  const vadIntervalRef    = useRef(null)
  const silenceTimerRef   = useRef(null)
  const isRecordingRef    = useRef(false)
  const isMimiSpeakingRef = useRef(false)
  const _speechStartRef   = useRef(0)
  const currentAudioRef   = useRef(null)   // tracks playing Audio so wake-word can stop it
  const startVADRef            = useRef(null)   // stable ref to startVAD, breaks circular dep
  const stopSessionRef         = useRef(null)   // stable ref to stopSession for recognition handlers
  const doInterruptRef         = useRef(null)   // stable ref to doInterrupt, used by playMimiAudio VAD
  const sayGoodbyeAndStopRef   = useRef(null)   // voice-triggered goodbye flow
  const justInterruptedRef     = useRef(0)      // timestamp of last doInterrupt (echo-clear window)

  useEffect(() => {
    chatHistoryRef.current = chatHistory
  }, [chatHistory])

  const generateSessionId = () =>
    `mimi-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`

  // ── Webcam Management ─────────────────────────────────────────
  const stopWebcam = useCallback(() => {
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks()
      tracks.forEach(track => track.stop())
      videoRef.current.srcObject = null
    }
    setWebcamActive(false)
  }, [])

  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 } 
      })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        setWebcamActive(true)
      }
    } catch (err) {
      console.error("Webcam error:", err)
      alert("Please allow camera access for face detection.")
    }
  }

  // ── Face detection ───────────────────────────────────────────
  const startFaceDetection = useCallback(async () => {
    // Unlock audio playback — must happen inside a real user-gesture handler.
    // Chrome blocks audio.play() from async callbacks (setInterval, fetch, etc.)
    // unless the tab has already been "unlocked" by a synchronous user click.
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)()
      const buf = ctx.createBuffer(1, 1, 22050)
      const src = ctx.createBufferSource()
      src.buffer = buf
      src.connect(ctx.destination)
      src.start(0)
      ctx.close()
    } catch {}

    setSessionState('detecting')
    setStudentName('')
    setMimiText('')
    setImageUrl(null)
    setYtVideo(null)
    setChatHistory([])
    chatHistoryRef.current = []
    lastAnswerRef.current  = ''
    lastActionRef.current  = ''
    setLastQuestion('')
    setShowManualEntry(false)
    setManualName('')
    setTopicsList([])
    setShowTopics(false)

    await startWebcam()

    // After 30s of no recognition, show manual entry fallback
    faceTimeoutRef.current = setTimeout(() => {
      setShowManualEntry(true)
    }, 30000)

    faceHitCountRef.current = 0
    lastFaceNameRef.current = null

    facePollingRef.current = setInterval(async () => {
      if (!videoRef.current || !canvasRef.current || !videoRef.current.srcObject) return

      try {
        const canvas = canvasRef.current
        const video  = videoRef.current
        // Full webcam resolution — 320x240 produced ~50x50 px faces that HOG misses at arm's length
        canvas.width  = 640
        canvas.height = 480
        const ctx = canvas.getContext('2d')
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
        const base64 = canvas.toDataURL('image/jpeg', 0.85)

        const res  = await axios.post(API_ENDPOINTS.PROCESS_FRAME, { image: base64 })
        const data = res.data

        if (data.person) {
          const name = data.person.replace(/_/g, ' ').trim()
          // Require 2 consecutive frames of the same person to avoid single-frame false positives
          if (name === lastFaceNameRef.current) {
            faceHitCountRef.current++
          } else {
            faceHitCountRef.current = 1
            lastFaceNameRef.current = name
          }
          console.log(`[FaceDetect] ${name} — hit ${faceHitCountRef.current}/2`)

          if (faceHitCountRef.current >= 2) {
            clearInterval(facePollingRef.current)
            clearTimeout(faceTimeoutRef.current)
            facePollingRef.current = null
            faceTimeoutRef.current = null
            faceHitCountRef.current = 0
            lastFaceNameRef.current = null
            stopWebcam()
            setShowManualEntry(false)
            setStudentName(name)
            startMimiSession(name)
          }
        } else {
          // Reset streak on any non-recognition frame
          faceHitCountRef.current = 0
          lastFaceNameRef.current = null
          console.log('[FaceDetect] No face recognized (distance or no detection)')
        }
      } catch (e) { console.error('[FaceDetect] Error during frame processing:', e) }
    }, 1000) // 1 s — matches original intent (comment said 1 s, code was 2 s)
  }, [stopWebcam]) // eslint-disable-line

  // ── Play Mimi's audio response, then resume listening ─────────
  const playMimiAudio = useCallback((base64audio, onDone) => {
    if (!sessionIdRef.current && !onDone) return

    // Stop any currently-playing audio so responses never overlap
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }
    clearInterval(vadIntervalRef.current)

    isMimiSpeakingRef.current = true
    setVadStatus('celebrating')
    setIsSpeaking(true)
    setTimeout(() => setVadStatus('mimi_speaking'), 700)

    // ── Audio-based VAD: detect user speaking via echo-cancelled mic ──
    // Uses AnalyserNode (set up with echoCancellation) so we DON'T pick up
    // Mimi's own speaker output — only real user voice triggers this.
    clearInterval(vadIntervalRef.current)
    if (analyserRef.current) {
      const buf = new Uint8Array(analyserRef.current.frequencyBinCount)
      let voiced = 0
      vadIntervalRef.current = setInterval(() => {
        if (!isMimiSpeakingRef.current) { clearInterval(vadIntervalRef.current); return }
        analyserRef.current.getByteTimeDomainData(buf)
        let sum = 0
        for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; sum += v * v }
        const rms = Math.sqrt(sum / buf.length)
        if (rms > 0.04) {
          if (++voiced >= 2) {                        // ~200ms sustained voice = real speech
            clearInterval(vadIntervalRef.current)
            if (doInterruptRef.current) doInterruptRef.current()
          }
        } else { voiced = 0 }
      }, 100)
    }

    try {
      const url   = URL.createObjectURL(
        new Blob([Uint8Array.from(atob(base64audio), c => c.charCodeAt(0))], { type: 'audio/mpeg' })
      )
      const audio = new Audio(url)
      currentAudioRef.current = audio

      const _resume = () => {
        clearInterval(vadIntervalRef.current)       // stop VAD when audio ends naturally
        URL.revokeObjectURL(url)
        currentAudioRef.current = null
        isMimiSpeakingRef.current = false
        setIsSpeaking(false)
        if (!sessionIdRef.current && !onDone) return
        setVadStatus('listening')
        if (onDone) {
          onDone()
        } else if (sessionIdRef.current) {
          // With continuous:false, recognition ends naturally while Mimi speaks.
          // Always restart it so we're listening again after Mimi finishes.
          if (startVADRef.current) startVADRef.current()
        }
      }

      audio.play().catch((err) => {
        console.error('[Mimi] Audio play() failed:', err.name, err.message)
        _resume()
      })
      audio.onended = _resume
      audio.onerror = (e) => {
        console.error('[Mimi] Audio decode/load error:', e)
        clearInterval(vadIntervalRef.current)
        URL.revokeObjectURL(url)
        currentAudioRef.current = null
        isMimiSpeakingRef.current = false
        setIsSpeaking(false)
        setVadStatus('listening')
        if (onDone) onDone()
        else if (sessionIdRef.current && startVADRef.current) startVADRef.current()
      }
    } catch {
      clearInterval(vadIntervalRef.current)
      currentAudioRef.current = null
      isMimiSpeakingRef.current = false
      setIsSpeaking(false)
      setVadStatus('listening')
      onDone && onDone()
    }
  }, [])

  // ── Send speech blob → get Mimi's reply ───────────────────────
  const _sendAudioToMimi = useCallback(async (blob) => {
    const sid  = sessionIdRef.current
    const name = studentNameRef.current
    if (!sid || !name || blob.size < 500) {
      // too short / silence — just go back to listening
      isMimiSpeakingRef.current = false
      setVadStatus('listening')
      return
    }
    isMimiSpeakingRef.current = true   // block VAD while processing
    setVadStatus('thinking')
    try {
      const token = localStorage.getItem('token')
      const form  = new FormData()
      form.append('audio', blob, 'audio.webm')
      form.append('session_id', sid)
      form.append('student_name', name)
      const res  = await axios.post(API_ENDPOINTS.MIMI_CHAT_AUDIO, form,
        { headers: { Authorization: `Bearer ${token}` } })
      const data = res.data?.data
      if (data?.farewell) {
        // Backend detected farewell — play goodbye audio then show GoodbyeScreen
        setMimiText(data.text || '')
        if (data.audio) {
          const bytes = Uint8Array.from(atob(data.audio), c => c.charCodeAt(0))
          const blob  = new Blob([bytes], { type: 'audio/mpeg' })
          const url   = URL.createObjectURL(blob)
          const audio = new Audio(url)
          currentAudioRef.current = audio
          const done = () => { URL.revokeObjectURL(url); currentAudioRef.current = null; setShowGoodbye(true); stopSessionRef.current && stopSessionRef.current() }
          audio.onended = done
          audio.onerror = done
          audio.play().catch(done)
        } else {
          setShowGoodbye(true)
          stopSessionRef.current && stopSessionRef.current()
        }
        return
      }
      if (data?.text) {
        setMimiText(data.text)
        setImageUrl(data.image_url || null)
        setYtVideo(data.yt_video || null)
        lastAnswerRef.current = data.text

        if (data.topics_list) {
          setTopicsList(data.topics_list)
          setShowTopics(true)
        } else if (data.topic) {
          setTopicsList(prev => {
            const key = data.topic.toLowerCase()
            if (prev.some(t => t.toLowerCase() === key)) return prev
            return [...prev, data.topic]
          })
        }

        setChatHistory(prev => [...prev, { q: '', a: data.text }])
        if (data.audio) {
          playMimiAudio(data.audio)
        } else {
          isMimiSpeakingRef.current = false
          setVadStatus('listening')
        }
      } else {
        isMimiSpeakingRef.current = false
        setVadStatus('listening')
      }
    } catch (e) {
      console.error('[AudioSend]', e)
      isMimiSpeakingRef.current = false
      setVadStatus('listening')
    }
  }, [playMimiAudio])

  // ── Resume recognition after Mimi finishes (or on error) ──────
  const resumeListening = useCallback(() => {
    isMimiSpeakingRef.current = false
    setIsSpeaking(false)
    setVadStatus('listening')
    if (recognitionRef.current && sessionIdRef.current) {
      try { recognitionRef.current.start() } catch {}
    }
  }, [])

  // ── Send transcribed text to Mimi (fast path) ─────────────────
  const sendTextToMimi = useCallback(async (text) => {
    const sid  = sessionIdRef.current
    const name = studentNameRef.current
    if (!sid || !text.trim()) return

    // Kill any currently-playing audio before we go async — prevents overlap
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }
    clearInterval(vadIntervalRef.current)

    isMimiSpeakingRef.current = true
    setVadStatus('thinking')
    try {
      const token = localStorage.getItem('token')
      const res   = await axios.post(API_ENDPOINTS.MIMI_TEXT_CHAT,
        { text, session_id: sid, student_name: name },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      const data = res.data?.data
      if (data?.text) {
        setMimiText(data.text)
        setImageUrl(data.image_url || null)
        setYtVideo(data.yt_video   || null)
        lastAnswerRef.current = data.text

        // Topic memory — update list & auto-show when topics_list returned
        if (data.topics_list) {
          setTopicsList(data.topics_list)
          setShowTopics(true)
        } else if (data.topic) {
          setTopicsList(prev => {
            const key = data.topic.toLowerCase()
            if (prev.some(t => t.toLowerCase() === key)) return prev
            return [...prev, data.topic]
          })
        }

        // Backend already saved Q&A to MongoDB synchronously before returning.
        // Increment local counter so the "X conversations" UI stays accurate.
        setChatHistory(prev => [...prev, { q: text, a: data.text }])

        if (data.audio) {
          playMimiAudio(data.audio)
        } else {
          setTimeout(resumeListening, 1500)
        }
      } else {
        resumeListening()
      }
    } catch (e) {
      console.error('[TextSend] Error — did you restart Docker?', e)
      resumeListening()
    }
  }, [playMimiAudio, resumeListening])

  // ── Web Speech API — real-time transcript, instant send ───────
  const recognitionRef = useRef(null)

  const stopVAD = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop() } catch {}
      recognitionRef.current = null
    }
    clearInterval(vadIntervalRef.current)
    clearTimeout(silenceTimerRef.current)
    vadIntervalRef.current  = null
    silenceTimerRef.current = null
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(t => t.stop())
      micStreamRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {})
      audioContextRef.current = null
    }
    isRecordingRef.current = false
    setVadStatus('idle')
  }, [])

  // ── Set up echo-cancelled mic for interrupt VAD ──────────────
  const setupMicVAD = useCallback(async () => {
    if (analyserRef.current) return           // already set up
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
      })
      micStreamRef.current = stream
      const ctx = new (window.AudioContext || window.webkitAudioContext)()
      audioContextRef.current = ctx
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 512
      analyser.smoothingTimeConstant = 0.4
      ctx.createMediaStreamSource(stream).connect(analyser)
      analyserRef.current = analyser
    } catch (e) {
      console.warn('[VAD] Mic setup failed, voice interrupt disabled:', e)
    }
  }, [])

  // ── Interrupt handler: stop Mimi's audio only — recognition keeps running ────
  // Recognition is continuous (see startVAD) so we never stop/restart it here.
  // justInterruptedRef gives a 500ms echo-clear window: recognition results that
  // arrive right after Mimi stops (her buffered voice) are silently discarded.
  // "bye" is exempt from the window — it is always processed immediately.
  const doInterrupt = useCallback(() => {
    clearInterval(vadIntervalRef.current)
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }
    isMimiSpeakingRef.current = false
    setIsSpeaking(false)
    setVadStatus('interrupted')               // flash "Got it!" for 400ms
    justInterruptedRef.current = Date.now()   // start 200ms echo-clear window
    setTimeout(() => setVadStatus('listening'), 400)
    // Always kill the old recognition (it was discarding results while Mimi spoke)
    // and start a fresh one so the child's interrupting voice is captured.
    if (recognitionRef.current) {
      try { recognitionRef.current.stop() } catch {}
      recognitionRef.current = null
    }
    if (sessionIdRef.current && startVADRef.current) {
      startVADRef.current()
    }
  }, [])

  useEffect(() => { doInterruptRef.current = doInterrupt }, [doInterrupt])

  // ── Voice-triggered goodbye: play warm farewell THEN stop session ──────────
  const goodbyeInProgressRef = useRef(false)
  const sayGoodbyeAndStop = useCallback(async () => {
    if (goodbyeInProgressRef.current) return   // prevent double-fire
    goodbyeInProgressRef.current = true
    // Freeze recognition and current audio immediately
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }
    clearInterval(vadIntervalRef.current)
    if (recognitionRef.current) {
      try { recognitionRef.current.stop() } catch {}
      recognitionRef.current = null
    }
    isMimiSpeakingRef.current = false
    setIsSpeaking(true)   // keep speaking indicator while goodbye plays
    setVadStatus('idle')  // prevent recognition from restarting

    const msg = getGoodbyeQuote()
    setMimiText(msg)

    // Show goodbye screen immediately — TTS plays in background
    setIsSpeaking(false)
    setShowGoodbye(true)
    stopSessionRef.current && stopSessionRef.current()
    // NOTE: goodbyeInProgressRef stays true — reset only on next session start

    // Play Mimi's voice for the goodbye quote
    try {
      const token = localStorage.getItem('token')
      const res = await axios.post(API_ENDPOINTS.MIMI_SPEAK, { text: msg },
        { headers: { Authorization: `Bearer ${token}` } })
      if (res.data?.audio) {
        const bytes = Uint8Array.from(atob(res.data.audio), c => c.charCodeAt(0))
        const blob  = new Blob([bytes], { type: 'audio/mpeg' })
        const url   = URL.createObjectURL(blob)
        const audio = new Audio(url)
        currentAudioRef.current = audio
        const cleanup = () => { URL.revokeObjectURL(url); currentAudioRef.current = null }
        audio.onended = cleanup
        audio.onerror = cleanup
        audio.play().catch(cleanup)
      }
    } catch (err) {
      console.error('[Goodbye TTS]', err)
    }
  }, [])

  useEffect(() => { sayGoodbyeAndStopRef.current = sayGoodbyeAndStop }, [sayGoodbyeAndStop])

  const startVAD = useCallback(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) { setVadStatus('listening'); return }

    if (recognitionRef.current) {
      try { recognitionRef.current.stop() } catch {}
      recognitionRef.current = null
    }

    let silenceTimer  = null
    let pendingText   = ''

    const _sendNow = (text) => {
      clearTimeout(silenceTimer)
      silenceTimer = null
      pendingText  = ''
      if (text.trim() && !isMimiSpeakingRef.current && sessionIdRef.current) {
        setVadStatus('thinking')
        sendTextToMimi(text.trim())
      }
    }

    const BYE_PHRASES = [
      'bye', 'goodbye', 'bye mimi', 'stop session', 'end session',
      'goodnight', 'good night', 'see you', 'i have to go',
      'bye bye', 'ok bye', 'tata', 'stop mimi', 'close session',
      'exit', 'quit', 'stop learning', 'i am done', "i'm done",
      'band karo', 'bas karo', 'rukjao', 'ruk jao', 'alvida',
      'phir milenge', 'kal milenge', 'chalo bye', 'ok goodbye',
      'see you later', 'see ya', 'i want to stop',
      // Google STT (en-IN) often transcribes "bye" as "by"
      'by mimi', 'by mini', 'ok by', 'chalo by',
    ]

    // Extra check: exact short words + common STT misrecognitions of "bye"
    // en-IN Google STT: "bye" → "by" / "buy" / "bi"
    const isBye = (t) =>
      BYE_PHRASES.some(p => t.includes(p)) ||
      t === 'by' || t === 'bye' || t === 'buy' || t === 'bi' ||
      t === 'by mimi' || t === 'buy mimi' || t === 'buy mini' || t === 'bi mimi'

    const recognition           = new SR()
    recognition.lang            = 'en-IN'
    recognition.continuous      = false  // short-lived per-utterance sessions — far more stable
    recognition.interimResults  = true   // interim results let us catch "bye" before isFinal
    recognition.maxAlternatives = 1

    recognition.onstart = () => setVadStatus('listening')

    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result     = event.results[i]
        const transcript = result[0].transcript
        const lower      = transcript.toLowerCase().trim()
        if (!lower) continue

        // ── BYE CHECK: always first — exempt from all guards ──────────
        // Fires on interim AND final, during Mimi speaking AND silence.
        if (isBye(lower)) {
          clearTimeout(silenceTimer)
          sayGoodbyeAndStopRef.current
            ? sayGoodbyeAndStopRef.current()
            : stopSessionRef.current && stopSessionRef.current()
          return
        }

        // ── Discard while Mimi is speaking (echo of her voice) ────────
        if (isMimiSpeakingRef.current) return

        // ── 200ms echo-clear window after VAD interrupt ───────────────
        if (Date.now() - justInterruptedRef.current < 200) return

        // ── Normal listening ──────────────────────────────────────────
        if (result.isFinal) {
          _sendNow(transcript)
        } else {
          pendingText = transcript
          setVadStatus('user_speaking')
          clearTimeout(silenceTimer)
          // 3 s gives children time to pause mid-thought without triggering an early send
          silenceTimer = setTimeout(() => _sendNow(pendingText), 3000)
        }
      }
    }

    recognition.onerror = (e) => {
      if (e.error === 'no-speech') return
      if (e.error === 'aborted')   return
      console.warn('[Speech]', e.error)
      // Network error: Chrome's WebSocket to Google dropped — restart after 1s
      if (e.error === 'network' && sessionIdRef.current) {
        setTimeout(() => {
          if (sessionIdRef.current && !isMimiSpeakingRef.current && startVADRef.current) {
            startVADRef.current()
          }
        }, 1000)
      }
    }

    recognition.onend = () => {
      clearTimeout(silenceTimer)
      // Bye phrase detected via pending interim text (recognition ended before final)
      const pendingLower = pendingText.toLowerCase().trim()
      if (pendingLower && isBye(pendingLower)) {
        pendingText = ''
        sayGoodbyeAndStopRef.current
          ? sayGoodbyeAndStopRef.current()
          : stopSessionRef.current && stopSessionRef.current()
        return
      }
      if (pendingText.trim() && !isMimiSpeakingRef.current) _sendNow(pendingText)
      pendingText = ''
      // Restart immediately — recognitionRef guard prevents duplicate restarts
      if (sessionIdRef.current && !isMimiSpeakingRef.current && recognitionRef.current === recognition) {
        try { recognition.start() } catch { if (startVADRef.current) startVADRef.current() }
      }
    }

    recognition.start()
    recognitionRef.current = recognition
  }, [sendTextToMimi, playMimiAudio])

  // Keep startVADRef in sync so playMimiAudio can call it without circular dep
  useEffect(() => { startVADRef.current = startVAD }, [startVAD])

  // ── Poll /mimi-get — catches proactive Mimi messages ──────────
  const startPolling = useCallback((name, sid) => {
    if (pollingRef.current) return
    const token = localStorage.getItem('token')
    pollingRef.current = setInterval(async () => {
      if (isMimiSpeakingRef.current) return
      try {
        const res = await axios.get(
          `${API_ENDPOINTS.GET_MIMI_STATUS}?session_id=${sid}`,
          { headers: { Authorization: `Bearer ${token}` } }
        )
        const d = res.data
        if (!d.text || d.text === 'Thinking...' || d.text === lastAnswerRef.current) return
        lastAnswerRef.current = d.text
        setMimiText(d.text)
        setImageUrl(d.image_url || null)
        setYtVideo(d.yt_video || null)
        if (d.audio) playMimiAudio(d.audio)
      } catch {}
    }, 1500)
  }, [playMimiAudio])

  // ── Mimi session ─────────────────────────────────────────────
  const startMimiSession = useCallback(async (name) => {
    if (sessionIdRef.current) {
      console.log('[Mimi] Session already active, skipping duplicate call')
      return
    }
    // Set up echo-cancelled mic for interrupt detection (non-blocking)
    setupMicVAD().catch(() => {})
    goodbyeInProgressRef.current = false   // reset so next session can detect farewell
    const sid = generateSessionId()
    setSessionId(sid)
    sessionIdRef.current   = sid
    studentNameRef.current = name
    setSessionState('running')
    try {
      const token = localStorage.getItem('token')
      let studentId = ''
      try {
        const idRes = await axios.post(API_ENDPOINTS.GET_STUDENT_ID,
          { name }, { headers: { Authorization: `Bearer ${token}` } })
        studentId = idRes.data.student_id || ''
      } catch {}
      const res = await axios.post(API_ENDPOINTS.START_MIMI_SESSION,
        { student_name: name, session_id: sid, student_id: studentId },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      // Play greeting, then start VAD
      const greeting = res.data
      if (greeting.greeting_text) setMimiText(greeting.greeting_text)
      if (greeting.greeting_audio) {
        playMimiAudio(greeting.greeting_audio, () => startVAD())
      } else {
        startVAD()
      }
    } catch (e) {
      console.error('Mimi session start error:', e)
      startVAD()
    }
    startPolling(name, sid)
  }, [startPolling, startVAD, playMimiAudio, setupMicVAD]) // eslint-disable-line
  
  // ── Stop session ──────────────────────────────────────────────
  const stopSession = useCallback(() => {
    // 1. Kill audio immediately — no await, no delay
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }
    isMimiSpeakingRef.current = false

    // 2. Kill all timers & polling
    clearInterval(pollingRef.current)
    clearInterval(facePollingRef.current)
    clearTimeout(faceTimeoutRef.current)
    pollingRef.current     = null
    facePollingRef.current = null
    faceTimeoutRef.current = null

    // 3. Kill recognition & webcam
    stopVAD()
    stopWebcam()
    setShowManualEntry(false)

    // 4. Snapshot refs then clear them so any in-flight callbacks are rejected
    const sid  = sessionIdRef.current
    const name = studentNameRef.current
    sessionIdRef.current   = ''
    studentNameRef.current = ''

    // 5. Update UI immediately (no await)
    setSessionState('stopped')
    setIsSpeaking(false)
    setVadStatus('idle')

    // 6. Notify backend in background (fire-and-forget, don't block UI)
    if (sid) {
      axios.post(API_ENDPOINTS.MIMI_STOP_SESSION,
        { session_id: sid, student_name: name, send_whatsapp: false }
      ).catch(e => console.error('Stop error:', e))
    }
  }, [stopWebcam, stopVAD])

  // Keep stopSessionRef in sync so recognition handlers can call it
  useEffect(() => { stopSessionRef.current = stopSession }, [stopSession])

  // ── Typewriter ────────────────────────────────────────────────
  useEffect(() => {
    if (!mimiText) { setDisplayedText(''); setIsTyping(false); return }
    setDisplayedText('')
    setIsTyping(true)
    const chars = Array.from(mimiText)
    let i = 0
    const t = setInterval(() => {
      i += 1
      setDisplayedText(chars.slice(0, i).join(''))
      if (i >= chars.length) {
        clearInterval(t)
        setIsTyping(false)
        setIsSpeaking(false) // typing khatam = speaking khatam
      }
    }, 15)
    return () => clearInterval(t)
  }, [mimiText])

  // ── Cleanup ───────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      clearInterval(pollingRef.current)
      clearInterval(facePollingRef.current)
      stopWebcam()
    }
  }, [stopWebcam])


  return (
    <div className="relative min-h-screen w-full bg-cover bg-center overflow-hidden"
      style={{ backgroundImage: `url(${bgImage})` }}>

      {/* ── Goodbye Screen Overlay ────────────────────────────── */}
      <AnimatePresence>
        {showGoodbye && (
          <Motion.div
            key="goodbye"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9999] bg-gradient-to-b from-purple-100 to-pink-100"
          >
            <GoodbyeScreen
              studentName={studentName || 'Superstar'}
              totalStars={Math.floor(Math.random() * 2) + 4}
              onComplete={() => {
                setShowGoodbye(false)
                setSessionState('idle')
                setStudentName('')
                setMimiText('')
                setChatHistory([])
                setTopicsList([])
              }}
            />
          </Motion.div>
        )}
      </AnimatePresence>

      {/* Hidden canvas for capturing frames */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {/* ── Top Bar ────────────────────────────────────────────── */}
      <div className="absolute top-6 right-6 z-50 flex items-center gap-3">
        {studentName && (
          <div className="flex items-center gap-2 px-4 py-2 bg-white/90 rounded-full font-bold text-purple-700 shadow-lg">
            👤 {studentName}
          </div>
        )}
        {(sessionState === 'idle' || sessionState === 'stopped') && (
          <Motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
            onClick={startFaceDetection}
            className="px-6 py-3 rounded-full text-white bg-indigo-600 font-bold shadow-lg">
            🎤 Start Mimi Chat
          </Motion.button>
        )}
        {sessionState === 'running' && topicsList.length > 0 && (
          <Motion.button
            whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
            onClick={() => setShowTopics(v => !v)}
            className="px-4 py-2 rounded-full bg-amber-100 text-amber-700 font-bold shadow text-sm border border-amber-300">
            📚 Topics ({topicsList.length})
          </Motion.button>
        )}
        {sessionState === 'running' && (
          <>
            <Motion.div
              animate={vadStatus === 'user_speaking' || vadStatus === 'interrupted' ? { scale: [1, 1.1, 1] } : {}}
              transition={{ repeat: Infinity, duration: 0.5 }}
              className={`px-5 py-2 rounded-full text-sm font-bold shadow-lg ${
                vadStatus === 'listening'     ? 'bg-green-100 text-green-700' :
                vadStatus === 'user_speaking' ? 'bg-red-100 text-red-600 animate-pulse' :
                vadStatus === 'thinking'      ? 'bg-yellow-100 text-yellow-700' :
                vadStatus === 'mimi_speaking' ? 'bg-purple-100 text-purple-700' :
                vadStatus === 'interrupted'   ? 'bg-cyan-100 text-cyan-700 animate-pulse' :
                'bg-gray-100 text-gray-500'
              }`}
            >
              {vadStatus === 'listening'     && '🎤 Listening...'}
              {vadStatus === 'user_speaking' && '🔴 Speaking...'}
              {vadStatus === 'thinking'      && '⏳ Thinking...'}
              {vadStatus === 'mimi_speaking' && '🔊 Mimi Speaking...'}
              {vadStatus === 'interrupted'   && '⚡ Got it!'}
              {vadStatus === 'idle'          && '⚪ Starting...'}
            </Motion.div>
            <Motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
              onClick={stopSession}
              className="px-6 py-3 rounded-full text-white bg-red-500 font-bold shadow-lg">
              ⏹ Stop
            </Motion.button>
          </>
        )}
        <div className={`px-4 py-2 rounded-full text-sm font-bold ${
          sessionState === 'running'   ? 'bg-green-100 text-green-700'   :
          sessionState === 'detecting' ? 'bg-yellow-100 text-yellow-700' :
          sessionState === 'stopped'   ? 'bg-gray-100 text-gray-600'     :
          'bg-gray-100 text-gray-500'
        }`}>
          {sessionState === 'idle'      && '⚪ Ready'}
          {sessionState === 'detecting' && '📷 Scanning...'}
          {sessionState === 'running'   && '🟢 Active'}
          {sessionState === 'stopped'   && '🔴 Stopped'}
        </div>
      </div>

      {/* ── Face Detection Overlay ─────────────────────────────── */}
      <AnimatePresence>
        {sessionState === 'detecting' && (
          <Motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0 z-30 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <Motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }}
              className="bg-white rounded-[2.5rem] p-8 text-center shadow-2xl max-w-lg w-full mx-4 border-4 border-purple-100">
              
              <div className="relative w-full aspect-video bg-gray-100 rounded-3xl overflow-hidden mb-6 shadow-inner border-2 border-purple-50">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover scale-x-[-1]" // Mirror effect
                />
                <div className="absolute inset-0 border-[3px] border-dashed border-purple-400/50 rounded-3xl pointer-events-none animate-pulse" />
                {!webcamActive && (
                  <div className="absolute inset-0 flex items-center justify-center bg-gray-50/80">
                    <p className="text-purple-400 font-bold">Requesting camera access...</p>
                  </div>
                )}
              </div>

              <h2 className="text-3xl font-black text-purple-700 mb-2">Who is there?</h2>
              <p className="text-purple-500 text-lg mb-6 tracking-wide">Align your face with the frame...</p>
              
              <div className="flex justify-center gap-3">
                {[0, 1, 2].map(i => (
                  <Motion.div key={i}
                    animate={{ y: [0, -10, 0], opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                    className="w-4 h-4 bg-purple-500 rounded-full shadow-sm" />
                ))}
              </div>

              {showManualEntry && (
                <div className="mt-4 space-y-3">
                  <p className="text-sm text-orange-500 font-semibold">Face not recognized. Enter name manually:</p>
                  <input
                    type="text"
                    value={manualName}
                    onChange={e => setManualName(e.target.value)}
                    placeholder="Student name..."
                    className="w-full px-4 py-3 rounded-xl border-2 border-purple-200 focus:border-purple-500 outline-none text-gray-700 text-center font-semibold"
                    onKeyDown={e => {
                      if (e.key === 'Enter' && manualName.trim()) {
                        clearInterval(facePollingRef.current)
                        clearTimeout(faceTimeoutRef.current)
                        facePollingRef.current = null
                        stopWebcam()
                        setShowManualEntry(false)
                        setStudentName(manualName.trim())
                        startMimiSession(manualName.trim())
                      }
                    }}
                  />
                  <button
                    onClick={() => {
                      if (!manualName.trim()) return
                      clearInterval(facePollingRef.current)
                      clearTimeout(faceTimeoutRef.current)
                      facePollingRef.current = null
                      stopWebcam()
                      setShowManualEntry(false)
                      setStudentName(manualName.trim())
                      startMimiSession(manualName.trim())
                    }}
                    disabled={!manualName.trim()}
                    className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-xl disabled:opacity-40"
                  >
                    Start Session →
                  </button>
                </div>
              )}

              <button
                onClick={stopSession}
                className="mt-6 text-gray-400 hover:text-red-500 transition-colors text-sm font-bold uppercase tracking-widest"
              >
                Cancel
              </button>
            </Motion.div>
          </Motion.div>
        )}
      </AnimatePresence>


      {/* ── Session Stopped Screen ─────────────────────────────── */}
      <AnimatePresence>
        {sessionState === 'stopped' && (
          <Motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0 z-30 flex items-center justify-center bg-black/50">
            <Motion.div initial={{ scale: 0.8 }} animate={{ scale: 1 }}
              className="bg-white rounded-3xl px-12 py-10 text-center shadow-2xl max-w-md">
              <div className="text-7xl mb-4">✅</div>
              <h2 className="text-3xl font-black text-green-700 mb-2">Session Complete!</h2>
              <p className="text-gray-500 mb-2">
                <strong>{chatHistory.length}</strong> conversations saved for{' '}
                <strong>{studentName}</strong>
              </p>
              <p className="text-xs text-gray-400 mb-6">Python server is still running ✅</p>
              <button onClick={() => {
                  setSessionState('idle')
                  setStudentName('')
                  setChatHistory([])
                  setMimiText('')
                  setImageUrl(null)
                  setYtVideo(null)
                  setIsSpeaking(false)
                  setTopicsList([])
                  setShowTopics(false)
                }}
                className="px-8 py-3 bg-purple-600 text-white font-black rounded-2xl shadow-lg hover:bg-purple-700">
                🔄 Start New Session
              </button>
            </Motion.div>
          </Motion.div>
        )}
      </AnimatePresence>

      {/* ── Layout: Mimi left, Response right ─────────────────── */}
      <div className="absolute inset-0 flex items-end">

        {/* ── Mimi Character — LEFT ───────────────────────────── */}
        <MimiCharacter
          vadStatus={vadStatus}
          isSpeaking={isSpeaking}
          sessionState={sessionState}
        />

        {/* ── Response Box — RIGHT ────────────────────────────── */}
        <div className="flex-1 flex flex-col justify-center z-20 pr-6 pb-8 pl-4"
          style={{ maxHeight: '90vh', overflowY: 'auto' }}>
          <AnimatePresence mode="wait">
            {mimiText && sessionState === 'running' && (
              <Motion.div
                key="mimi-response"
                initial={{ opacity: 0, x: 50, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 30, scale: 0.97 }}
                transition={{ type: 'spring', stiffness: 260, damping: 22 }}
                className="bg-white rounded-3xl shadow-2xl overflow-hidden"
                style={{ border: '3px solid', borderColor: isSpeaking ? '#a78bfa' : '#e0e7ff' }}
              >
                {/* Mimi label strip */}
                <div className={`flex items-center gap-2 px-5 py-2.5 ${isSpeaking ? 'bg-purple-100' : 'bg-indigo-50'}`}>
                  <Motion.div
                    className="text-xl"
                    animate={isSpeaking ? { scale: [1, 1.3, 1] } : {}}
                    transition={{ duration: 0.5, repeat: Infinity }}
                  >
                    {isSpeaking ? '🔊' : '💬'}
                  </Motion.div>
                  <span className="text-sm font-black text-purple-700 tracking-wide">
                    {isSpeaking ? 'Mimi is talking...' : 'Mimi says'}
                  </span>
                  {isTyping && (
                    <Motion.div
                      className="ml-auto flex gap-1"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                    >
                      {[0, 1, 2].map(i => (
                        <Motion.div
                          key={i}
                          className="w-2 h-2 bg-purple-400 rounded-full"
                          animate={{ y: [0, -5, 0] }}
                          transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.15 }}
                        />
                      ))}
                    </Motion.div>
                  )}
                </div>

                <div className="px-6 py-5">
                  <p className="text-2xl font-semibold text-gray-800 leading-relaxed min-h-[64px]">
                    {displayedText}
                    {isTyping && (
                      <Motion.span
                        className="ml-1 inline-block w-0.5 h-6 bg-purple-400 rounded align-middle"
                        animate={{ opacity: [1, 0, 1] }}
                        transition={{ duration: 0.7, repeat: Infinity }}
                      />
                    )}
                  </p>

                  {/* Image — shown immediately, hides when video plays */}
                  {imageUrl && !playing && (
                    <Motion.div
                      className="mt-4"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.4 }}>
                      <img src={imageUrl} alt="mimi result"
                        referrerPolicy="no-referrer"
                        className="w-full max-h-56 object-cover mx-auto rounded-2xl shadow-lg" />
                      {ytVideo && (
                        <p className="text-center text-xs text-purple-500 font-semibold mt-2 animate-pulse">
                          🎬 Video loading soon...
                        </p>
                      )}
                    </Motion.div>
                  )}

                  {/* Video — auto-plays after 5s if image shown, else immediately */}
                  {ytVideo && playing && (
                    <Motion.div
                      className="mt-4"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4 }}>
                      <iframe
                        src={`https://www.youtube.com/embed/${extractYoutubeId(ytVideo)}?autoplay=1&rel=0&modestbranding=1`}
                        title="YouTube video"
                        allow="autoplay; encrypted-media; fullscreen"
                        allowFullScreen
                        className="w-full h-52 rounded-2xl shadow-lg" />
                    </Motion.div>
                  )}
                </div>
              </Motion.div>
            )}
          </AnimatePresence>

          {/* ── Topic Chips Panel ──────────────────────────────── */}
          <AnimatePresence>
            {showTopics && topicsList.length > 0 && sessionState === 'running' && (
              <Motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                transition={{ duration: 0.3 }}
                className="mt-4 bg-white/95 rounded-2xl p-4 shadow-xl border border-amber-100">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-black text-amber-700">📚 Topics we've explored</p>
                  <button onClick={() => setShowTopics(false)} className="text-gray-400 hover:text-gray-600 text-xs font-bold">✕</button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {topicsList.map((topic, i) => (
                    <Motion.button
                      key={i}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => {
                        setShowTopics(false)
                        sendTextToMimi(`Tell me more about ${topic}`)
                      }}
                      className="px-3 py-1.5 bg-gradient-to-r from-amber-100 to-orange-100 text-amber-800 rounded-full text-sm font-bold shadow-sm border border-amber-200 hover:from-amber-200 hover:to-orange-200 transition-colors">
                      {topic}
                    </Motion.button>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-2">Tap any topic to explore it deeper!</p>
              </Motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── Chat History Sidebar ─────────────────────────────────
      {chatHistory.length > 0 && sessionState === 'running' && (
        <div className="absolute top-24 right-6 z-40 w-64 max-h-[50vh] overflow-y-auto">
          <div className="bg-white/90 backdrop-blur rounded-2xl p-4 shadow-xl">
            <p className="font-black text-purple-700 mb-3 text-sm">
              💬 Chat History ({studentName})
            </p>
            <div className="space-y-3">
              {chatHistory.map((c, i) => (
                <div key={i} className="border-b border-purple-100 pb-2 last:border-0">
                  <p className="text-sm text-gray-700 font-medium">{c.answer}</p>
                  <p className="text-xs text-gray-400 mt-1">{c.time}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )} */}

    </div>
  )
}

function extractYoutubeId(url) {
  if (!url) return ''
  const m = url.match(/(youtu\.be\/|v=|embed\/)([A-Za-z0-9_-]{6,})/)
  return m ? m[2] : url
}

export default MimiChat

// ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


// import React, { useState, useEffect, useRef } from 'react'
// import axios from 'axios'
// import { motion as Motion, AnimatePresence } from 'framer-motion'
// import { API_ENDPOINTS } from '../config'

// import bgImage from '../assets/images/mimi/bg.jpg'
// import mimiIdleVideo from '../assets/images/mimi/mimiidell_nobg.webm'
// import mimiWaveVideo from '../assets/images/mimi/mimiwavehand_nobg.webm'

// const MimiChat = () => {
//   const [sessionState, setSessionState] = useState('idle')
//   const [mimiText, setMimiText] = useState('')
//   const [imageUrl, setImageUrl] = useState(null)
//   const [ytVideo, setYtVideo] = useState(null)
//   const [playing, setPlaying] = useState(false)
//   const [displayedText, setDisplayedText] = useState('')
//   const [isTyping, setIsTyping] = useState(false)

//   const pollingRef = useRef(null)

//   const startSession = async () => {
//     try {
//       await axios.get(API_ENDPOINTS.START_MIMI_SESSION)
//       setSessionState('running')
//       startPolling()
//     } catch (e) {
//       console.error(e)
//     }
//   }

//   const startPolling = () => {
//     if (pollingRef.current) return
//     pollingRef.current = setInterval(async () => {
//       try {
//         const res = await axios.get(API_ENDPOINTS.GET_MIMI_STATUS)
//         const d = res.data

//         if (d.text === "Thinking..." || !d.text) {
//         } else {
//           setMimiText(d.text)
//           setImageUrl(d.image_url)
//           setYtVideo(d.yt_video)
//           setSessionState(d.action || 'idle')
//         }

//         if (d.action === 'playing_video' && d.yt_video) setPlaying(true)
//       } catch (e) {
//         console.error('Mimi poll error', e)
//       }
//     }, 500)
//   }

//   useEffect(() => {
//     if (!mimiText) {
//       setDisplayedText('')
//       setIsTyping(false)
//       return
//     }

//     setDisplayedText('')
//     setIsTyping(true)

//     const chars = Array.from(mimiText)
//     let i = 0
//     const speed = 30

//     const t = setInterval(() => {
//       i += 1
//       setDisplayedText(chars.slice(0, i).join(''))
//       if (i >= chars.length) {
//         clearInterval(t)
//         setIsTyping(false)
//       }
//     }, speed)

//     return () => clearInterval(t)
//   }, [mimiText])

//   useEffect(() => {
//     if (!displayedText || isTyping) return

//     try {
//       if ('speechSynthesis' in window) {
//         window.speechSynthesis.cancel()
//         const u = new SpeechSynthesisUtterance(mimiText || displayedText)
//         u.lang = 'en-US'
//         u.rate = 0.95
//       }
//     } catch (e) {
//       console.warn('Browser TTS failed', e)
//     }
//   }, [displayedText, isTyping, mimiText])

//   useEffect(() => {
//     return () => {
//       if (pollingRef.current) clearInterval(pollingRef.current)
//     }
//   }, [])

//   return (
//     <div
//       className="relative min-h-screen w-full bg-cover bg-center overflow-hidden px-4 sm:px-6"
//       style={{ backgroundImage: `url(${bgImage})` }}
//     >
//       {/* Buttons */}
//       <div className="absolute top-4 right-4 sm:top-8 sm:right-8 z-50 flex flex-wrap gap-2">
//         <Motion.button
//           onClick={startSession}
//           disabled={sessionState !== 'idle'}
//           className="px-4 sm:px-6 py-2 sm:py-3 rounded-full text-white bg-indigo-600 text-sm sm:text-base"
//         >
//           {sessionState === 'idle' ? 'Start Mimi Chat' : 'Session Running'}
//         </Motion.button>

//         <Motion.button
//           onClick={() => {
//             setSessionState('running')
//             setMimiText('The sun is big and bright. It gives us light and keeps us warm.')
//             setImageUrl('https://via.placeholder.com/600x360?text=Sun+Image')
//             setYtVideo('https://www.youtube.com/watch?v=ysz5S6PUM-U')
//             setPlaying(false)
//           }}
//           className="px-3 sm:px-4 py-2 rounded-full bg-white border border-gray-200 text-gray-800 shadow-sm text-sm"
//         >
//           Demo Response
//         </Motion.button>
//       </div>

//       {/* Mimi Character */}
//       <Motion.div
//         className="absolute bottom-0 z-50 
//         w-[220px] h-[220px]
//         sm:w-[300px] sm:h-[300px]
//         md:w-[380px] md:h-[380px]
//         lg:w-[450px] lg:h-[450px]
//         xl:w-[520px] xl:h-[520px]"
//         animate={mimiText ? { left: '10px', x: 0 } : { left: '50%', x: '-50%' }}
//         transition={{ type: 'spring', stiffness: 120, damping: 18 }}
//       >
//         <video
//           src={mimiText ? mimiIdleVideo : (sessionState === 'running' ? mimiWaveVideo : mimiIdleVideo)}
//           autoPlay
//           loop
//           muted
//           playsInline
//           className="w-full h-full object-contain"
//         />
//       </Motion.div>

//       {/* Response Box */}
//       <div className="
//         absolute z-40 pointer-events-none
//         top-20
//         left-1/2 -translate-x-1/2
//         w-[95%]
//         sm:w-[85%]
//         md:w-[70%]
//         lg:w-[600px]
//         xl:w-[700px]
//         md:left-[380px] md:translate-x-0
//         lg:left-[420px]
//       ">
//         <AnimatePresence>
//           {(mimiText || imageUrl || ytVideo) && (
//             <Motion.div
//               initial={{ opacity: 0, y: -20, scale: 0.98 }}
//               animate={{ opacity: 1, y: 0, scale: 1 }}
//               exit={{ opacity: 0, y: -10 }}
//               transition={{ duration: 0.35 }}
//               className="bg-white rounded-2xl p-4 sm:p-6 shadow-2xl pointer-events-auto"
//             >
//               <p className="text-lg sm:text-xl md:text-2xl font-semibold text-gray-800 min-h-[64px]">
//                 {displayedText}
//                 <span className={`ml-1 text-gray-700 ${isTyping ? 'animate-pulse' : ''}`}>
//                   {isTyping ? '|' : ''}
//                 </span>
//               </p>

//               {imageUrl && (
//                 <div className="mt-4">
//                   <img
//                     src={imageUrl}
//                     alt="mimi result"
//                     referrerPolicy="no-referrer"
//                     className="max-h-64 w-full object-contain mx-auto rounded-md"
//                   />
//                 </div>
//               )}

//               {ytVideo && (
//                 <div className="mt-4">
//                   {!playing ? (
//                     <button
//                       onClick={() => setPlaying(true)}
//                       className="px-4 py-2 bg-blue-600 text-white rounded"
//                     >
//                       Play Video
//                     </button>
//                   ) : (
//                     <div className="w-full aspect-video">
//                       <iframe
//                         src={`https://www.youtube.com/embed/${extractYoutubeId(ytVideo)}?autoplay=1`}
//                         title="YouTube video"
//                         allow="autoplay; encrypted-media"
//                         className="w-full h-full rounded"
//                       />
//                     </div>
//                   )}
//                 </div>
//               )}
//             </Motion.div>
//           )}
//         </AnimatePresence>
//       </div>
//     </div>
//   )
// }

// function extractYoutubeId(url) {
//   if (!url) return ''
//   const m = url.match(/(youtu\.be\/|v=|embed\/)([A-Za-z0-9_-]{6,})/)
//   return m ? m[2] : url
// }

// export default MimiChat;
