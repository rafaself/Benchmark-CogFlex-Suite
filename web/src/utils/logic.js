export const shuffleArray = (array) => {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
};

export function parseItem(itemStr) {
  const [attributes, label] = itemStr.split(' -> ');
  const parts = attributes.split(/[|,]/).map(p => p.trim());
  const obj = { label };
  parts.forEach(p => {
    const [key, val] = p.split('=');
    if (key && val) obj[key.trim()] = val.trim();
  });
  return obj;
}

export function getPossibleLabels(turns) {
  const lastTurnText = turns[turns.length - 1];
  const labelMatch = lastTurnText?.match(/Use only labels from: (.*)\./);
  return labelMatch ? labelMatch[1].split(', ') : ['accept', 'reject'];
}

const RULE_DESCRIPTIONS = {
  accept_diagonal_pull: 'Accept when |r1-r2| is at least 4.',
  accept_tone_bright_or_r2_negative: 'Accept when tone is bright or r2 is negative.',
  north_shape_pointed: 'North when the shape is triangle or star.',
  north_sum_nonnegative: 'North when r1+r2 is non-negative.',
  amber_cobalt_jade_sum_band: 'Use the sum band over r1+r2.',
  amber_cobalt_jade_shape_tone: 'Use the shape/tone router.',
  ember_frost_glade_noir_quadrant: 'Use the quadrant rule over the signs of r1 and r2.',
  ember_frost_glade_noir_surface: 'Use the shape/tone surface router.',
};

const RULE_PAIR_BY_MEMBERS = {
  'accept_diagonal_pull|accept_tone_bright_or_r2_negative': {
    source: 'accept_tone_bright_or_r2_negative',
    target: 'accept_diagonal_pull',
  },
  'amber_cobalt_jade_shape_tone|amber_cobalt_jade_sum_band': {
    source: 'amber_cobalt_jade_sum_band',
    target: 'amber_cobalt_jade_shape_tone',
  },
  'ember_frost_glade_noir_quadrant|ember_frost_glade_noir_surface': {
    source: 'ember_frost_glade_noir_quadrant',
    target: 'ember_frost_glade_noir_surface',
  },
  'north_shape_pointed|north_sum_nonnegative': {
    source: 'north_shape_pointed',
    target: 'north_sum_nonnegative',
  },
};

function getTurnNarrative(turnText) {
  return turnText?.split('\n\n')[1]?.split('\n')[0] ?? '';
}

function extractTurnSectionItems(turnText, sectionHeader, { stripUnknownLabel = false } = {}) {
  const sectionText = turnText?.split(sectionHeader)[1];
  if (!sectionText) return [];

  return sectionText
    .split('\n')
    .filter(line => line.includes('->'))
    .map(line => line.replace(/^\d+\.\s+/, ''))
    .map(line => stripUnknownLabel ? line.replace(' -> ?', '') : line)
    .map(parseItem);
}

function humanizeRuleId(ruleId) {
  return ruleId
    ?.split('_')
    .join(' ')
    .replace(/\b\w/g, char => char.toUpperCase()) ?? '';
}

export function getRuleDescription(ruleId) {
  if (!ruleId) return '';
  return RULE_DESCRIPTIONS[ruleId] ?? humanizeRuleId(ruleId);
}

function getEpisodeRulePair(episode) {
  const probeMetadata = episode?.scoring?.probe_metadata ?? [];
  const routeRuleIds = [...new Set(
    probeMetadata
      .map(metadata => metadata.route_metadata?.route_rule_id || metadata.active_rule_id)
      .filter(Boolean)
  )];

  if (routeRuleIds.length === 2) {
    const pairKey = [...routeRuleIds].sort().join('|');
    if (RULE_PAIR_BY_MEMBERS[pairKey]) return RULE_PAIR_BY_MEMBERS[pairKey];
  }

  const uniqueActiveRuleIds = [...new Set(probeMetadata.map(metadata => metadata.active_rule_id).filter(Boolean))];
  if (uniqueActiveRuleIds.length === 1) {
    const activeRuleId = uniqueActiveRuleIds[0];
    const matchingPair = Object.values(RULE_PAIR_BY_MEMBERS).find(pair => pair.target === activeRuleId);
    if (matchingPair) return matchingPair;
  }

  return null;
}

function getRouteRuleMap(episode, routeKey) {
  const entries = (episode?.scoring?.probe_metadata ?? [])
    .map(metadata => {
      const routeValue = metadata.route_metadata?.[routeKey];
      const routeRuleId = metadata.route_metadata?.route_rule_id || metadata.active_rule_id;
      return routeValue && routeRuleId ? [routeValue, routeRuleId] : null;
    })
    .filter(Boolean);

  return Object.fromEntries(entries);
}

