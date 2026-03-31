import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Phone, Play, Check, X, Loader2, RefreshCw,
  MessageSquare, Clock, ChevronRight, History
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = 'http://localhost:8000';

// ─── Helpers ───────────────────────────────────────────────────────────────
function formatTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
  });
}

function formatDuration(start, end) {
  if (!start || !end) return null;
  const secs = Math.round((new Date(end) - new Date(start)) / 1000);
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// ─── Transcript Viewer ─────────────────────────────────────────────────────
function TranscriptView({ callData }) {
  const endRef = useRef(null);
  const messages = (callData?.transcript || []).filter(
    m => m.role === 'user' || m.role === 'assistant'
  );

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  if (!callData) {
    return (
      <div className="conv-empty-state">
        <div className="conv-empty-icon"><MessageSquare size={32} /></div>
        <p className="conv-empty-text">No call selected</p>
        <p className="conv-empty-hint">
          Start a new call or select a past call<br />from the history panel to view the transcript.
        </p>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="conv-empty-state">
        <div className="conv-empty-icon"><Clock size={32} /></div>
        <p className="conv-empty-text">
          {callData.status === 'started' ? 'Call in progress…' : 'No transcript available'}
        </p>
        <p className="conv-empty-hint">Transcript will appear here once the conversation starts.</p>
      </div>
    );
  }

  return (
    <div className="transcript-box">
      {messages.map((msg, idx) => (
        <div key={idx} className={`message-row ${msg.role === 'user' ? 'msg-user' : 'msg-bot'}`}>
          <div className="message-bubble">
            <span className="msg-role-label">
              {msg.role === 'assistant' ? 'AI Assistant' : 'Customer'}
            </span>
            <p className="msg-text">
              {typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)}
            </p>
          </div>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}

// ─── Past Call List Item ───────────────────────────────────────────────────
function CallListItem({ call, isActive, onClick }) {
  const analysis = call.analysis;
  const duration = formatDuration(call.start_time, call.end_time);
  const msgCount = (call.transcript || []).filter(
    m => m.role === 'user' || m.role === 'assistant'
  ).length;

  const isCompleted = call.status === 'completed';
  const interested = analysis?.is_interested;

  return (
    <button
      className={`call-list-item ${isActive ? 'call-list-item--active' : ''}`}
      onClick={onClick}
    >
      <div className={`call-item-dot ${isCompleted ? (interested ? 'dot-success' : 'dot-failure') : 'dot-pending'}`} />
      <div className="call-item-body">
        <div className="call-item-top">
          <span className="call-item-number">{call.call_sid?.slice(-8) ?? 'Unknown'}</span>
          <span className="call-item-time">{formatTime(call.start_time)}</span>
        </div>
        <div className="call-item-meta">
          {duration && <span className="call-meta-tag"><Clock size={10} /> {duration}</span>}
          {msgCount > 0 && <span className="call-meta-tag"><MessageSquare size={10} /> {msgCount} msgs</span>}
          {isCompleted && analysis && (
            <span className={`call-meta-tag ${interested ? 'tag-success' : 'tag-failure'}`}>
              {interested ? <Check size={10} /> : <X size={10} />}
              {interested ? 'Interested' : 'Not Interested'}
            </span>
          )}
          {!isCompleted && (
            <span className="call-meta-tag tag-pending">
              <Loader2 size={10} className="spin-anim" /> In Progress
            </span>
          )}
        </div>
      </div>
      <ChevronRight size={14} className="call-item-arrow" />
    </button>
  );
}

// ─── App ───────────────────────────────────────────────────────────────────
function App() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [status, setStatus] = useState('idle');
  const [callSid, setCallSid] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [currentCallData, setCurrentCallData] = useState(null);
  const [error, setError] = useState(null);

  // Past calls state
  const [allCalls, setAllCalls] = useState([]);
  const [selectedCallId, setSelectedCallId] = useState(null); // id from mongo
  const [activeView, setActiveView] = useState('live'); // 'live' | 'history'

  // The call data shown in the conversation panel
  const displayedCall = activeView === 'live'
    ? currentCallData
    : allCalls.find(c => c.id === selectedCallId) ?? null;

  // ── Lead Form State ──────────────────────────────────────────────────────
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    phone: '',
    email: ''
  });
  const [formStatus, setFormStatus] = useState('idle'); // idle, submitting, success, error

  const handleFormSubmit = async () => {
    if (!formData.firstName || !formData.lastName || !formData.phone || !formData.email) {
      setFormStatus('error');
      setTimeout(() => setFormStatus('idle'), 3000);
      return;
    }
    setFormStatus('submitting');
    try {
      await axios.post(`${API_URL}/submit-lead`, formData);
      setFormStatus('success');
      setFormData({ firstName: '', lastName: '', phone: '', email: '' });
      setTimeout(() => setFormStatus('idle'), 3000);
    } catch (err) {
      console.error('Failed to submit form', err);
      setFormStatus('error');
      setTimeout(() => setFormStatus('idle'), 3000);
    }
  };

  // ── Fetch all calls ────────────────────────────────────────────────────
  const fetchAllCalls = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/calls`);
      setAllCalls(res.data);
    } catch (e) {
      console.error('Failed to fetch call history:', e);
    }
  }, []);

  // Initial load
  useEffect(() => { fetchAllCalls(); }, [fetchAllCalls]);

  // ── Start a new call ───────────────────────────────────────────────────
  const startCall = async () => {
    if (!phoneNumber) return;
    setStatus('calling');
    setError(null);
    setAnalysis(null);
    setCurrentCallData(null);
    setActiveView('live');

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

  // ── Poll live call ─────────────────────────────────────────────────────
  useEffect(() => {
    let interval;
    if (status === 'active' || status === 'analyzing') {
      interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_URL}/calls`);
          const calls = response.data;
          setAllCalls(calls); // keep history in sync during live call

          const currentCall = callSid
            ? calls.find(c => c.call_sid === callSid)
            : calls[0];

          if (currentCall) {
            setCurrentCallData(currentCall);
            if (currentCall.status === 'completed' || currentCall.analysis) {
              if (currentCall.analysis) {
                setAnalysis(currentCall.analysis);
                setStatus('concluded');
                clearInterval(interval);
                fetchAllCalls(); // final refresh of history
              } else {
                setStatus('analyzing');
              }
            }
          }
        } catch (err) {
          console.error('Polling error:', err);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [status, callSid, fetchAllCalls]);

  const handleReset = () => {
    setStatus('idle');
    setAnalysis(null);
    setCurrentCallData(null);
    setCallSid(null);
    setError(null);
    setActiveView('history');
    fetchAllCalls();
  };

  const handleSelectCall = (call) => {
    setSelectedCallId(call.id);
    setActiveView('history');
  };

  // Determine the header title for the conversation panel
  const convTitle = activeView === 'live'
    ? 'Live Conversation'
    : selectedCallId
      ? `Call · ${allCalls.find(c => c.id === selectedCallId)?.call_sid?.slice(-8) ?? ''}`
      : 'Conversation Log';

  const convMsgCount = (displayedCall?.transcript || []).filter(
    m => m.role === 'user' || m.role === 'assistant'
  ).length;

  return (
    <div className="app-container">
      <div className="bg-gradient" />

      {/* ── Top Bar ── */}
      <div className="top-bar">
        <div className="top-bar-icon"><Phone size={20} /></div>
        <div>
          <p className="top-bar-title">Voice AI Loan Bot</p>
          <p className="top-bar-subtitle">Automated Loan Qualification System</p>
        </div>
        <div className="top-bar-status">
          <AnimatePresence mode="wait">
            {status === 'idle' && (
              <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="status-badge status-ready">
                <span className="dot dot-gray" /> Ready
              </motion.div>
            )}
            {status === 'calling' && (
              <motion.div key="calling" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="status-badge status-calling">
                <Loader2 className="spin-anim" size={14} /> Connecting...
              </motion.div>
            )}
            {status === 'active' && (
              <motion.div key="active" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="status-badge status-active">
                <span className="pulse-container"><span className="pulse-ping" /><span className="pulse-dot" /></span>
                Call in Progress
              </motion.div>
            )}
            {status === 'analyzing' && (
              <motion.div key="analyzing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="status-badge status-analyzing">
                <RefreshCw className="spin-anim" size={14} /> Analyzing...
              </motion.div>
            )}
            {status === 'concluded' && (
              <motion.div key="concluded" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className={`status-badge ${analysis?.is_interested ? 'status-active' : ''}`}
                style={!analysis?.is_interested ? { color: '#f87171' } : {}}>
                {analysis?.is_interested ? <Check size={14} /> : <X size={14} />}
                {analysis?.is_interested ? 'Qualified' : 'Not Interested'}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── Main ── */}
      <div className="main-content">

        {/* ── Left: Controls + Call History ── */}
        <div className="controls-panel">

          {/* Lead Details Form */}
          <div className="lead-form-section">
            <p className="panel-label">Lead Information</p>
            <div className="form-group">
              <input
                type="text"
                placeholder="First Name"
                className="input-field"
                style={{ paddingLeft: '1rem' }}
                value={formData.firstName}
                onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
              />
              <input
                type="text"
                placeholder="Last Name"
                className="input-field"
                style={{ paddingLeft: '1rem' }}
                value={formData.lastName}
                onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
              />
              <input
                type="tel"
                placeholder="Phone No."
                className="input-field"
                style={{ paddingLeft: '1rem' }}
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              />
              <input
                type="email"
                placeholder="Email ID"
                className="input-field"
                style={{ paddingLeft: '1rem' }}
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              />
              <button 
                className="btn-primary" 
                onClick={handleFormSubmit}
                disabled={formStatus === 'submitting'}
                style={formStatus === 'success' ? { background: 'var(--success)', boxShadow: 'none' } : {}}
              >
                {formStatus === 'submitting' ? <Loader2 size={16} className="spin-anim" /> : 
                 formStatus === 'success' ? <><Check size={16} /> Submitted</> : 
                 'Submit Lead'}
              </button>
              {formStatus === 'error' && (
                <p style={{ color: 'var(--error)', fontSize: '0.8rem', margin: 0, textAlign: 'center' }}>
                  Failed to submit. Please check fields.
                </p>
              )}
            </div>
          </div>

          <div className="section-divider" />

          {/* New Call Section */}
          <div>
            <p className="panel-label">New Call</p>
            <div className="form-group">
              <div className="input-wrapper">
                <input
                  type="tel"
                  placeholder="+1 (555) 000-0000"
                  className="input-field"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  disabled={status !== 'idle'}
                />
                <Phone className="input-icon" size={16} />
              </div>
              <button
                onClick={startCall}
                disabled={!phoneNumber || status !== 'idle'}
                className="btn-primary"
              >
                {status === 'idle'
                  ? <><Play size={18} fill="currentColor" /> Start Conversation</>
                  : 'System Processing...'}
              </button>
            </div>
          </div>

          {error && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="error-banner">
              {error}
            </motion.div>
          )}

          {/* Analysis result after call */}
          <AnimatePresence>
            {status === 'concluded' && analysis && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className={`result-card ${analysis.is_interested ? 'result-success' : 'result-failure'}`}
              >
                <div className="result-content">
                  <div className="result-header-row">
                    <div className={`result-icon-circle ${analysis.is_interested ? 'bg-success' : 'bg-failure'}`}>
                      {analysis.is_interested ? <Check size={22} strokeWidth={3} /> : <X size={22} strokeWidth={3} />}
                    </div>
                    <h2 className={`result-title ${analysis.is_interested ? 'text-success' : 'text-failure'}`}>
                      {analysis.is_interested ? 'Loan Approved!' : 'Not Interested'}
                    </h2>
                  </div>
                  <p className="result-summary">{analysis.summary}</p>
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
                  <button onClick={handleReset} className="restart-link">↩ Start New Call</button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Section divider */}
          <div className="section-divider" />

          {/* Past Calls History */}
          <div className="history-section">
            <div className="history-header">
              <p className="panel-label" style={{ margin: 0 }}>
                <History size={12} style={{ display: 'inline', marginRight: 5 }} />
                Call History
              </p>
              <button className="refresh-btn" onClick={fetchAllCalls} title="Refresh history">
                <RefreshCw size={13} />
              </button>
            </div>

            {allCalls.length === 0 ? (
              <div className="history-empty">
                <p>No past calls found.</p>
              </div>
            ) : (
              <div className="call-list">
                {/* Live call pinned to top if active */}
                {(status === 'active' || status === 'analyzing' || status === 'concluded') && currentCallData && (
                  <CallListItem
                    key="live"
                    call={{ ...currentCallData, id: currentCallData.id ?? 'live', call_sid: currentCallData.call_sid ?? callSid }}
                    isActive={activeView === 'live'}
                    onClick={() => setActiveView('live')}
                  />
                )}
                {allCalls
                  .filter(c => c.call_sid !== callSid || status === 'idle') // avoid duplicate of live call
                  .map(call => (
                    <CallListItem
                      key={call.id}
                      call={call}
                      isActive={activeView === 'history' && selectedCallId === call.id}
                      onClick={() => handleSelectCall(call)}
                    />
                  ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Right: Conversation Panel ── */}
        <div className="conversation-panel">
          <div className="conv-panel-header">
            <h3 className="conv-panel-title">
              <MessageSquare size={16} />
              {convTitle}
            </h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {/* View toggle tabs */}
              <div className="view-tabs">
                <button
                  className={`view-tab ${activeView === 'live' ? 'view-tab--active' : ''}`}
                  onClick={() => setActiveView('live')}
                  disabled={!currentCallData && status === 'idle'}
                >
                  Live
                </button>
                <button
                  className={`view-tab ${activeView === 'history' ? 'view-tab--active' : ''}`}
                  onClick={() => { setActiveView('history'); if (!selectedCallId && allCalls.length > 0) setSelectedCallId(allCalls[0].id); }}
                >
                  History
                </button>
              </div>
              {convMsgCount > 0 && (
                <span className="conv-msg-count">{convMsgCount} messages</span>
              )}
            </div>
          </div>

          {/* Analysis bar for history view */}
          {activeView === 'history' && displayedCall?.analysis && (
            <div className={`analysis-bar ${displayedCall.analysis.is_interested ? 'analysis-bar--success' : 'analysis-bar--failure'}`}>
              <div className="analysis-bar-left">
                <div className={`analysis-bar-icon ${displayedCall.analysis.is_interested ? 'bg-success' : 'bg-failure'}`}>
                  {displayedCall.analysis.is_interested ? <Check size={14} strokeWidth={3} /> : <X size={14} strokeWidth={3} />}
                </div>
                <div>
                  <span className="analysis-bar-label">
                    {displayedCall.analysis.is_interested ? 'Qualified Lead' : 'Not Interested'}
                    {displayedCall.analysis.lead_score != null && <> · Score: <strong>{displayedCall.analysis.lead_score}/10</strong></>}
                    {displayedCall.analysis.loan_type && <> · {displayedCall.analysis.loan_type}</>}
                  </span>
                  {displayedCall.analysis.summary && (
                    <p className="analysis-bar-summary">{displayedCall.analysis.summary}</p>
                  )}
                </div>
              </div>
              <span className="analysis-bar-time">{formatTime(displayedCall.start_time)}</span>
            </div>
          )}

          <TranscriptView callData={displayedCall} />
        </div>
      </div>
    </div>
  );
}

export default App;
