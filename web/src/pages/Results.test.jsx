import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Results } from './Results';

vi.mock('../components/MetricCard', () => ({
  MetricCard: ({ title, value }) => <div data-testid={`metric-${title}`}>{value}</div>
}));

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Results Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  const renderResults = (initialUrl = '/results') => {
    render(
      <MemoryRouter initialEntries={[initialUrl]}>
        <Routes>
          <Route path="/results" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('redirects to / if no session data is found', () => {
    renderResults();
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('renders session payload correctly', () => {
    const fakeData = {
      episodes: [
        {
          episode_id: 'ep-1',
          analysis: { suite_task_id: 'task_1', difficulty_bin: 'easy' },
          inference: { response_spec: { probe_count: 2 }, turns: [] },
          scoring: { probe_metadata: [] }
        }
      ],
      results: [
        { episodeId: 'ep-1', isCorrect: true, responseTime: 1000, userLabel: 'accept' },
        { episodeId: 'ep-1', isCorrect: false, responseTime: 2000, userLabel: 'reject' }
      ]
    };
    sessionStorage.setItem('cogflex_last_session', JSON.stringify(fakeData));

    renderResults();
    expect(screen.getByText('Assessment Report')).toBeInTheDocument();
    
    // Check metric cards basic info (Accuracy: 1 correct / 2 probes = 50%)
    expect(screen.getByTestId('metric-Success Rate')).toHaveTextContent('50%');
  });

  it('renders with session id from history', () => {
    const fakeHistory = [
      {
        id: '123',
        episodes: [
          {
            episode_id: 'ep-2',
            analysis: { suite_task_id: 'task_2', difficulty_bin: 'hard' },
            inference: { response_spec: { probe_count: 1 }, turns: [] },
            scoring: { probe_metadata: [] }
          }
        ],
        results: [
          { episodeId: 'ep-2', isCorrect: true, responseTime: 1500, userLabel: 'accept' }
        ]
      }
    ];
    localStorage.setItem('cogflex_history', JSON.stringify(fakeHistory));

    renderResults('/results?id=123');

    expect(screen.getByText('Assessment Report')).toBeInTheDocument();
    expect(screen.getByTestId('metric-Success Rate')).toHaveTextContent('100%');
  });

  it('starts new session when button is clicked', () => {
    const fakeData = {
      episodes: [],
      results: []
    };
    sessionStorage.setItem('cogflex_last_session', JSON.stringify(fakeData));

    renderResults();

    const newSessionBtn = screen.getByText('New Session');
    fireEvent.click(newSessionBtn);

    expect(mockNavigate).toHaveBeenCalled();
    const navigatedUrl = mockNavigate.mock.calls[0][0];
    expect(navigatedUrl).toMatch(/\/challenge\/.+/);
  });
});