function isShiftedEvidenceTurn(episode, turnIndex, evidenceTurns) {
  const suiteTaskId = episode?.analysis?.suite_task_id;

  if (suiteTaskId === 'latent_rule_update') {
    return turnIndex >= 1;
  }

  if (suiteTaskId === 'explicit_rule_update') {
    const shiftTurnIndex = evidenceTurns.findIndex((turnText, index) => (
      index > 0 && /changed|new rule|replacement|no longer applies|rule refresh/i.test(getTurnNarrative(turnText))
    ));
    return turnIndex >= (shiftTurnIndex >= 0 ? shiftTurnIndex : Math.max(evidenceTurns.length - 1, 1));
  }

  return false;
}

function getExampleRuleId(episode, example, turnIndex, evidenceTurns) {
  const suiteTaskId = episode?.analysis?.suite_task_id;
  const rulePair = getEpisodeRulePair(episode);

  if (suiteTaskId === 'context_binding') {
    const contextRuleMap = getRouteRuleMap(episode, 'context');
    return contextRuleMap[example.context] ?? null;
  }

  if (suiteTaskId === 'trial_cued_switch') {
    const cueRuleMap = getRouteRuleMap(episode, 'cue');
    if (example.cue) return cueRuleMap[example.cue] ?? null;
    return rulePair?.source ?? null;
  }

  if (suiteTaskId === 'explicit_rule_update' || suiteTaskId === 'latent_rule_update') {
    return isShiftedEvidenceTurn(episode, turnIndex, evidenceTurns) ? rulePair?.target ?? null : rulePair?.source ?? null;
  }

  return rulePair?.target ?? rulePair?.source ?? null;
}

export function getEpisodeExampleGroups(episode) {
  const turns = episode?.inference?.turns ?? [];
  const evidenceTurns = turns.filter(turnText => turnText.includes('Examples:\n'));

  return evidenceTurns
    .map((turnText, index) => {
      const examples = extractTurnSectionItems(turnText, 'Examples:\n');
      if (!examples.length) return null;

      return {
        turnIndex: index,
        title: `Turn ${index + 1}`,
        narrative: getTurnNarrative(turnText),
        examples: examples.map(example => {
          const ruleId = getExampleRuleId(episode, example, index, evidenceTurns);
          return {
            data: example,
            ruleId,
            ruleDescription: getRuleDescription(ruleId),
          };
        }),
      };
    })
    .filter(Boolean);
}

export function getEpisodeProbes(episode) {
  const turns = episode?.inference?.turns ?? [];
  const finalTurnText = turns[turns.length - 1];
  const probes = extractTurnSectionItems(finalTurnText, 'Probes:\n', { stripUnknownLabel: true });
  const probeMetadata = episode?.scoring?.probe_metadata ?? [];

  return probes.map((probe, index) => {
    const metadata = probeMetadata[index];
    const ruleId = metadata?.route_metadata?.route_rule_id || metadata?.active_rule_id || null;

    return {
      data: probe,
      ruleId,
      ruleDescription: getRuleDescription(ruleId),
    };
  });
}

export function getLabelStyle(label) {
  const l = label?.toLowerCase();
  
  if (['accept', 'valid', 'north', 'anchor', 'jade', 'glade'].includes(l)) {
    return 'bg-green-500 text-white border-green-400';
  }
  if (['reject', 'invalid', 'south', 'pull'].includes(l)) {
    return 'bg-red-500 text-white border-red-400';
  }
  if (['amber', 'ember'].includes(l)) {
    return 'bg-orange-500 text-white border-orange-400';
  }
  if (['cobalt', 'frost'].includes(l)) {
    return 'bg-blue-500 text-white border-blue-400';
  }
  if (['noir'].includes(l)) {
    return 'bg-zinc-800 text-white border-zinc-700';
  }
  
  return 'bg-zinc-500 text-white border-zinc-400';
}

export function getProbeCount(episode) {
  return episode?.inference?.response_spec?.probe_count ?? 0;
}

export function getTotalProbeCount(episodes) {
  return episodes.reduce((total, episode) => total + getProbeCount(episode), 0);
}

export function getProbeOffset(episodes, episodeIndex) {
  return episodes.slice(0, Math.max(episodeIndex, 0)).reduce((total, episode) => total + getProbeCount(episode), 0);
}
