import React, { useState, useEffect, useRef } from 'react';
import data from './data.json';

const STAGES = {
  START: 'START',
  STUDY: 'STUDY',
  SHIFT: 'SHIFT',
  DECISION: 'DECISION',
  RESULTS: 'RESULTS',
};

function parseItem(itemStr) {
  const [attributes, label] = itemStr.split(' -> ');
  const parts = attributes.split('|').map(p => p.trim());
  const obj = { label };
  parts.forEach(p => {
    const [key, val] = p.split('=');
    if (key && val) obj[key.trim()] = val.trim();
  });
  return obj;
}

const Card = ({ data, showLabel = true }) => {
  const isCorrect = data.label === 'accept' || data.label === 'anchor' || data.label === 'valid' || data.label === 'north' || data.label === 'amber' || data.label === 'ember';
  
  const getToneColor = (tone) => {
    const tones = {
      warm: 'bg-orange-100 border-orange-300',
      cool: 'bg-blue-100 border-blue-300',
      bright: 'bg-yellow-100 border-yellow-300',
      muted: 'bg-gray-200 border-gray-400',
      neutral: 'bg-slate-100 border-slate-300',
      dim: 'bg-indigo-100 border-indigo-300',
    };
    return tones[tone] || 'bg-white border-gray-200';
  };

  const getShapeIcon = (shape) => {
    const icons = {
      star: '⭐',
      triangle: '▲',
      circle: '●',
      square: '■',
      diamond: '◆',
      pentagon: '⬠',
      kite: '🪁',
      oval: '⬭',
    };
    return icons[shape] || '?';
  };

  return (
    <div className={`relative w-48 h-64 border-4 rounded-xl flex flex-col items-center justify-center p-4 shadow-lg ${getToneColor(data.tone)} transition-all hover:scale-105`}>
      <div className="absolute top-2 left-2 text-xs font-bold text-gray-500">R1: {data.r1}</div>
      <div className="absolute top-2 right-2 text-xs font-bold text-gray-500">R2: {data.r2}</div>
      <div className="text-6xl mb-4">{getShapeIcon(data.shape)}</div>
      <div className="text-sm font-medium uppercase tracking-widest text-gray-600">{data.shape}</div>
      <div className="text-xs text-gray-400 mt-1">{data.tone}</div>
      
      {showLabel && data.label && (
        <div className={`mt-4 px-3 py-1 rounded-full text-xs font-bold uppercase ${
          ['accept', 'anchor', 'valid', 'north', 'amber', 'ember'].includes(data.label) 
          ? 'bg-green-500 text-white' 
          : 'bg-red-500 text-white'
        }`}>
          {data.label}
        </div>
      )}
    </div>
  );
};

