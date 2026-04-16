import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Card } from './Card';

describe('Card component', () => {
  const defaultData = {
    r1: '10',
    r2: '20',
    shape: 'star',
    tone: 'warm',
    label: 'accept'
  };

  it('renders r1 and r2 values', () => {
    render(<Card data={defaultData} />);
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
  });

  it('renders shape name', () => {
    render(<Card data={defaultData} />);
    expect(screen.getAllByText('star')[0]).toBeInTheDocument();
  });

  it('renders tone property', () => {
    render(<Card data={defaultData} />);
    expect(screen.getByText('warm')).toBeInTheDocument();
  });

  it('renders the label if showLabel is true', () => {
    render(<Card data={defaultData} showLabel={true} />);
    expect(screen.getByText('accept')).toBeInTheDocument();
  });

  it('does not render the label if showLabel is false', () => {
    render(<Card data={defaultData} showLabel={false} />);
    expect(screen.queryByText('accept')).not.toBeInTheDocument();
  });

  it('renders fallback color for unknown tone', () => {
    const { container } = render(<Card data={{ ...defaultData, tone: 'unknown' }} />);
    // Check if the fallback class 'bg-white/95' is applied
    const el = container.querySelector('.bg-white\\/95');
    expect(el).toBeInTheDocument();
  });

  it('renders fallback icon for unknown shape', () => {
    render(<Card data={{ ...defaultData, shape: 'unknown_shape' }} />);
    expect(screen.getByText('unknown_shape')).toBeInTheDocument();
  });
});
