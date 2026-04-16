import React, { useState, useEffect, useRef } from 'react';
import { 
  Star, 
  Triangle, 
  Circle, 
  Square, 
  Diamond, 
  Pentagon, 
  Hexagon, 
  Octagon,
  Zap,
  Box,
  Check,
  X,
  Timer,
  History,
  Activity,
  Brain,
  Target
} from 'lucide-react';
import data from './data.json';

// Fisher-Yates shuffle algorithm
const shuffleArray = (array) => {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
};

const STAGES = {
  START: 'START',
  STUDY: 'STUDY',
  SHIFT: 'SHIFT',
  DECISION: 'DECISION',
  RESULTS: 'RESULTS',
};

function parseItem(itemStr) {
  const [attributes, label] = itemStr.split(' -> ');
  // Split by | and also handle comma-separated values like r1=+1, r2=+1
  const parts = attributes.split(/[|,]/).map(p => p.trim());
  const obj = { label };
  parts.forEach(p => {
    const [key, val] = p.split('=');
    if (key && val) obj[key.trim()] = val.trim();
  });
  return obj;
}

const Card = ({ data, showLabel = true }) => {
  const getToneColor = (tone) => {
    const tones = {
      warm: 'bg-orange-300/95 border-orange-400',
      cool: 'bg-blue-300/95 border-blue-400',
      bright: 'bg-yellow-200/95 border-yellow-300',
      muted: 'bg-gray-300/95 border-gray-400',
      neutral: 'bg-slate-200/95 border-slate-300',
      dim: 'bg-indigo-300/95 border-indigo-400',
    };
    return tones[tone] || 'bg-white/95 border-gray-300';
  };

  const getShapeIcon = (shape) => {
    const props = { size: 64, strokeWidth: 2, className: "text-zinc-800 drop-shadow-sm" };
    const icons = {
      star: <Star {...props} />,
      triangle: <Triangle {...props} />,
      circle: <Circle {...props} />,
      square: <Square {...props} />,
      diamond: <Diamond {...props} />,
      pentagon: <Pentagon {...props} />,
      kite: <Diamond {...props} className="text-zinc-800 drop-shadow-sm rotate-12 scale-y-125" />,
      oval: <Circle {...props} className="text-zinc-800 drop-shadow-sm scale-x-150" />,
      hexagon: <Hexagon {...props} />,
      octagon: <Octagon {...props} />,
    };
    return icons[shape] || <Box {...props} />;
  };

  return (
    <div className="flex flex-col items-center group">
      <div className={`w-52 border-2 rounded-2xl overflow-hidden shadow-lg ${getToneColor(data.tone)}`}>
        {/* Header: Coordinates */}
        <div className="flex justify-between px-4 py-3 bg-black/20 border-b border-black/10">
          <div className="flex flex-col items-center">
            <span className="text-[10px] uppercase text-black/60 font-black leading-tight">R1 VALUE</span>
            <span className="text-lg font-mono font-black text-black leading-none">{data.r1}</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-[10px] uppercase text-black/60 font-black leading-tight">R2 VALUE</span>
            <span className="text-lg font-mono font-black text-black leading-none">{data.r2}</span>
          </div>
        </div>

        {/* Visual Content */}
        <div className="py-8 flex flex-col items-center justify-center bg-white/10">
          <div className="mb-3">
            {getShapeIcon(data.shape)}
          </div>
          <div className="px-4 py-1 bg-black/80 rounded-full text-[11px] font-black uppercase tracking-widest text-white shadow-inner">
            {data.shape}
          </div>
        </div>

        {/* Footer: Properties */}
        <div className="px-4 py-3 bg-black/10 border-t border-black/10">
          <div className="flex flex-col">
            <span className="text-[10px] uppercase text-black/60 font-black leading-tight">TONE PROPERTY</span>
            <span className="text-sm font-black text-black capitalize">{data.tone}</span>
          </div>
        </div>
      </div>

      {/* Label outside the card container */}
      {showLabel && data.label && (
        <div className={`mt-4 px-6 py-2 rounded-xl text-sm font-black uppercase tracking-tighter shadow-2xl border-2 ${
          ['accept', 'anchor', 'valid', 'north', 'amber', 'ember'].includes(data.label) 
          ? 'bg-green-500 text-white border-green-400' 
          : 'bg-red-500 text-white border-red-400'
        }`}>
          {data.label}
        </div>
      )}
    </div>
  );
};

