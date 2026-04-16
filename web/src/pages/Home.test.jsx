import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Home } from './Home';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Home Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('renders correctly', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );
    expect(screen.getByRole('heading', { name: /CogFlex/i })).toBeInTheDocument();
    expect(screen.getByText('START CHALLENGE')).toBeInTheDocument();
    expect(screen.getByText('No session data available')).toBeInTheDocument();
  });

  it('clears sessionStorage on mount', () => {
    sessionStorage.setItem('cogflex_active_episodes', 'some-data');
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );
    expect(sessionStorage.getItem('cogflex_active_episodes')).toBeNull();
  });

  it('starts challenge on click', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );
    
    const startBtn = screen.getByText('START CHALLENGE');
    fireEvent.click(startBtn);

    expect(sessionStorage.getItem('cogflex_active_episodes')).not.toBeNull();
    expect(mockNavigate).toHaveBeenCalled();
    const navigatedUrl = mockNavigate.mock.calls[0][0];
    expect(navigatedUrl).toMatch(/\/challenge\/.+/);
  });

  it('renders history and allows clearing it', () => {
    const fakeHistory = [
      { id: '123', date: new Date().toISOString(), totalProbes: 10, totalCorrect: 8, avgTime: 1200 }
    ];
    localStorage.setItem('cogflex_history', JSON.stringify(fakeHistory));

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );
    
    expect(screen.getByText('8/10 Hits')).toBeInTheDocument();
    
    const clearBtn = screen.getByText('Clear History');
    fireEvent.click(clearBtn);

    const confirmModal = screen.getByText('Clear History?');
    expect(confirmModal).toBeInTheDocument();

    const clearAllBtn = screen.getByText('Clear All');
    fireEvent.click(clearAllBtn);

    expect(localStorage.getItem('cogflex_history')).toBeNull();
    expect(screen.getByText('No session data available')).toBeInTheDocument();
  });

  it('allows cancelling history clear', () => {
    const fakeHistory = [
      { id: '123', date: new Date().toISOString(), totalProbes: 10, totalCorrect: 8, avgTime: 1200 }
    ];
    localStorage.setItem('cogflex_history', JSON.stringify(fakeHistory));

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );
    
    fireEvent.click(screen.getByText('Clear History'));
    fireEvent.click(screen.getByText('Cancel'));

    expect(localStorage.getItem('cogflex_history')).not.toBeNull();
    expect(screen.queryByText('Clear History?')).not.toBeInTheDocument();
  });
});
