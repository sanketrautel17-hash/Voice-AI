import { useState, useEffect } from 'react';
import axios from 'axios';
import { Phone, Play, Check, X, Loader2, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Backend URL - Using localhost as requested.
const API_URL = 'http://localhost:8000';

function App() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [status, setStatus] = useState('idle'); // idle, calling, active, analyzing, concluded
  const [callSid, setCallSid] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [currentCallData, setCurrentCallData] = useState(null); // Store full call data including transcript
  const [error, setError] = useState(null);

  const startCall = async () => {
    if (!phoneNumber) return;
    setStatus('calling');
    setError(null);
    setAnalysis(null);
    setCurrentCallData(null);

    try {
      const response = await axios.post(`${API_URL}/dialout`, { to_number: phoneNumber });
      setCallSid(response.data.call_sid);
      setStatus('active');
    } catch (err) {
      console.error(err);
      setError('Failed to initiate call. Ensure backend is running.');
      setStatus('idle');
    }
  };

  // Poll for status
  useEffect(() => {
    let interval;
    if (status === 'active' || status === 'analyzing') {
      interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_URL}/calls`);
          const calls = response.data;
          // Find our call by SID or just take the latest one
          const currentCall = callSid
            ? calls.find(c => c.call_sid === callSid)
            : calls[0];

          if (currentCall) {
            setCurrentCallData(currentCall); // Update state with latest data
            console.log('Call Status:', currentCall.status, 'Analysis:', currentCall.analysis);

            // Check if call is completed and analysis is available
            if (currentCall.status === 'completed' || currentCall.analysis) {
              if (currentCall.analysis) {
                setAnalysis(currentCall.analysis);
                setStatus('concluded');
                clearInterval(interval);
              } else {
                setStatus('analyzing'); // Call done, waiting for AI analysis
              }
            }
          }
        } catch (err) {
          console.error('Polling error:', err);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [status, callSid]);

  return (
    <div className="app-container">
      <div className="bg-gradient" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card"
      >
        {/* Header */}
        <div className="header-section">
          <div className="icon-ring">
            <Phone size={32} />
          </div>
          <h1 className="title gradient-text">
            Voice AI Loan Bot
          </h1>
          <p className="sub-text">Automated Loan Qualification System</p>
        </div>

        {/* Status Indicator */}
        <div className="status-bar-container">
          <AnimatePresence mode='wait'>
            {status === 'idle' && (
              <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="status-badge status-ready">
                <span className="dot dot-gray" /> Ready to connect
              </motion.div>
            )}
            {status === 'calling' && (
              <motion.div key="calling" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="status-badge status-calling">
                <Loader2 className="spin-anim" size={16} /> Connecting...
              </motion.div>
            )}
            {status === 'active' && (
              <motion.div key="active" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="status-badge status-active">
                <span className="pulse-container">
                  <span className="pulse-ping"></span>
                  <span className="pulse-dot"></span>
                </span>
                Call in Progress
              </motion.div>
            )}
            {status === 'analyzing' && (
              <motion.div key="analyzing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="status-badge status-analyzing">
                <RefreshCw className="spin-anim" size={16} /> Analyzing Conversation...
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Input Form */}
        {status !== 'concluded' && (
          <motion.div layout className="form-group">
            <div className="input-wrapper">
              <input
                type="tel"
                placeholder="+1 (555) 000-0000"
                className="input-field"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                disabled={status !== 'idle'}
              />
              <Phone className="input-icon" size={18} />
            </div>

            <button
              onClick={startCall}
              disabled={!phoneNumber || status !== 'idle'}
              className={`btn-primary ${status !== 'idle' ? 'disabled' : ''}`}
            >
              {status === 'idle' ? (
                <> <Play size={20} fill="currentColor" /> Start Conversation </>
              ) : (
                'System Processing...'
              )}
            </button>
          </motion.div>
        )}

        {/* Conclusion / Result */}
        <AnimatePresence>
          {status === 'concluded' && analysis && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className={`result-card ${analysis.is_interested ? 'result-success' : 'result-failure'}`}
            >
              <div className="result-content">
                <div className={`result-icon-circle ${analysis.is_interested ? 'bg-success' : 'bg-failure'
                  }`}>
                  {analysis.is_interested ? <Check size={32} strokeWidth={3} /> : <X size={32} strokeWidth={3} />}
                </div>

                <div className="result-text-group">
                  <h2 className={`result-title ${analysis.is_interested ? 'text-success' : 'text-failure'
                    }`}>
                    {analysis.is_interested ? 'Loan Approved!' : 'Not Interested'}
                  </h2>
                  <p className="result-summary">{analysis.summary}</p>
                </div>

                {analysis.is_interested && (
                  <div className="result-grid">
                    <div className="result-item">
                      <p className="label">Loan Type</p>
                      <p className="value">{analysis.loan_type || 'General'}</p>
                    </div>
                    <div className="result-item">
                      <p className="label">Lead Score</p>
                      <p className="value">{analysis.lead_score}/10</p>
                    </div>
                  </div>
                )}

                {/* Transcript Section */}
                {currentCallData?.transcript && (
                  <div className="transcript-section">
                    <h3 className="transcript-header">Conversation Log</h3>
                    <div className="transcript-box">
                      {currentCallData.transcript
                        .filter(msg => msg.role === 'user' || msg.role === 'assistant')
                        .map((msg, idx) => (
                          <div key={idx} className={`message-row ${msg.role === 'user' ? 'msg-user' : 'msg-bot'}`}>
                            <div className="message-bubble">
                              <span className="msg-role-label">{msg.role === 'assistant' ? 'AI Assistant' : 'You'}</span>
                              <p className="msg-text">{typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)}</p>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                <button
                  onClick={() => {
                    setStatus('idle');
                    setAnalysis(null);
                    setCurrentCallData(null);
                  }}
                  className="restart-link"
                >
                  Start New Call
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {error && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="error-banner">
            {error}
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

export default App;
