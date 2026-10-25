import React, { useRef, useState, useEffect, useCallback } from 'react';
import * as faceapi from 'face-api.js';
import {
  X,
  Camera,
  CheckCircle2,
  AlertCircle,
  Loader,
  ScanFace,
  Shield,
} from 'lucide-react';

/**
 * FaceCheckInModal – Uses the browser webcam + face-api.js TinyFaceDetector
 * to perform real face detection-based attendance check-in.
 *
 * Props:
 *  - open: boolean – whether the modal is visible
 *  - onClose: () => void – close handler
 *  - onConfirm: () => Promise<void> – called when face is detected to actually perform check-in
 */
export const FaceCheckInModal = ({ open, onClose, onConfirm }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const animationFrameRef = useRef(null);

  const [phase, setPhase] = useState('loading'); // loading | scanning | detected | confirmed | error
  const [modelsLoaded, setModelsLoaded] = useState(false);
  const [statusMsg, setStatusMsg] = useState('Loading face detection models…');
  const [faceCount, setFaceCount] = useState(0);
  const [confidence, setConfidence] = useState(0);
  const [detectionProgress, setDetectionProgress] = useState(0);
  const consecutiveDetections = useRef(0);
  const REQUIRED_DETECTIONS = 15; // ~1.5 seconds at ~10fps

  // Load face-api models
  useEffect(() => {
    if (!open) return;
    let cancelled = false;

    const loadModels = async () => {
      try {
        setPhase('loading');
        setStatusMsg('Loading face detection models…');

        await faceapi.nets.tinyFaceDetector.loadFromUri('/models');

        if (!cancelled) {
          setModelsLoaded(true);
          setStatusMsg('Models loaded. Starting camera…');
        }
      } catch (err) {
        console.error('Failed to load face-api models:', err);
        if (!cancelled) {
          setPhase('error');
          setStatusMsg('Failed to load face detection models. Please try again.');
        }
      }
    };

    loadModels();
    return () => { cancelled = true; };
  }, [open]);

  // Start webcam when models are loaded
  useEffect(() => {
    if (!open || !modelsLoaded) return;

    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: 'user',
          },
        });

        streamRef.current = stream;

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
          setPhase('scanning');
          setStatusMsg('Position your face in the center of the frame…');
          consecutiveDetections.current = 0;
          setDetectionProgress(0);
        }
      } catch (err) {
        console.error('Camera access error:', err);
        setPhase('error');
        setStatusMsg(
          err.name === 'NotAllowedError'
            ? 'Camera access denied. Please allow camera permissions and try again.'
            : 'Could not access camera. Make sure your device has a webcam.'
        );
      }
    };

    startCamera();

    return () => {
      stopCamera();
    };
  }, [open, modelsLoaded]);

  const stopCamera = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  // Run face detection loop
  useEffect(() => {
    if (phase !== 'scanning' || !videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;

    const detect = async () => {
      if (phase !== 'scanning' || !video || video.paused || video.ended) return;

      try {
        const detections = await faceapi.detectAllFaces(
          video,
          new faceapi.TinyFaceDetectorOptions({
            inputSize: 320,
            scoreThreshold: 0.5,
          })
        );

        // Draw detections on canvas
        const dims = faceapi.matchDimensions(canvas, video, true);
        const resized = faceapi.resizeResults(detections, dims);

        canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);

        // Draw custom bounding boxes
        const ctx = canvas.getContext('2d');
        resized.forEach((det) => {
          const { x, y, width, height } = det.box;
          const score = det.score;

          // Glow effect
          ctx.shadowColor = score > 0.7 ? '#00ff88' : '#ffaa00';
          ctx.shadowBlur = 15;
          ctx.strokeStyle = score > 0.7 ? '#00ff88' : '#ffaa00';
          ctx.lineWidth = 3;
          ctx.setLineDash([8, 4]);

          // Rounded rect
          const r = 12;
          ctx.beginPath();
          ctx.moveTo(x + r, y);
          ctx.lineTo(x + width - r, y);
          ctx.quadraticCurveTo(x + width, y, x + width, y + r);
          ctx.lineTo(x + width, y + height - r);
          ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
          ctx.lineTo(x + r, y + height);
          ctx.quadraticCurveTo(x, y + height, x, y + height - r);
          ctx.lineTo(x, y + r);
          ctx.quadraticCurveTo(x, y, x + r, y);
          ctx.stroke();

          // Corner markers
          ctx.shadowBlur = 0;
          ctx.setLineDash([]);
          ctx.lineWidth = 4;
          const cornerLen = 20;

          // Top-left
          ctx.beginPath();
          ctx.moveTo(x, y + cornerLen);
          ctx.lineTo(x, y);
          ctx.lineTo(x + cornerLen, y);
          ctx.stroke();

          // Top-right
          ctx.beginPath();
          ctx.moveTo(x + width - cornerLen, y);
          ctx.lineTo(x + width, y);
          ctx.lineTo(x + width, y + cornerLen);
          ctx.stroke();

          // Bottom-left
          ctx.beginPath();
          ctx.moveTo(x, y + height - cornerLen);
          ctx.lineTo(x, y + height);
          ctx.lineTo(x + cornerLen, y + height);
          ctx.stroke();

          // Bottom-right
          ctx.beginPath();
          ctx.moveTo(x + width - cornerLen, y + height);
          ctx.lineTo(x + width, y + height);
          ctx.lineTo(x + width, y + height - cornerLen);
          ctx.stroke();

          // Confidence label
          ctx.font = '13px "Inter", sans-serif';
          ctx.fillStyle = score > 0.7 ? '#00ff88' : '#ffaa00';
          ctx.fillText(`${(score * 100).toFixed(0)}% match`, x + 4, y - 8);
        });

        setFaceCount(detections.length);

        if (detections.length === 1 && detections[0].score > 0.6) {
          consecutiveDetections.current += 1;
          setConfidence(Math.round(detections[0].score * 100));
          const progress = Math.min(100, Math.round((consecutiveDetections.current / REQUIRED_DETECTIONS) * 100));
          setDetectionProgress(progress);
          setStatusMsg(`Face detected! Hold steady… ${progress}%`);

          if (consecutiveDetections.current >= REQUIRED_DETECTIONS) {
            setPhase('detected');
            setStatusMsg('Face verified! Confirming check-in…');
            return; // Stop detection loop
          }
        } else {
          consecutiveDetections.current = Math.max(0, consecutiveDetections.current - 2);
          const progress = Math.min(100, Math.round((consecutiveDetections.current / REQUIRED_DETECTIONS) * 100));
          setDetectionProgress(progress);
          if (detections.length === 0) {
            setStatusMsg('No face detected. Please look at the camera.');
          } else if (detections.length > 1) {
            setStatusMsg('Multiple faces detected. Only one person should be in the frame.');
          }
        }
      } catch (err) {
        console.error('Detection error:', err);
      }

      animationFrameRef.current = requestAnimationFrame(() => {
        setTimeout(detect, 100); // ~10fps
      });
    };

    detect();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [phase]);

  // Auto-confirm when face detected
  useEffect(() => {
    if (phase !== 'detected') return;

    const confirmCheckIn = async () => {
      try {
        let geoData = {
          check_in_method: 'FACE_DETECTION',
          faces_detected: 1,
        };

        if (navigator.geolocation) {
          try {
            const pos = await new Promise((resolve, reject) => {
              navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 4000,
                maximumAge: 0,
              });
            });
            if (pos && pos.coords) {
              geoData.latitude = pos.coords.latitude;
              geoData.longitude = pos.coords.longitude;
              geoData.accuracy = pos.coords.accuracy;
            }
          } catch (geoErr) {
            console.warn('Geolocation not obtained, proceeding with face verification:', geoErr);
          }
        }

        await onConfirm(geoData);
        setPhase('confirmed');
        setStatusMsg('✅ Check-in successful via face detection!');
        // Auto close after 2 seconds
        setTimeout(() => {
          stopCamera();
          onClose();
        }, 2500);
      } catch (err) {
        setPhase('error');
        setStatusMsg(typeof err === 'string' ? err : err?.message || 'Check-in failed. Please try again.');
      }
    };

    confirmCheckIn();
  }, [phase]);

  // Cleanup on close
  useEffect(() => {
    if (!open) {
      stopCamera();
      setModelsLoaded(false);
      setPhase('loading');
      setStatusMsg('');
      setFaceCount(0);
      setConfidence(0);
      setDetectionProgress(0);
      consecutiveDetections.current = 0;
    }
  }, [open, stopCamera]);

  if (!open) return null;

  const phaseColors = {
    loading: 'var(--accent-blue)',
    scanning: 'var(--accent-purple)',
    detected: 'var(--status-success)',
    confirmed: 'var(--status-success)',
    error: 'var(--status-danger)',
  };

  const phaseIcons = {
    loading: <Loader size={22} className="spin-icon" />,
    scanning: <ScanFace size={22} />,
    detected: <Shield size={22} />,
    confirmed: <CheckCircle2 size={22} />,
    error: <AlertCircle size={22} />,
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 1100 }}>
      <div
        className="modal-dialog"
        style={{
          maxWidth: '680px',
          width: '95%',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          className="modal-header"
          style={{
            background: `linear-gradient(135deg, ${phaseColors[phase]}22, transparent)`,
            borderBottom: `2px solid ${phaseColors[phase]}44`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '12px',
                background: `${phaseColors[phase]}22`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: phaseColors[phase],
              }}
            >
              {phaseIcons[phase]}
            </div>
            <div>
              <h3 style={{ margin: 0 }}>Face Detection Check-In</h3>
              <span
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                }}
              >
                AI-powered biometric verification
              </span>
            </div>
          </div>
          <button className="btn-icon" onClick={() => { stopCamera(); onClose(); }}>
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body" style={{ padding: 0 }}>
          {/* Video container */}
          <div
            style={{
              position: 'relative',
              width: '100%',
              aspectRatio: '4 / 3',
              background: '#0a0a0a',
              overflow: 'hidden',
            }}
          >
            <video
              ref={videoRef}
              muted
              playsInline
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                transform: 'scaleX(-1)', // Mirror
              }}
            />
            <canvas
              ref={canvasRef}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                transform: 'scaleX(-1)', // Mirror to match video
                pointerEvents: 'none',
              }}
            />

            {/* Scanning overlay corners */}
            {phase === 'scanning' && (
              <div
                style={{
                  position: 'absolute',
                  inset: '15%',
                  border: '2px dashed rgba(139, 92, 246, 0.4)',
                  borderRadius: '50%',
                  pointerEvents: 'none',
                  animation: 'pulse 2s ease-in-out infinite',
                }}
              />
            )}

            {/* Phase overlay for confirmed */}
            {phase === 'confirmed' && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: 'rgba(0, 255, 136, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  pointerEvents: 'none',
                }}
              >
                <CheckCircle2 size={80} color="#00ff88" style={{ opacity: 0.8 }} />
              </div>
            )}

            {/* Phase overlay for loading */}
            {phase === 'loading' && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: 'rgba(0, 0, 0, 0.7)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '1rem',
                  color: '#fff',
                }}
              >
                <div className="spinner" />
                <span style={{ fontSize: '0.9rem' }}>Initializing face detection…</span>
              </div>
            )}

            {/* Phase overlay for error */}
            {phase === 'error' && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: 'rgba(0, 0, 0, 0.7)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '1rem',
                  color: '#fff',
                  padding: '2rem',
                  textAlign: 'center',
                }}
              >
                <AlertCircle size={48} color="var(--status-danger)" />
                <span>{statusMsg}</span>
              </div>
            )}
          </div>

          {/* Status bar */}
          <div
            style={{
              padding: '1rem 1.5rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            {/* Status message */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                color: phaseColors[phase],
                fontWeight: 600,
                fontSize: '0.9rem',
              }}
            >
              {phaseIcons[phase]}
              <span>{statusMsg}</span>
            </div>

            {/* Progress bar */}
            {(phase === 'scanning' || phase === 'detected') && (
              <div
                style={{
                  width: '100%',
                  height: '6px',
                  borderRadius: '3px',
                  background: 'rgba(255,255,255,0.08)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${detectionProgress}%`,
                    height: '100%',
                    borderRadius: '3px',
                    background:
                      detectionProgress < 50
                        ? 'var(--accent-purple)'
                        : detectionProgress < 100
                        ? 'var(--accent-blue)'
                        : 'var(--status-success)',
                    transition: 'width 0.3s ease, background 0.3s ease',
                  }}
                />
              </div>
            )}

            {/* Metrics row */}
            {phase === 'scanning' && (
              <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <span>
                  Faces: <strong style={{ color: faceCount === 1 ? '#00ff88' : faceCount > 1 ? '#ff6b6b' : '#ffaa00' }}>{faceCount}</strong>
                </span>
                {confidence > 0 && (
                  <span>
                    Confidence: <strong style={{ color: confidence > 70 ? '#00ff88' : '#ffaa00' }}>{confidence}%</strong>
                  </span>
                )}
                <span>
                  Progress: <strong>{detectionProgress}%</strong>
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => { stopCamera(); onClose(); }}
          >
            Cancel
          </button>
          {phase === 'error' && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                setPhase('loading');
                setStatusMsg('Retrying…');
                setModelsLoaded(false);
                // Trigger model load again
                setTimeout(() => {
                  const reload = async () => {
                    try {
                      await faceapi.nets.tinyFaceDetector.loadFromUri('/models');
                      setModelsLoaded(true);
                    } catch {
                      setPhase('error');
                      setStatusMsg('Failed to load models.');
                    }
                  };
                  reload();
                }, 500);
              }}
            >
              <Camera size={16} /> Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
