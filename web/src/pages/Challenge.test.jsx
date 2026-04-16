import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Challenge } from './Challenge';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Challenge Page', () => {
  const mockEpisode = {
    episode_id: 'ep-1',
    analysis: {
      suite_task_id: 'task_1',
      shift_mode: 'explicit_instruction'
    },
    inference: {
      response_spec: { probe_count: 2 },
      turns: [
        'Turn 0\n\nNarrative 0\n\nExamples:\n1. r1=1 | r2=2 -> accept\nUse only labels from: accept, reject.',
        'Turn 1\n\nNarrative 1\n\nExamples:\n1. r1=3 | r2=4 -> reject\nUse only labels from: accept, reject.',
        'Turn 2\n\nNarrative 2\n\nProbes:\n1. r1=5 | r2=6 -> ?\n2. r1=7 | r2=8 -> ?'
      ]
    },
    scoring: {
      final_probe_targets: ['accept', 'reject']
    }
  };

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
  });

  const renderChallenge = (episodeId = 'ep-1') => {
    render(
      <MemoryRouter initialEntries={[`/challenge/${episodeId}`]}>
        <Routes>
          <Route path="/challenge/:episodeId" element={<Challenge />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('redirects to / if no active episodes are found', () => {
    renderChallenge();
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('progresses through Study -> Shift -> Decision -> Next Episode/Results', async () => {
    sessionStorage.setItem('cogflex_active_episodes', JSON.stringify([mockEpisode]));
    renderChallenge();

    // Stage: Study (Turn 0)
    expect(screen.getByText('Learn the Rule')).toBeInTheDocument();
    expect(screen.getByText('Narrative 0')).toBeInTheDocument();
    
    // Click Next Evidence
    fireEvent.click(screen.getByText('Next Evidence'));

    // Stage: Study (Turn 1)
    expect(screen.getByText('Narrative 1')).toBeInTheDocument();
    
    // Click Ready
    fireEvent.click(screen.getByText('Ready?'));

    // Stage: Shift
    expect(screen.getByText('Rule Update')).toBeInTheDocument();
    fireEvent.click(screen.getByText('START PROBES'));

    // Stage: Decision (Probe 0)
    // Buttons should be accept, reject
    expect(screen.getAllByRole('button', { name: /accept/i })[0]).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: /accept/i })[0]);

    // Stage: Decision (Probe 1)
    fireEvent.click(screen.getAllByRole('button', { name: /reject/i })[0]);

    // After last probe, navigates to results (since it's the only episode)
    expect(mockNavigate).toHaveBeenCalledWith('/results');
  });

  it('abort session navigates to home and clears session', () => {
    sessionStorage.setItem('cogflex_active_episodes', JSON.stringify([mockEpisode]));
    renderChallenge();

    fireEvent.click(screen.getByText('Abort Session'));
    
    expect(sessionStorage.getItem('cogflex_active_episodes')).toBeNull();
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });
});