export default function App() {
  const [stage, setStage] = useState(STAGES.START);
  const [activeEpisodes, setActiveEpisodes] = useState([]);
  const [episodeIndex, setEpisodeIndex] = useState(0);
  const [turnIndex, setTurnIndex] = useState(0);
  const [probeIndex, setProbeIndex] = useState(0);
  const [results, setResults] = useState([]);
  const [history, setHistory] = useState([]);
  const [startTime, setStartTime] = useState(null);

  useEffect(() => {
    const savedHistory = localStorage.getItem('cogflex_history');
    if (savedHistory) {
      try {
        setHistory(JSON.parse(savedHistory));
      } catch (e) {
        console.error("Failed to load history", e);
      }
    }
  }, []);

  const currentEpisode = activeEpisodes[episodeIndex];
  const turns = currentEpisode?.inference?.turns || [];
  
  const lastTurnText = turns.length > 0 ? turns[turns.length - 1] : '';
  const labelMatch = lastTurnText.match(/Use only labels from: (.*)\./);
  const possibleLabels = labelMatch ? labelMatch[1].split(', ') : ['accept', 'reject'];

  const resetGame = () => {
    setStage(STAGES.START);
    setEpisodeIndex(0);
    setTurnIndex(0);
    setProbeIndex(0);
    setResults([]);
  };

  const handleStart = () => {
    setActiveEpisodes(shuffleArray(data));
    setStage(STAGES.STUDY);
    setEpisodeIndex(0);
    setTurnIndex(0);
    setProbeIndex(0);
    setResults([]);
  };

  const handleNextTurn = () => {
    if (turnIndex < turns.length - 2) {
      setTurnIndex(turnIndex + 1);
    } else {
      setStage(STAGES.SHIFT);
      setTurnIndex(turnIndex + 1);
    }
  };

  const handleStartDecision = () => {
    setStage(STAGES.DECISION);
    setProbeIndex(0);
    setStartTime(Date.now());
  };

  const handleDecision = (label) => {
    const endTime = Date.now();
    const targetLabel = currentEpisode.scoring.final_probe_targets[probeIndex];
    const isCorrect = label === targetLabel;
    
    const newResult = {
      episodeId: currentEpisode.episode_id,
      task: currentEpisode.analysis.suite_task_id,
      probeIndex,
      userLabel: label,
      targetLabel,
      isCorrect,
      responseTime: endTime - startTime
    };

    setResults([...results, newResult]);

    if (probeIndex < 4) {
      setProbeIndex(probeIndex + 1);
      setStartTime(Date.now());
    } else {
      if (episodeIndex < activeEpisodes.length - 1) {
        setEpisodeIndex(episodeIndex + 1);
        setStage(STAGES.STUDY);
        setTurnIndex(0);
      } else {
        const finalResults = [...results, newResult];
        const sessionReport = {
          id: Date.now(),
          date: new Date().toISOString(),
          totalCorrect: finalResults.filter(r => r.isCorrect).length,
          avgTime: finalResults.reduce((acc, r) => acc + r.responseTime, 0) / finalResults.length,
          episodesCount: activeEpisodes.length
        };
        const updatedHistory = [sessionReport, ...history].slice(0, 10); // Keep last 10
        setHistory(updatedHistory);
        localStorage.setItem('cogflex_history', JSON.stringify(updatedHistory));
        setStage(STAGES.RESULTS);
      }
    }
  };

  const renderStudyTurn = () => {
    const turnText = turns[turnIndex];
    const exampleLines = turnText.split('Examples:\n')[1]?.split('\n') || [];
    const examples = exampleLines.filter(l => l.includes('->')).map(l => parseItem(l.replace(/^\d+\.\s+/, '')));

    return (
      <div className="flex flex-col items-center pt-20">
        {/* Navigation Header */}
        <div className="fixed top-0 left-0 w-full bg-black/80 backdrop-blur-md border-b border-zinc-800 z-50 px-8 py-4 flex items-center justify-between">
          <button 
            onClick={resetGame}
            className="flex items-center gap-4 hover:opacity-80 transition-opacity cursor-pointer text-left"
          >
            <h1 className="text-xl font-black tracking-tighter">
              CogFlex <span className="text-indigo-500">Human</span>
            </h1>
          </button>
          
          <button 
            onClick={resetGame}
            className="px-4 py-2 rounded-xl border border-zinc-800 text-zinc-400 font-black text-[10px] uppercase tracking-widest hover:bg-zinc-900 transition-all cursor-pointer flex items-center gap-2"
          >
            Abort Session
          </button>
        </div>

        <div className="mb-4 text-indigo-400 font-mono uppercase tracking-widest text-sm mt-8">
          Challenge {episodeIndex + 1} of {activeEpisodes.length} — Step {turnIndex + 1} of {turns.length - 1}
        </div>
        <h2 className="text-4xl font-black mb-4 tracking-tight">Learn the Rule</h2>
        <p className="text-gray-400 mb-10 max-w-2xl text-lg leading-relaxed">
          {turnText.split('\n\n')[1]?.split('\n')[0] || "Analyze the examples to deduce the current logic."}
        </p>
        
        <div className="flex flex-wrap justify-center gap-8 mb-12">
          {examples.map((ex, i) => (
            <div key={i} className="flex flex-col items-center">
              <span className="mb-2 text-[10px] font-bold text-gray-600 uppercase">Example {i + 1}</span>
              <Card data={ex} />
            </div>
          ))}
        </div>

        <button 
          onClick={handleNextTurn}
          className="bg-white text-black hover:bg-gray-200 px-12 py-4 rounded-xl font-black text-lg transition-all duration-300 shadow-xl shadow-white/5 active:scale-[0.98] cursor-pointer"
        >
          {turnIndex === turns.length - 2 ? "Ready for Challenge?" : "Next Evidence Step"}
        </button>
      </div>
    );
  };

  const renderShift = () => {
    return (
      <div className="flex flex-col items-center animate-pulse">
        <div className="bg-red-600 text-white text-4xl font-black p-8 rounded-2xl mb-8 shadow-2xl">
          THE RULE HAS CHANGED!
        </div>
        <p className="text-xl text-gray-300 mb-10">Prepare for the final decision.</p>
        <button 
          onClick={handleStartDecision}
          className="bg-white text-black px-12 py-4 rounded-full font-black text-xl hover:bg-gray-200 transition-all cursor-pointer"
        >
          START PROBES
        </button>
      </div>
    );
  };

  const renderDecision = () => {
    const turnText = turns[turns.length - 1];
    const probeLines = turnText.split('Probes:\n')[1]?.split('\n\n')[0].split('\n') || [];
    const currentProbeText = probeLines[probeIndex].replace(/^\d+\.\s+/, '').replace(' -> ?', '');
    const currentProbe = parseItem(currentProbeText);

    const renderProbeTracker = () => {
      const episodeResults = results.filter(r => r.episodeId === currentEpisode.episode_id);
      return (
        <div className="flex gap-2 mb-8">
          {[0, 1, 2, 3, 4].map(i => {
            const res = episodeResults.find(r => r.probeIndex === i);
            return (
              <div 
                key={i}
                className={`w-12 h-14 rounded-xl border-2 flex flex-col items-center justify-center transition-all ${
                  res 
                    ? (res.isCorrect ? 'bg-green-600/20 border-green-500 text-green-500' : 'bg-red-600/20 border-red-500 text-red-500')
                    : (i === probeIndex ? 'bg-indigo-900/40 border-indigo-400 text-indigo-400 animate-pulse' : 'bg-gray-900 border-gray-800 text-gray-700')
                }`}
              >
                <span className="text-[10px] font-bold mb-1">{i + 1}</span>
                {res ? (res.isCorrect ? <Check size={18} strokeWidth={3} /> : <X size={18} strokeWidth={3} />) : <Box size={14} />}
              </div>
            );
          })}
        </div>
      );
    };

    return (
      <div className="flex flex-col items-center pt-20">
        {/* Navigation Header */}
        <div className="fixed top-0 left-0 w-full bg-black/80 backdrop-blur-md border-b border-zinc-800 z-50 px-8 py-4 flex items-center justify-between">
          <button 
            onClick={resetGame}
            className="flex items-center gap-4 hover:opacity-80 transition-opacity cursor-pointer text-left"
          >
            <h1 className="text-xl font-black tracking-tighter">
              CogFlex <span className="text-indigo-500">Human</span>
            </h1>
          </button>
          
          <button 
            onClick={resetGame}
            className="px-4 py-2 rounded-xl border border-zinc-800 text-zinc-400 font-black text-[10px] uppercase tracking-widest hover:bg-zinc-900 transition-all cursor-pointer flex items-center gap-2"
          >
            Abort Session
          </button>
        </div>

        <div className="mb-2 text-indigo-400 font-mono uppercase tracking-widest text-sm mt-8">
          Challenge {episodeIndex + 1} of {activeEpisodes.length} — Final Decision Phase
        </div>
        {renderProbeTracker()}
        <h2 className="text-4xl font-black mb-10 tracking-tight">Classify this Object</h2>
        <Card data={currentProbe} showLabel={false} />
        
        <div className="flex gap-6 mt-12">
          {possibleLabels.map(label => (
            <button 
              key={label}
              onClick={() => handleDecision(label)}
              className="px-12 py-5 rounded-2xl border-4 border-indigo-600 text-indigo-400 font-black text-2xl hover:bg-indigo-600 hover:text-white transition-all duration-300 capitalize active:scale-[0.98] shadow-lg shadow-indigo-900/20 cursor-pointer"
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    );
  };

  const renderResults = () => {
    const totalCorrect = results.filter(r => r.isCorrect).length;
    const avgTime = results.reduce((acc, r) => acc + r.responseTime, 0) / results.length;
    const totalProbes = activeEpisodes.length * 5;
    
    return (
      <div className="flex flex-col items-center w-full max-w-7xl py-12 px-4 mt-20">
        {/* Persistent Results Header */}
        <div className="fixed top-0 left-0 w-full bg-black/80 backdrop-blur-md border-b border-zinc-800 z-50 px-8 py-4 flex items-center justify-between">
          <button 
            onClick={resetGame}
            className="flex items-center gap-4 hover:opacity-80 transition-opacity cursor-pointer text-left"
          >
            <h1 className="text-2xl font-black tracking-tighter">
              CogFlex <span className="text-indigo-500">Human</span>
            </h1>
          </button>
          
          <div className="flex items-center gap-3">
            <button 
              onClick={handleStart}
              className="px-6 py-2 rounded-xl bg-white text-black font-black text-xs uppercase tracking-widest hover:bg-zinc-200 transition-all cursor-pointer flex items-center gap-2"
            >
              <Zap size={14} className="fill-black" />
              New Session
            </button>
          </div>
        </div>

        <div className="text-center mb-16">
          <h1 className="text-7xl font-black mb-4 tracking-tighter bg-gradient-to-b from-white to-zinc-500 bg-clip-text text-transparent">
            Assessment Report
          </h1>
          <p className="text-zinc-500 font-mono uppercase tracking-[0.2em] text-sm">Cognitive Flexibility Baseline Analysis</p>
        </div>
        
        {/* Top Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full mb-20">
          <div className="group relative bg-zinc-900/40 p-10 rounded-[2.5rem] border border-zinc-800/50 backdrop-blur-xl transition-all hover:bg-zinc-900/60 hover:border-zinc-700">
            <div className="absolute top-8 right-10 text-green-500/20 group-hover:text-green-500/40 transition-colors">
              <Check size={48} strokeWidth={3} />
            </div>
            <div className="text-zinc-500 text-[10px] font-black uppercase tracking-[0.2em] mb-4">Success Rate</div>
            <div className="text-7xl font-black text-white mb-2">{((totalCorrect / totalProbes) * 100).toFixed(0)}<span className="text-3xl text-zinc-600">%</span></div>
            <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
              <div className="h-full bg-green-500 transition-all duration-1000" style={{ width: `${(totalCorrect / totalProbes) * 100}%` }}></div>
            </div>
            <p className="text-zinc-500 text-xs mt-4 font-bold">{totalCorrect} / {totalProbes} Identifications Correct</p>
          </div>

          <div className="group relative bg-zinc-900/40 p-10 rounded-[2.5rem] border border-zinc-800/50 backdrop-blur-xl transition-all hover:bg-zinc-900/60 hover:border-zinc-700">
            <div className="absolute top-8 right-10 text-blue-500/20 group-hover:text-blue-500/40 transition-colors">
              <Zap size={48} strokeWidth={3} />
            </div>
            <div className="text-zinc-500 text-[10px] font-black uppercase tracking-[0.2em] mb-4">Neural Latency</div>
            <div className="text-7xl font-black text-white mb-2">{(avgTime / 1000).toFixed(2)}<span className="text-3xl text-zinc-600">s</span></div>
            <div className="flex gap-1">
              {[1,2,3,4,5,6,7,8].map(i => (
                <div key={i} className={`h-1.5 flex-1 rounded-full ${i < 4 ? 'bg-blue-500' : 'bg-zinc-800'}`}></div>
              ))}
            </div>
            <p className="text-zinc-500 text-xs mt-4 font-bold">Average Response Speed</p>
          </div>

          <div className="group relative bg-zinc-900/40 p-10 rounded-[2.5rem] border border-zinc-800/50 backdrop-blur-xl transition-all hover:bg-zinc-900/60 hover:border-zinc-700">
            <div className="absolute top-8 right-10 text-indigo-500/20 group-hover:text-indigo-500/40 transition-colors">
              <Star size={48} strokeWidth={3} />
            </div>
            <div className="text-zinc-500 text-[10px] font-black uppercase tracking-[0.2em] mb-4">Flexibility Index</div>
            <div className="text-7xl font-black text-white mb-2">{Math.round((totalCorrect * 1000) / (avgTime / 100))}</div>
            <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500 transition-all duration-1000" style={{ width: '65%' }}></div>
            </div>
            <p className="text-zinc-500 text-xs mt-4 font-bold">Precision-Velocity Ratio</p>
          </div>
        </div>

        {/* Detailed Challenges Section */}
        <div className="w-full space-y-16">
          <div className="flex items-center gap-4 mb-4">
            <div className="h-px flex-1 bg-zinc-800"></div>
            <h2 className="text-zinc-500 text-xs font-black uppercase tracking-[0.3em]">Detailed Challenge Breakdown</h2>
            <div className="h-px flex-1 bg-zinc-800"></div>
          </div>

          {activeEpisodes.map((episode, epIdx) => {
            const epResults = results.filter(r => r.episodeId === episode.episode_id);
            const epCorrect = epResults.filter(r => r.isCorrect).length;
            
            return (
              <div key={episode.episode_id} className="group relative bg-zinc-950 rounded-[3rem] border border-zinc-800 overflow-hidden transition-all hover:border-zinc-600">
                <div className="bg-zinc-900/80 px-12 py-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-zinc-800">
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <span className="px-3 py-1 bg-indigo-500/10 text-indigo-400 text-[10px] font-black rounded-full border border-indigo-500/20 uppercase tracking-widest">Challenge {epIdx + 1}</span>
                      <span className="px-3 py-1 bg-zinc-800 text-zinc-400 text-[10px] font-black rounded-full uppercase tracking-widest">{episode.analysis.difficulty_bin}</span>
                    </div>
                    <h3 className="text-4xl font-black text-white tracking-tight uppercase">{episode.analysis.suite_task_id.replace(/_/g, ' ')}</h3>
                    <p className="text-zinc-400 font-mono text-sm mt-2 uppercase tracking-[0.15em] font-bold">{episode.analysis.structure_family_id.replace(/_/g, ' ')}</p>
                  </div>
                  <div className="flex items-center gap-8 bg-black/40 px-8 py-6 rounded-3xl border border-white/5">
                    <div className="text-center">
                      <div className="text-4xl font-black text-white">{epCorrect}<span className="text-xl text-zinc-600">/5</span></div>
                      <div className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Accuracy</div>
                    </div>
                    <div className="w-px h-10 bg-zinc-800"></div>
                    <div className="text-center">
                      <div className="text-4xl font-black text-white">{(epResults.reduce((acc, r) => acc + r.responseTime, 0) / 5000).toFixed(2)}<span className="text-xl text-zinc-600">s</span></div>
                      <div className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Avg Speed</div>
                    </div>
                  </div>
                </div>

                <div className="p-12 space-y-16">
                  {/* Step History with Large View */}
                  <div className="space-y-6">
                    <div className="flex items-center gap-4">
                      <h4 className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em]">Learning Evidence Flow</h4>
                      <div className="h-px flex-1 bg-zinc-800/50"></div>
                    </div>
                    <div className="grid grid-cols-1 gap-8">
                      {episode.inference.turns.slice(0, -1).map((turn, tIdx) => (
                        <div key={tIdx} className="bg-zinc-900/30 rounded-[2rem] p-10 border border-white/5">
                          <div className="flex items-center gap-4 mb-8">
                            <span className="w-8 h-8 rounded-full bg-indigo-500 text-black flex items-center justify-center font-black text-xs">{tIdx + 1}</span>
                            <span className="text-sm font-black text-white uppercase tracking-widest">{tIdx === 0 ? "Initial Rule Set" : "Rule Shift Evidence"}</span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10">
                            {turn.split('Examples:\n')[1]?.split('\n').filter(l => l.includes('->')).map((ex, i) => (
                              <div key={i} className="flex flex-col items-center">
                                <Card data={parseItem(ex.replace(/^\d+\.\s+/, ''))} />
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Decision Grid with Better Visual Feedback */}
                  <div className="space-y-6">
                    <div className="flex items-center gap-4">
                      <h4 className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em]">Decision Matrix</h4>
                      <div className="h-px flex-1 bg-zinc-800/50"></div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8">
                      {epResults.map((res, i) => (
                        <div key={i} className={`relative p-8 rounded-[2.5rem] border-2 transition-all ${res.isCorrect ? 'border-green-500/20 bg-green-500/[0.02]' : 'border-red-500/20 bg-red-500/[0.02]'}`}>
                          <div className={`absolute top-6 right-6 ${res.isCorrect ? 'text-green-500' : 'text-red-500'}`}>
                            {res.isCorrect ? <Check size={20} strokeWidth={4} /> : <X size={20} strokeWidth={4} />}
                          </div>
                          <div className="text-[10px] font-black text-zinc-600 mb-6 tracking-widest uppercase text-center">Probe {i + 1}</div>
                          <div className="mb-8 flex justify-center">
                            <Card data={parseItem(episode.inference.turns[episode.inference.turns.length - 1].split('Probes:\n')[1].split('\n')[i].replace(/^\d+\.\s+/, '').replace(' -> ?', ''))} showLabel={false} />
                          </div>
                          <div className="space-y-4">
                            <div className="w-full bg-zinc-950/80 rounded-2xl border border-white/10 overflow-hidden">
                              {/* Input Row */}
                              <div className="flex flex-col p-4 space-y-1 items-center text-center">
                                <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Your Input</span>
                                <span className={`text-base font-black uppercase truncate w-full ${res.isCorrect ? 'text-green-400' : 'text-red-400'}`}>
                                  {res.userLabel}
                                </span>
                              </div>
                              
                              {/* Divider with Icon */}
                              <div className="relative h-px bg-white/10 mx-4">
                                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-zinc-950 px-2">
                                  {res.isCorrect ? 
                                    <Check size={10} className="text-green-500/50" /> : 
                                    <X size={10} className="text-red-500/50" />
                                  }
                                </div>
                              </div>

                              {/* Target Row */}
                              <div className="flex flex-col p-4 space-y-1 items-center text-center">
                                <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Answer</span>
                                <span className="text-base font-black uppercase text-white truncate w-full">
                                  {res.targetLabel}
                                </span>
                              </div>
                            </div>
                             <div className="flex items-center justify-center gap-1.5 py-1.5 px-3 bg-white/[0.03] rounded-full border border-white/5 mx-auto w-fit mt-2">
                               <Timer size={14} className="text-zinc-500" />
                               <span className="text-[13px] font-mono text-zinc-400 font-bold tabular-nums tracking-tight leading-none">
                                 {(res.responseTime / 1000).toFixed(2)}s
                               </span>
                             </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };


  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-8 font-sans transition-all duration-300">
      {/* Mobile Block Overlay */}
      <div className="lg:hidden fixed inset-0 z-[100] bg-black flex flex-col items-center justify-center p-10 text-center">
        <Box size={64} className="text-indigo-500 mb-6" />
        <h1 className="text-3xl font-black mb-4">Desktop Only</h1>
        <p className="text-zinc-500 leading-relaxed">
          The CogFlex Human Benchmark requires a larger screen to display complex cognitive patterns and evidence flows correctly. 
          Please access this page from a tablet (landscape) or desktop computer.
        </p>
      </div>

      {stage !== STAGES.START && stage !== STAGES.RESULTS && activeEpisodes.length > 0 && (
        <div className="fixed top-0 left-0 w-full h-2 bg-gray-900">
          <div 
            className="h-full bg-indigo-500 transition-all duration-300"
            style={{ width: `${((episodeIndex * 5 + (stage === STAGES.DECISION ? probeIndex : 0)) / (activeEpisodes.length * 5)) * 100}%` }}
          ></div>
        </div>
      )}
      {stage === STAGES.START && (
        <div className="w-full max-w-5xl flex flex-col items-center py-12 px-6">
          {/* Header Section */}
          <div className="text-center mb-20">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-black uppercase tracking-[0.3em] mb-8 animate-fade-in">
              <Activity size={12} />
              Human Performance Benchmark
            </div>
            <h1 className="text-8xl font-black mb-6 tracking-tighter bg-gradient-to-b from-white to-zinc-500 bg-clip-text text-transparent leading-[1.1] py-2">
              CogFlex
            </h1>
            <p className="text-xl text-zinc-400 max-w-2xl mx-auto leading-relaxed font-medium">
              Measure your cognitive flexibility against frontier AI models. 
              Adapt to rule shifts in real-time and establish the human baseline.
            </p>
          </div>

          {/* Sections Stack: Protocol & History */}
          <div className="flex flex-col gap-20 w-full max-w-4xl">
            {/* Top: How it works */}
            <div className="space-y-10">
              <div className="flex items-center gap-6">
                <h3 className="text-white text-xs font-black uppercase tracking-[0.4em] whitespace-nowrap">Protocol Specification</h3>
                <div className="h-px flex-1 bg-zinc-800/50"></div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { icon: <Brain size={20} />, title: "Inference", desc: "Study 4 examples to deduce the current classification logic." },
                  { icon: <Zap size={20} />, title: "Adaptation", desc: "Alert: Rules shift without warning. Stay agile." },
                  { icon: <Target size={20} />, title: "Precision", desc: "Classify 5 probes per challenge with maximum accuracy." },
                  { icon: <Timer size={20} />, title: "Latency", desc: "Response speed is recorded to calculate efficiency." }
                ].map((step, i) => (
                  <div key={i} className="bg-zinc-900/40 border border-zinc-800/50 p-6 rounded-[2rem] hover:border-zinc-700 transition-all duration-300 group">
                    <div className="w-10 h-10 flex items-center justify-center rounded-xl bg-indigo-500/5 mb-4 group-hover:bg-indigo-500/15 transition-all duration-500">
                      <div className="text-indigo-500 group-hover:scale-110 group-hover:text-indigo-400 transition-all duration-500 ease-out">
                        {step.icon}
                      </div>
                    </div>
                    <div className="text-white font-black text-xs uppercase tracking-widest mb-2">{step.title}</div>
                    <div className="text-zinc-500 text-[11px] leading-relaxed font-bold">{step.desc}</div>
                  </div>
                ))}
              </div>

              <button 
                onClick={handleStart}
                className="w-full bg-white text-black hover:bg-zinc-200 py-6 rounded-[2rem] font-black text-2xl transition-all shadow-[0_0_40px_rgba(255,255,255,0.05)] active:scale-[0.98] cursor-pointer flex items-center justify-center gap-4 group"
              >
                INITIATE CHALLENGE
                <Zap size={24} className="fill-black group-hover:animate-pulse" />
              </button>
            </div>

            {/* Bottom: History */}
            <div className="space-y-8">
              <div className="flex items-center gap-6">
                <h3 className="text-zinc-500 text-xs font-black uppercase tracking-[0.4em] whitespace-nowrap">Session History</h3>
                <div className="h-px flex-1 bg-zinc-800/50"></div>
              </div>

              {history.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {history.map(session => (
                    <div key={session.id} className="bg-zinc-900/30 border border-zinc-800/50 p-5 rounded-2xl flex items-center justify-between group hover:bg-zinc-900/60 transition-all">
                      <div className="flex items-center gap-5">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-black text-sm border-2 ${
                          (session.totalCorrect / (session.episodesCount * 5)) > 0.8 
                          ? 'bg-green-500/10 border-green-500/20 text-green-500' 
                          : 'bg-zinc-800/50 border-zinc-700/50 text-zinc-500'
                        }`}>
                          {Math.round((session.totalCorrect / (session.episodesCount * 5)) * 100)}%
                        </div>
                        <div>
                          <div className="text-zinc-100 font-black text-sm tracking-tight capitalize">
                            {new Date(session.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} • {new Date(session.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                          <div className="text-zinc-500 text-[10px] uppercase font-black tracking-[0.15em] mt-1 flex items-center gap-2">
                            <span className="text-zinc-400">{session.totalCorrect}/{session.episodesCount * 5} Hits</span>
                            <span className="w-1 h-1 rounded-full bg-zinc-700"></span>
                            <span>{(session.avgTime / 1000).toFixed(2)}s Latency</span>
                          </div>
                        </div>
                      </div>
                      <div className="text-zinc-800 group-hover:text-zinc-600 transition-colors">
                        <History size={18} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-32 rounded-[2rem] border-2 border-dashed border-zinc-900/50 flex flex-col items-center justify-center text-center p-8">
                  <Activity size={24} className="text-zinc-800 mb-2" />
                  <p className="text-zinc-600 text-[10px] font-black uppercase tracking-widest leading-relaxed">
                    No session data available
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {stage === STAGES.STUDY && renderStudyTurn()}
      {stage === STAGES.SHIFT && renderShift()}
      {stage === STAGES.DECISION && renderDecision()}
      {stage === STAGES.RESULTS && renderResults()}
    </div>
  );
}
