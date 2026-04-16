import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MetricCard } from './MetricCard';

describe('MetricCard component', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders title and sub text', () => {
    render(<MetricCard title="Total Score" sub="Subtext here" value="100" progress={50} color="bg-red-500" />);
    expect(screen.getByText('Total Score')).toBeInTheDocument();
    expect(screen.getByText('Subtext here')).toBeInTheDocument();
  });

  it('animates numeric value', () => {
    render(<MetricCard title="Total" value="100" progress={50} color="bg-red-500" />);
    // Initially should be 0 or near 0
    expect(screen.getByText('0')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(500); // half way
    });
    
    // Should be some intermediate value, but let's just jump to end
    act(() => {
      vi.advanceTimersByTime(600); 
    });

    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('animates value with suffix (e.g. seconds)', () => {
    render(<MetricCard title="Time" value="10.5s" progress={50} color="bg-red-500" />);
    
    act(() => {
      vi.advanceTimersByTime(1100); 
    });

    expect(screen.getByText('10.50s')).toBeInTheDocument();
  });

  it('animates value with other suffix', () => {
    render(<MetricCard title="Percentage" value="99%" progress={50} color="bg-red-500" />);
    
    act(() => {
      vi.advanceTimersByTime(1100); 
    });

    expect(screen.getByText('99%')).toBeInTheDocument();
  });
});
