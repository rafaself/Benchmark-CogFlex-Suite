import React, { useEffect } from 'react';
import { Check, X, Box } from 'lucide-react';
import { Card } from '../Card';
import { getProbeCount, parseItem } from '../../utils/logic';

export function RenderDecision({ currentEpisode, probeIndex, results, onDecision, possibleLabels, feedback }) {
  const turnText = currentEpisode?.inference?.turns[currentEpisode.inference.turns.length - 1];
  const probeLines = turnText.split('Probes:\n')[1]?.split('\n\n')[0].split('\n') || [];
  const currentProbe = parseItem(probeLines[probeIndex].replace(/^\d+\.\s+/, '').replace(' -> ?', ''));
  const epResults = results.filter(r => r.episodeId === currentEpisode.episode_id);
  const probeCount = getProbeCount(currentEpisode);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (feedback) return;
      const key = parseInt(e.key);
      if (key >= 1 && key <= possibleLabels.length) {
        onDecision(possibleLabels[key - 1]);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [possibleLabels, onDecision, feedback]);

  return (
    <div className="flex flex-col items-center">
      <div className="flex gap-2 mb-8">
        {Array.from({ length: probeCount }, (_, i) => i).map(i => (
          <div key={i} className={`w-10 h-12 rounded-lg border-2 flex items-center justify-center transition-all duration-300 ${epResults[i] ? (epResults[i].isCorrect ? 'border-green-500 bg-green-500/10' : 'border-red-500 bg-red-500/10') : (i === probeIndex ? (feedback ? (feedback === 'correct' ? 'border-green-500 bg-green-500/30 scale-110' : 'border-red-500 bg-red-500/30 scale-110') : 'border-indigo-500 animate-pulse') : 'border-zinc-800')}`}>
            {epResults[i] ? (epResults[i].isCorrect ? <Check size={16} /> : <X size={16} />) : (i === probeIndex && feedback ? (feedback === 'correct' ? <Check size={16} className="text-green-500" /> : <X size={16} className="text-red-500" />) : <Box size={12} className="text-zinc-800" />)}
          </div>
        ))}
      </div>
      <div className={`transition-all duration-300 ${feedback ? 'scale-95 opacity-50' : 'scale-100 opacity-100'}`}>
        <Card data={currentProbe} showLabel={false} />
      </div>
      <div className="flex gap-6 mt-12">
        {possibleLabels.map((label, i) => (
          <div key={label} className="flex flex-col items-center gap-3">
            <button onClick={() => onDecision(label)} className={`px-12 py-5 rounded-2xl border-4 text-2xl font-black transition-all capitalize cursor-pointer ${feedback ? 'opacity-50 cursor-not-allowed' : 'border-indigo-600 text-indigo-400 hover:bg-indigo-600 hover:text-white'}`}>{label}</button>
            <span className="text-zinc-600 font-black text-xs uppercase tracking-widest">Press {i + 1}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