export default function App() {
  const [stage, setStage] = useState(STAGES.START);
  const [episodeIndex, setEpisodeIndex] = useState(0);
  const [turnIndex, setTurnIndex] = useState(0);
  const [probeIndex, setProbeIndex] = useState(0);
  const [results, setResults] = useState([]);
  const [startTime, setStartTime] = useState(null);

  const currentEpisode = data[episodeIndex];
  const turns = currentEpisode.inference.turns;
  
  // Extract possible labels from the last turn
  const lastTurnText = turns[turns.length - 1];
  const labelMatch = lastTurnText.match(/Use only labels from: (.*)\./);
  const possibleLabels = labelMatch ? labelMatch[1].split(', ') : ['accept', 'reject'];

  const handleStart = () => {
    setStage(STAGES.STUDY);
    setTurnIndex(0);
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
      if (episodeIndex < data.length - 1) {
        setEpisodeIndex(episodeIndex + 1);
        setStage(STAGES.STUDY);
        setTurnIndex(0);
      } else {
        setStage(STAGES.RESULTS);
      }
    }
  };

  const renderStudyTurn = () => {
    const turnText = turns[turnIndex];
    const exampleLines = turnText.split('Examples:\n')[1]?.split('\n') || [];
    const examples = exampleLines.filter(l => l.includes('->')).map(l => parseItem(l.replace(/^\d+\.\s+/, '')));

    return (
      <div className="flex flex-col items-center">
        <h2 className="text-2xl font-bold mb-4">Turn {turnIndex + 1} of {turns.length}</h2>
        <p className="text-gray-400 mb-8 max-w-2xl">{turnText.split('\n\n')[1] || "Study the patterns."}</p>
        <div className="flex flex-wrap justify-center gap-6 mb-10">
          {examples.map((ex, i) => <Card key={i} data={ex} />)}
        </div>
        <button 
          onClick={handleNextTurn}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3 rounded-lg font-bold transition-colors"
        >
          {turnIndex === turns.length - 2 ? "Ready for Change?" : "Next Evidence"}
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
          className="bg-white text-black px-12 py-4 rounded-full font-black text-xl hover:bg-gray-200 transition-all"
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

    return (
      <div className="flex flex-col items-center">
        <div className="mb-4 text-indigo-400 font-mono">Episode {episodeIndex + 1}/5 | Probe {probeIndex + 1}/5</div>
        <h2 className="text-3xl font-bold mb-8">What is the correct label?</h2>
        <Card data={currentProbe} showLabel={false} />
        <div className="flex gap-4 mt-12">
          {possibleLabels.map(label => (
            <button 
              key={label}
              onClick={() => handleDecision(label)}
              className="px-10 py-4 rounded-xl border-2 border-indigo-500 text-indigo-400 font-bold text-xl hover:bg-indigo-500 hover:text-white transition-all capitalize"
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
    
    return (
      <div className="flex flex-col items-center max-w-4xl w-full">
        <h1 className="text-5xl font-black mb-4">Results</h1>
        <div className="grid grid-cols-3 gap-8 w-full mb-12">
          <div className="bg-gray-800 p-6 rounded-2xl">
            <div className="text-gray-400 text-sm uppercase">Accuracy</div>
            <div className="text-4xl font-bold text-green-400">{((totalCorrect / 25) * 100).toFixed(1)}%</div>
          </div>
          <div className="bg-gray-800 p-6 rounded-2xl">
            <div className="text-gray-400 text-sm uppercase">Avg. Speed</div>
            <div className="text-4xl font-bold text-blue-400">{(avgTime / 1000).toFixed(2)}s</div>
          </div>
          <div className="bg-gray-800 p-6 rounded-2xl">
            <div className="text-gray-400 text-sm uppercase">Score</div>
            <div className="text-4xl font-bold text-indigo-400">{totalCorrect}/25</div>
          </div>
        </div>

        <div className="w-full bg-gray-800 rounded-2xl overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-gray-700">
              <tr>
                <th className="p-4">Task</th>
                <th className="p-4">Correct</th>
                <th className="p-4">Avg Speed</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(results.reduce((acc, r) => ({...acc, [r.task]: 1}), {})).map(task => {
                const taskResults = results.filter(r => r.task === task);
                const taskCorrect = taskResults.filter(r => r.isCorrect).length;
                const taskTime = taskResults.reduce((acc, r) => acc + r.responseTime, 0) / taskResults.length;
                return (
                  <tr key={task} className="border-t border-gray-700">
                    <td className="p-4 capitalize">{task.replace(/_/g, ' ')}</td>
                    <td className="p-4">{taskCorrect}/5</td>
                    <td className="p-4">{(taskTime / 1000).toFixed(2)}s</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <button 
          onClick={() => window.location.reload()}
          className="mt-12 bg-white text-black px-10 py-3 rounded-lg font-bold hover:bg-gray-200"
        >
          Try Again
        </button>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-8 font-sans">
      {stage === STAGES.START && (
        <div className="text-center max-w-2xl">
          <h1 className="text-6xl font-black mb-6 tracking-tighter">CogFlex <span className="text-indigo-500">Human</span></h1>
          <p className="text-xl text-gray-400 mb-10">
            Compare your cognitive flexibility with the world's most advanced AI models. 
            Can you adapt to changing rules faster than a LLM?
          </p>
          <div className="bg-gray-900 p-6 rounded-xl text-left mb-10 border border-gray-800">
            <h3 className="font-bold mb-2">How it works:</h3>
            <ul className="text-sm text-gray-400 space-y-2">
              <li>1. Study labeled examples to infer the active rule.</li>
              <li>2. Watch for rule changes (they happen often!).</li>
              <li>3. Classify 5 probes as quickly as possible.</li>
              <li>4. Complete 5 diverse tasks to get your baseline.</li>
            </ul>
          </div>
          <button 
            onClick={handleStart}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-12 py-4 rounded-full font-black text-xl transition-all shadow-lg shadow-indigo-500/20"
          >
            BEGIN CHALLENGE
          </button>
        </div>
      )}

      {stage === STAGES.STUDY && renderStudyTurn()}
      {stage === STAGES.SHIFT && renderShift()}
      {stage === STAGES.DECISION && renderDecision()}
      {stage === STAGES.RESULTS && renderResults()}
    </div>
  );
}
