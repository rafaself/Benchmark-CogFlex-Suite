import { describe, it, expect } from 'vitest';
import {
  shuffleArray,
  parseItem,
  getPossibleLabels,
  getRuleDescription,
  getEpisodeExampleGroups,
  getEpisodeProbes,
  getLabelStyle,
  getProbeCount,
  getTotalProbeCount,
  getProbeOffset
} from './logic';

describe('logic.js', () => {
  describe('shuffleArray', () => {
    it('should return an array of the same length', () => {
      const arr = [1, 2, 3, 4, 5];
      const result = shuffleArray(arr);
      expect(result.length).toBe(arr.length);
    });

    it('should contain all the original elements', () => {
      const arr = [1, 2, 3];
      const result = shuffleArray(arr);
      expect(result).toEqual(expect.arrayContaining(arr));
    });

    it('should not mutate original array', () => {
      const arr = [1, 2, 3];
      const result = shuffleArray(arr);
      expect(result).not.toBe(arr);
    });
  });

  describe('parseItem', () => {
    it('should parse simple item correctly', () => {
      const result = parseItem('r1=1 | r2=2 -> accept');
      expect(result).toEqual({ r1: '1', r2: '2', label: 'accept' });
    });

    it('should parse comma separated items correctly', () => {
      const result = parseItem('a=1, b=2 -> reject');
      expect(result).toEqual({ a: '1', b: '2', label: 'reject' });
    });
  });

  describe('getPossibleLabels', () => {
    it('should parse labels from instruction', () => {
      const turns = ['Some text\nUse only labels from: accept, reject, maybe.'];
      const result = getPossibleLabels(turns);
      expect(result).toEqual(['accept', 'reject', 'maybe']);
    });

    it('should return default labels if not found', () => {
      const turns = ['No labels here'];
      const result = getPossibleLabels(turns);
      expect(result).toEqual(['accept', 'reject']);
    });
  });

  describe('getRuleDescription', () => {
    it('should return mapped description', () => {
      expect(getRuleDescription('accept_diagonal_pull')).toBe('Accept when |r1-r2| is at least 4.');
    });

    it('should return humanized rule id if not mapped', () => {
      expect(getRuleDescription('unknown_rule_id')).toBe('Unknown Rule Id');
    });

    it('should return empty string if no rule id', () => {
      expect(getRuleDescription(null)).toBe('');
    });
  });

  describe('getLabelStyle', () => {
    it('should return correct style for accept', () => {
      expect(getLabelStyle('accept')).toContain('bg-green-500');
    });
    it('should return correct style for reject', () => {
      expect(getLabelStyle('reject')).toContain('bg-red-500');
    });
    it('should return correct style for amber', () => {
      expect(getLabelStyle('amber')).toContain('bg-orange-500');
    });
    it('should return correct style for frost', () => {
      expect(getLabelStyle('frost')).toContain('bg-blue-500');
    });
    it('should return default style for unknown', () => {
      expect(getLabelStyle('unknown')).toContain('bg-zinc-500');
    });
  });

  describe('Probe Counts', () => {
    const ep1 = { inference: { response_spec: { probe_count: 5 } } };
    const ep2 = { inference: { response_spec: { probe_count: 10 } } };

    it('getProbeCount should return count', () => {
      expect(getProbeCount(ep1)).toBe(5);
      expect(getProbeCount(null)).toBe(0);
    });

    it('getTotalProbeCount should return total', () => {
      expect(getTotalProbeCount([ep1, ep2])).toBe(15);
    });

    it('getProbeOffset should calculate correct offset', () => {
      const eps = [ep1, ep2, ep1];
      expect(getProbeOffset(eps, 0)).toBe(0);
      expect(getProbeOffset(eps, 1)).toBe(5);
      expect(getProbeOffset(eps, 2)).toBe(15);
    });
  });

  describe('getEpisodeExampleGroups and getEpisodeProbes', () => {
    const episode = {
      inference: {
        turns: [
          'Initial context\n\nExamples:\n1. r1=1 | r2=2 -> accept',
          'Next turn\n\nExamples:\n1. r1=3 | r2=4 -> reject',
          'Probes:\n1. r1=5 | r2=6 -> ?\n2. r1=7 | r2=8 -> ?'
        ]
      },
      scoring: {
        probe_metadata: [
          { active_rule_id: 'accept_diagonal_pull' },
          { active_rule_id: 'accept_diagonal_pull' }
        ]
      }
    };

    it('should extract example groups correctly', () => {
      const groups = getEpisodeExampleGroups(episode);
      expect(groups).toHaveLength(2);
      expect(groups[0].examples[0].data).toEqual({ r1: '1', r2: '2', label: 'accept' });
      expect(groups[1].examples[0].data).toEqual({ r1: '3', r2: '4', label: 'reject' });
    });

    it('should extract probes correctly', () => {
      const probes = getEpisodeProbes(episode);
      expect(probes).toHaveLength(2);
      expect(probes[0].data).toEqual({ r1: '5', r2: '6', label: undefined });
      expect(probes[0].ruleId).toBe('accept_diagonal_pull');
    });
  });

  describe('getEpisodeExampleGroups with different suite_task_ids', () => {
    it('handles context_binding', () => {
      const episode = {
        analysis: { suite_task_id: 'context_binding' },
        inference: {
          turns: [
            'Examples:\n1. r1=1 | r2=2, context=sun -> accept'
          ]
        },
        scoring: {
          probe_metadata: [
            { route_metadata: { context: 'sun', route_rule_id: 'accept_diagonal_pull' } }
          ]
        }
      };
      const groups = getEpisodeExampleGroups(episode);
      expect(groups[0].examples[0].ruleId).toBe('accept_diagonal_pull');
    });

    it('handles trial_cued_switch with and without cue', () => {
      const episode = {
        analysis: { suite_task_id: 'trial_cued_switch' },
        inference: {
          turns: [
            'Examples:\n1. r1=1 | r2=2, cue=foo -> accept\n2. r1=1 | r2=2 -> accept'
          ]
        },
        scoring: {
          probe_metadata: [
            { route_metadata: { cue: 'foo', route_rule_id: 'accept_diagonal_pull' } },
            { active_rule_id: 'accept_tone_bright_or_r2_negative' }
          ]
        }
      };
      const groups = getEpisodeExampleGroups(episode);
      expect(groups[0].examples[0].ruleId).toBe('accept_diagonal_pull');
      expect(groups[0].examples[1].ruleId).toBe('accept_tone_bright_or_r2_negative');
    });

    it('handles explicit_rule_update and shifted evidence', () => {
      const episode = {
        analysis: { suite_task_id: 'explicit_rule_update' },
        inference: {
          turns: [
            'Turn 1\n\nNarrative\n\nExamples:\n1. r1=1 -> accept',
            'Turn 2\n\nReplacement rule is now active.\n\nExamples:\n1. r1=2 -> reject'
          ]
        },
        scoring: {
          probe_metadata: [
            { active_rule_id: 'accept_diagonal_pull' },
            { active_rule_id: 'accept_tone_bright_or_r2_negative' }
          ]
        }
      };
      const groups = getEpisodeExampleGroups(episode);
      // first turn uses source rule
      expect(groups[0].examples[0].ruleId).toBe('accept_tone_bright_or_r2_negative');
      // second turn uses target rule
      expect(groups[1].examples[0].ruleId).toBe('accept_diagonal_pull');
    });

    it('handles single active rule mapping', () => {
      const episode = {
        inference: { turns: ['Examples:\n1. r1=1 -> accept'] },
        scoring: { probe_metadata: [{ active_rule_id: 'amber_cobalt_jade_shape_tone' }] }
      };
      const groups = getEpisodeExampleGroups(episode);
      expect(groups[0].examples[0].ruleId).toBe('amber_cobalt_jade_shape_tone');
    });
  });

  describe('getLabelStyle additional branches', () => {
    it('returns noir color', () => {
      expect(getLabelStyle('noir')).toContain('bg-zinc-800');
    });
  });
});
