import React, { useState, useEffect, useRef } from 'react';
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css';
import 'prismjs/components/prism-python';
import { 
  Play, RotateCcw, FileText, Code2, AlertTriangle, CheckCircle, 
  Terminal, History, Cpu, FileCode, Layers, Info, Trash2, ArrowRight
} from 'lucide-react';

export default function App() {
  const [task, setTask] = useState('Implement a rate limiter using token bucket algorithm');
  const [threadId, setThreadId] = useState('');
  const [threads, setThreads] = useState([]);
  const [selectedThreadId, setSelectedThreadId] = useState('');
  const [status, setStatus] = useState('idle');
  const [logs, setLogs] = useState([]);
  const [files, setFiles] = useState({});
  const [testFiles, setTestFiles] = useState({});
  const [selectedFile, setSelectedFile] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  
  const terminalEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  // Generate random thread ID on mount
  useEffect(() => {
    generateRandomThreadId();
    loadThreads();
  }, []);

  // Highlight code blocks when selected file or content changes
  useEffect(() => {
    Prism.highlightAll();
  }, [selectedFile, files, testFiles]);

  // Autoscroll logs terminal
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const generateRandomThreadId = () => {
    const rand = 'thread_' + Math.random().toString(36).substring(2, 8);
    setThreadId(rand);
  };

  const loadThreads = async () => {
    try {
      const res = await fetch('/api/threads');
      const data = await res.json();
      setThreads(data);
    } catch (err) {
      console.error('Failed to load threads:', err);
    }
  };

  const loadThreadDetails = async (id) => {
    if (isStreaming) return;
    try {
      setSelectedThreadId(id);
      const res = await fetch(`/api/threads/${id}`);
      const data = await res.json();
      
      setTask(data.spec || '');
      setThreadId(data.thread_id || id);
      setStatus(data.status || 'idle');
      setFiles(data.files || {});
      setTestFiles(data.test_files || {});
      setLogs(data.run_log || []);
      
      // Select first file if available
      const allFiles = [...Object.keys(data.files || {}), ...Object.keys(data.test_files || {})];
      if (allFiles.length > 0) {
        setSelectedFile(allFiles[0]);
      } else {
        setSelectedFile('');
      }
      setErrorMsg('');
    } catch (err) {
      console.error('Failed to load thread details:', err);
      setErrorMsg('Failed to load historical thread data.');
    }
  };

  const startGeneration = (resumeMode = false) => {
    if (isStreaming) return;
    
    setIsStreaming(true);
    setErrorMsg('');
    setFiles({});
    setTestFiles({});
    setSelectedFile('');
    
    if (!resumeMode) {
      setLogs([]);
      setStatus('planning');
    }

    const url = resumeMode 
      ? `/api/resume?thread_id=${encodeURIComponent(threadId)}`
      : `/api/generate?spec=${encodeURIComponent(task)}&thread_id=${encodeURIComponent(threadId)}`;
      
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.addEventListener('update', (event) => {
      const data = JSON.parse(event.data);
      if (data.status) setStatus(data.status);
      if (data.files) setFiles(data.files);
      if (data.test_files) setTestFiles(data.test_files);
      
      // Auto-select first file if none is selected
      const currentFileList = [...Object.keys(data.files || {}), ...Object.keys(data.test_files || {})];
      setSelectedFile(prev => {
        if (!prev && currentFileList.length > 0) return currentFileList[0];
        return prev;
      });

      if (data.run_log && Object.keys(data.run_log).length > 0) {
        setLogs(prev => {
          // Avoid appending duplicate log entries
          const isDup = prev.some(l => l.timestamp === data.run_log.timestamp && l.action === data.run_log.action);
          if (isDup) return prev;
          return [...prev, data.run_log];
        });
      }
    });

    eventSource.addEventListener('done', (event) => {
      setIsStreaming(false);
      eventSource.close();
      loadThreads();
      setStatus('done');
    });

    eventSource.addEventListener('error', (event) => {
      setIsStreaming(false);
      eventSource.close();
      loadThreads();
      let msg = 'An error occurred during run orchestration.';
      try {
        if (event.data) {
          const parsed = JSON.parse(event.data);
          msg = parsed.error || msg;
        }
      } catch(e){}
      setErrorMsg(msg);
      setStatus('failed');
    });
  };

  const handleStopStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      setIsStreaming(false);
      loadThreads();
      setStatus('failed');
      setErrorMsg('Run execution aborted by user.');
    }
  };

  const startNewRun = () => {
    if (isStreaming) return;
    setSelectedThreadId('');
    generateRandomThreadId();
    setTask('');
    setStatus('idle');
    setLogs([]);
    setFiles({});
    setTestFiles({});
    setSelectedFile('');
    setErrorMsg('');
  };

  // Helper to check if file is a test file
  const isTest = (filename) => filename.startsWith('test_');

  // Stepper Node Definitions
  const steps = [
    { key: 'planning', label: 'Planning', desc: 'Planner Agent' },
    { key: 'coding', label: 'Coding', desc: 'Coder Agent' },
    { key: 'testing', label: 'Testing', desc: 'Test Executor' },
    { key: 'linting', label: 'Linting', desc: 'Static Analyzer' },
    { key: 'reviewing', label: 'Reviewing', desc: 'Code Reviewer' },
    { key: 'documenting', label: 'Documenting', desc: 'Docs Agent' },
    { key: 'done', label: 'Done', desc: 'Completed' }
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      
      {/* 1. Left Sidebar: Threads Manager */}
      <div className="w-80 border-r border-slate-800 bg-slate-900 flex flex-col">
        <div className="p-6 border-b border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-purple-900/30">
            <Cpu className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg leading-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Antigravity</h1>
            <p className="text-xs text-slate-500 font-medium tracking-wide uppercase">Multi-Agent Assistant</p>
          </div>
        </div>

        <div className="p-4 border-b border-slate-800">
          <button 
            onClick={startNewRun}
            disabled={isStreaming}
            className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-lg bg-gradient-to-r from-purple-600 to-cyan-500 hover:from-purple-500 hover:to-cyan-400 text-white font-semibold text-sm shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Create New Run
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            <History className="w-4 h-4" />
            <span>Execution History</span>
          </div>

          {threads.length === 0 ? (
            <p className="text-sm text-slate-600 text-center py-8">No historical threads found.</p>
          ) : (
            threads.map((t) => (
              <div 
                key={t.thread_id}
                onClick={() => loadThreadDetails(t.thread_id)}
                className={`p-3 rounded-lg border text-left cursor-pointer transition ${
                  selectedThreadId === t.thread_id 
                    ? 'bg-slate-800/80 border-purple-500/50 shadow-md shadow-purple-950/20' 
                    : 'bg-slate-950/40 border-slate-800/60 hover:bg-slate-800/30'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-mono text-cyan-400 font-semibold">{t.thread_id}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                    t.status === 'done' ? 'bg-emerald-500/10 text-emerald-400' :
                    t.status === 'failed' ? 'bg-rose-500/10 text-rose-400' :
                    'bg-amber-500/10 text-amber-400 animate-pulse'
                  }`}>
                    {t.status}
                  </span>
                </div>
                <h4 className="text-sm font-medium text-slate-300 line-clamp-1 mb-2">{t.task}</h4>
                <div className="flex items-center justify-between text-[11px] text-slate-500">
                  <div className="flex items-center gap-1">
                    <FileText className="w-3.5 h-3.5" />
                    <span>{t.file_count} files</span>
                  </div>
                  <span>
                    {t.last_updated ? new Date(t.last_updated).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'unknown'}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 2. Main Work Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        
        {/* Top bar control & settings */}
        <div className="p-6 border-b border-slate-800 bg-slate-900/50 flex flex-col gap-4">
          <div className="flex items-start gap-4">
            <div className="flex-1">
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5 block">Coding Task Spec</label>
              <textarea 
                value={task}
                onChange={(e) => setTask(e.target.value)}
                disabled={isStreaming}
                placeholder="Describe what you want the assistant to build..."
                rows={2}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-purple-500/70 transition resize-none disabled:opacity-50"
              />
            </div>
            
            <div className="w-64">
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5 block">Thread ID (Checkpointer)</label>
              <input 
                type="text" 
                value={threadId}
                onChange={(e) => setThreadId(e.target.value)}
                disabled={isStreaming}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 font-mono focus:outline-none focus:border-purple-500/70 transition disabled:opacity-50 mb-2"
              />
              <div className="flex gap-2">
                {isStreaming ? (
                  <button 
                    onClick={handleStopStream}
                    className="flex-1 py-1.5 px-3 rounded bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs transition"
                  >
                    Abort Run
                  </button>
                ) : (
                  <>
                    <button 
                      onClick={() => startGeneration(false)}
                      disabled={!task.trim()}
                      className="flex-grow flex items-center justify-center gap-1 py-1.5 px-3 rounded bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs disabled:opacity-40 transition"
                    >
                      <Play className="w-3.5 h-3.5" />
                      <span>Start</span>
                    </button>
                    <button 
                      onClick={() => startGeneration(true)}
                      className="flex-grow flex items-center justify-center gap-1 py-1.5 px-3 rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 font-bold text-xs transition"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Resume</span>
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {errorMsg && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center gap-2 text-rose-400 text-xs font-semibold animate-pulse">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Stepper Status tracker */}
          <div className="bg-slate-950/60 p-4 border border-slate-800/80 rounded-xl">
            <div className="grid grid-cols-7 gap-2">
              {steps.map((step, idx) => {
                const isCurrent = status === step.key;
                const isPast = steps.findIndex(s => s.key === status) > idx || status === 'done';
                const isFailed = status === 'failed';
                
                return (
                  <div 
                    key={step.key}
                    className={`flex flex-col items-center p-2 rounded-lg border text-center transition ${
                      isCurrent 
                        ? (isFailed ? 'border-rose-500 bg-rose-950/10 shadow-lg shadow-rose-950/20' : 'border-cyan-500 bg-cyan-950/10 shadow-lg shadow-cyan-950/20 animate-pulse') 
                        : isPast 
                          ? 'border-emerald-500/30 bg-emerald-950/5' 
                          : 'border-slate-800 bg-transparent opacity-40'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 mb-1">
                      {isPast ? (
                        <CheckCircle className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <div className={`w-2 h-2 rounded-full ${isCurrent ? (isFailed ? 'bg-rose-500' : 'bg-cyan-400') : 'bg-slate-700'}`} />
                      )}
                      <span className="text-xs font-bold tracking-wide uppercase text-slate-300">{step.label}</span>
                    </div>
                    <span className="text-[10px] text-slate-500 font-medium">{step.desc}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* 3. Split Workspace view (File Explorer + Code Viewer) */}
        <div className="flex-1 flex min-h-0">
          
          {/* File list tree */}
          <div className="w-64 border-r border-slate-800 bg-slate-900/20 flex flex-col p-4">
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-slate-500" />
              <span>Workspace Files</span>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-1">
              {Object.keys(files).length === 0 && Object.keys(testFiles).length === 0 ? (
                <p className="text-xs text-slate-600 py-4 italic">No files coded yet.</p>
              ) : (
                <>
                  {Object.keys(files).map(f => (
                    <div 
                      key={f}
                      onClick={() => setSelectedFile(f)}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-md cursor-pointer text-sm font-medium transition ${
                        selectedFile === f 
                          ? 'bg-purple-600/10 border-l-2 border-purple-500 text-purple-300' 
                          : 'hover:bg-slate-800/40 text-slate-400'
                      }`}
                    >
                      <Code2 className="w-4 h-4 shrink-0 text-slate-500" />
                      <span className="truncate">{f}</span>
                    </div>
                  ))}
                  {Object.keys(testFiles).map(f => (
                    <div 
                      key={f}
                      onClick={() => setSelectedFile(f)}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-md cursor-pointer text-sm font-medium transition ${
                        selectedFile === f 
                          ? 'bg-cyan-600/10 border-l-2 border-cyan-500 text-cyan-300' 
                          : 'hover:bg-slate-800/40 text-slate-400'
                      }`}
                    >
                      <FileCode className="w-4 h-4 shrink-0 text-slate-500" />
                      <span className="truncate font-mono">{f}</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>

          {/* Syntax Highlighted Code Viewer */}
          <div className="flex-grow bg-slate-950 flex flex-col min-w-0">
            <div className="px-6 py-3 border-b border-slate-800 bg-slate-900/10 flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-slate-400 bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
                {selectedFile || 'select_a_file.py'}
              </span>
              <span className="text-[10px] text-slate-600 font-bold uppercase tracking-wider">python source</span>
            </div>
            
            <div className="flex-grow overflow-auto p-6 font-mono text-sm leading-relaxed min-h-0">
              {selectedFile ? (
                <pre className="m-0 h-full">
                  <code className="language-python">
                    {files[selectedFile] || testFiles[selectedFile] || ''}
                  </code>
                </pre>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-700 text-center gap-2">
                  <Code2 className="w-12 h-12 text-slate-800 animate-pulse" />
                  <p className="text-sm font-medium">Select a file from the workspace list to view its code.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 4. Bottom Terminal Log Feed */}
        <div className="h-64 border-t border-slate-800 bg-slate-950 flex flex-col">
          <div className="px-6 py-2 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between select-none">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Agent Stream Logs</span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 font-mono text-slate-500">AutoScroll Active</span>
          </div>
          
          <div className="flex-1 overflow-y-auto p-6 font-mono text-xs space-y-3 bg-slate-950/80">
            {logs.length === 0 ? (
              <p className="text-slate-700 italic select-none">No stream logs. Start a new run to begin logs capture.</p>
            ) : (
              logs.map((log, idx) => {
                const agentColors = {
                  supervisor: 'text-amber-400 font-semibold',
                  planner: 'text-purple-400',
                  coder: 'text-blue-400',
                  test_writer: 'text-indigo-400',
                  executor: 'text-emerald-400',
                  static_analyzer: 'text-teal-400',
                  reviewer: 'text-pink-400',
                  debugger: 'text-rose-400',
                  docs_agent: 'text-cyan-400'
                };
                
                return (
                  <div key={idx} className="p-3 bg-slate-900/35 border border-slate-800/40 rounded-lg hover:border-slate-700/60 transition">
                    <div className="flex items-center gap-2 mb-1 text-slate-500 font-semibold">
                      <span>[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                      <span className={agentColors[log.agent] || 'text-slate-400'}>
                        {log.agent ? log.agent.toUpperCase() : 'AGENT'}
                      </span>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-700 shrink-0" />
                      <span className="text-slate-300">{log.action}</span>
                    </div>
                    {log.reasoning && (
                      <p className="text-slate-400 pl-4 mt-0.5 leading-relaxed">
                        <strong className="text-slate-500">Reasoning:</strong> {log.reasoning}
                      </p>
                    )}
                    {log.details && (
                      <p className="text-slate-500 pl-4 mt-0.5 italic leading-relaxed">
                        <strong className="text-slate-600">Details:</strong> {log.details}
                      </p>
                    )}
                  </div>
                );
              })
            )}
            <div ref={terminalEndRef} />
          </div>
        </div>

      </div>
    </div>
  );
}
