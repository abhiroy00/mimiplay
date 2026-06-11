import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../../../config';
import { Camera, CheckCircle, AlertCircle, User } from 'lucide-react';

const FaceRegistration = () => {
  const [students, setStudents] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [captured, setCaptured] = useState(null);
  const [status, setStatus] = useState(null); // { type: 'success'|'error', msg }
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
      .then(data => {
        if (Array.isArray(data)) setStudents(data);
      })
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
    const dataUrl = canvas.toDataURL('image/jpeg');
    setCaptured(dataUrl);
    stopCamera();
  };

  const handleRegister = async () => {
    if (!selectedStudent) {
      setStatus({ type: 'error', msg: 'Please select a student first.' });
      return;
    }
    if (!captured) {
      setStatus({ type: 'error', msg: 'Please capture a photo first.' });
      return;
    }

    const student = students.find(s => s._id === selectedStudent);
    if (!student) return;

    setLoading(true);
    setStatus(null);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/register-face`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: student.name, image: captured }),
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setStatus({ type: 'success', msg: `Face registered for ${student.name}!` });
        setCaptured(null);
        setSelectedStudent('');
        // Mark face_registered in local list
        setStudents(prev =>
          prev.map(s => s._id === selectedStudent ? { ...s, face_registered: true } : s)
        );
      } else {
        setStatus({ type: 'error', msg: data.message || 'Registration failed.' });
      }
    } catch {
      setStatus({ type: 'error', msg: 'Server error. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const retake = () => {
    setCaptured(null);
    setStatus(null);
    startCamera();
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div>
        <h1 className="text-4xl font-bold text-text mb-2">Face Registration</h1>
        <p className="text-text/60">Register a student's face for attendance recognition</p>
      </div>

      {/* Student Selector */}
      <div className="bg-white rounded-2xl border-2 border-gray-200 p-6 space-y-3">
        <label className="block text-sm font-semibold text-gray-700">Select Student</label>
        <div className="relative">
          <User size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <select
            value={selectedStudent}
            onChange={e => setSelectedStudent(e.target.value)}
            className="w-full pl-10 pr-4 py-3 rounded-xl border-2 border-gray-200 focus:border-blue-400 outline-none text-gray-700 appearance-none"
          >
            <option value="">-- Choose a student --</option>
            {students.map(s => (
              <option key={s._id} value={s._id}>
                {s.name} {s.face_registered ? '(Face already registered)' : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Camera / Photo Area */}
      <div className="bg-white rounded-2xl border-2 border-gray-200 p-6 space-y-4">
        <label className="block text-sm font-semibold text-gray-700">Capture Photo</label>

        <div className="relative w-full aspect-video bg-gray-100 rounded-xl overflow-hidden flex items-center justify-center">
          {!streaming && !captured && (
            <div className="text-center text-gray-400 space-y-2">
              <Camera size={48} className="mx-auto opacity-40" />
              <p className="text-sm">Camera is off</p>
            </div>
          )}
          <video
            ref={videoRef}
            className={`w-full h-full object-cover ${streaming ? 'block' : 'hidden'}`}
          />
          {captured && (
            <img src={captured} alt="Captured" className="w-full h-full object-cover" />
          )}
        </div>

        <canvas ref={canvasRef} className="hidden" />

        <div className="flex gap-3">
          {!streaming && !captured && (
            <button
              onClick={startCamera}
              className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-xl transition-colors"
            >
              <Camera size={18} /> Open Camera
            </button>
          )}
          {streaming && (
            <button
              onClick={capturePhoto}
              className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-xl transition-colors"
            >
              <Camera size={18} /> Capture
            </button>
          )}
          {captured && (
            <button
              onClick={retake}
              className="flex-1 py-3 px-4 border-2 border-gray-300 hover:bg-gray-50 text-gray-700 font-semibold rounded-xl transition-colors"
            >
              Retake
            </button>
          )}
        </div>
      </div>

      {/* Status Message */}
      {status && (
        <div className={`flex items-center gap-3 p-4 rounded-xl font-medium ${
          status.type === 'success'
            ? 'bg-green-50 text-green-700 border border-green-200'
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {status.type === 'success'
            ? <CheckCircle size={20} />
            : <AlertCircle size={20} />}
          {status.msg}
        </div>
      )}

      {/* Register Button */}
      <button
        onClick={handleRegister}
        disabled={loading || !captured || !selectedStudent}
        className="w-full py-4 bg-gradient-to-r from-pink-500 to-orange-400 text-white font-bold text-lg rounded-2xl transition-opacity disabled:opacity-40"
      >
        {loading ? 'Registering...' : 'Register Face'}
      </button>
    </div>
  );
};

export default FaceRegistration;
