import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../../../config';
import { Camera, CheckCircle, AlertCircle, User } from 'lucide-react';

const FaceRegistration = () => {
  const [students, setStudents] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [captured, setCaptured] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    fetch(`${API_BASE_URL}/api/admin/all-students`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(res => res.json())
      .then(data => { if (Array.isArray(data)) setStudents(data); })
      .catch(() => setStatus({ type: 'error', msg: 'Failed to load students.' }));
  }, []);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      videoRef.current.play();
      setStreaming(true);
      setCaptured(null);
      setStatus(null);
    } catch {
      setStatus({ type: 'error', msg: 'Camera access denied. Please allow camera permission.' });
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    setStreaming(false);
  };

  const capturePhoto = () => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    setCaptured(canvas.toDataURL('image/jpeg'));
    stopCamera();
  };

  const handleRegister = async () => {
    const student = students.find(s => s._id === selectedStudent);
    if (!student) return;
    setLoading(true);
    setStatus(null);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/register-face`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: student.name, image: captured }),
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setStatus({ type: 'success', msg: `Face registered successfully for ${student.name}!` });
        setCaptured(null);
        setSelectedStudent('');
        setStudents(prev => prev.map(s => s._id === selectedStudent ? { ...s, face_registered: true } : s));
      } else {
        setStatus({ type: 'error', msg: data.message || 'Registration failed.' });
      }
    } catch {
      setStatus({ type: 'error', msg: 'Server error. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const step1Done = !!selectedStudent;
  const step2Done = !!captured;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-4xl font-bold text-text mb-1">Face Registration</h1>
        <p className="text-text/60">Register a student's face for attendance recognition</p>
      </div>

      {/* Status Message */}
      {status && (
        <div className={`flex items-center gap-3 p-4 rounded-xl font-medium ${
          status.type === 'success'
            ? 'bg-green-50 text-green-700 border border-green-200'
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {status.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
          {status.msg}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* LEFT — Step 1 + Step 3 */}
        <div className="space-y-4">

          {/* Step 1: Select Student */}
          <div className={`bg-white rounded-2xl border-2 p-5 space-y-3 ${step1Done ? 'border-green-400' : 'border-orange-400'}`}>
            <div className="flex items-center gap-2">
              <span className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold text-white ${step1Done ? 'bg-green-500' : 'bg-orange-400'}`}>
                {step1Done ? '✓' : '1'}
              </span>
              <span className="font-semibold text-gray-800">Select Student</span>
              {!step1Done && <span className="text-xs text-orange-500 font-medium ml-auto">← Do this first</span>}
            </div>
            <div className="relative">
              <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <select
                value={selectedStudent}
                onChange={e => setSelectedStudent(e.target.value)}
                className="w-full pl-9 pr-4 py-3 rounded-xl border-2 border-gray-200 focus:border-blue-400 outline-none text-gray-700 bg-gray-50"
              >
                <option value="">-- Choose a student --</option>
                {students.map(s => (
                  <option key={s._id} value={s._id}>
                    {s.name}{s.face_registered ? ' ✓' : ''}
                  </option>
                ))}
              </select>
            </div>
            {selectedStudent && (
              <p className="text-sm text-green-600 font-medium">
                ✓ Selected: {students.find(s => s._id === selectedStudent)?.name}
              </p>
            )}
          </div>

          {/* Step 3: Register Button */}
          <div className={`bg-white rounded-2xl border-2 p-5 space-y-3 ${step1Done && step2Done ? 'border-pink-400' : 'border-gray-200'}`}>
            <div className="flex items-center gap-2">
              <span className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold text-white ${step1Done && step2Done ? 'bg-pink-500' : 'bg-gray-300'}`}>
                3
              </span>
              <span className="font-semibold text-gray-800">Register Face</span>
            </div>

            {!step1Done && (
              <p className="text-sm text-gray-400">Select a student first (Step 1)</p>
            )}
            {step1Done && !step2Done && (
              <p className="text-sm text-gray-400">Capture a photo first (Step 2)</p>
            )}

            <button
              onClick={handleRegister}
              disabled={loading || !step1Done || !step2Done}
              className="w-full py-3 bg-gradient-to-r from-pink-500 to-orange-400 text-white font-bold text-base rounded-xl transition-opacity disabled:opacity-30 disabled:cursor-not-allowed"
            >
              {loading ? 'Registering...' : 'Register Face'}
            </button>
          </div>
        </div>

        {/* RIGHT — Step 2: Camera */}
        <div className={`bg-white rounded-2xl border-2 p-5 space-y-3 ${step2Done ? 'border-green-400' : 'border-blue-400'}`}>
          <div className="flex items-center gap-2">
            <span className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold text-white ${step2Done ? 'bg-green-500' : 'bg-blue-500'}`}>
              {step2Done ? '✓' : '2'}
            </span>
            <span className="font-semibold text-gray-800">Capture Photo</span>
          </div>

          {/* Camera / Preview */}
          <div className="relative w-full aspect-square bg-gray-100 rounded-xl overflow-hidden flex items-center justify-center">
            {!streaming && !captured && (
              <div className="text-center text-gray-400 space-y-2">
                <Camera size={40} className="mx-auto opacity-40" />
                <p className="text-sm">Click "Open Camera"</p>
              </div>
            )}
            <video ref={videoRef} className={`w-full h-full object-cover ${streaming ? 'block' : 'hidden'}`} />
            {captured && <img src={captured} alt="Captured" className="w-full h-full object-cover" />}
          </div>

          <canvas ref={canvasRef} className="hidden" />

          <div className="flex gap-2">
            {!streaming && !captured && (
              <button
                onClick={startCamera}
                className="flex-1 flex items-center justify-center gap-2 py-3 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-xl transition-colors"
              >
                <Camera size={16} /> Open Camera
              </button>
            )}
            {streaming && (
              <button
                onClick={capturePhoto}
                className="flex-1 flex items-center justify-center gap-2 py-3 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-xl transition-colors"
              >
                <Camera size={16} /> Capture
              </button>
            )}
            {captured && (
              <button
                onClick={() => { setCaptured(null); startCamera(); }}
                className="flex-1 py-3 border-2 border-gray-300 hover:bg-gray-50 text-gray-700 font-semibold rounded-xl transition-colors"
              >
                Retake
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FaceRegistration;
