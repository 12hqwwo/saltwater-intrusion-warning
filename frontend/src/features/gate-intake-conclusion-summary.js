import { node } from '../shared/ui.js';

export function renderGateIntakeConclusion(conclusion, result) {
  conclusion.dataset.status = result.status;
  conclusion.replaceChildren(node('h4', result.statusTitle), node('p', result.summaryReason));
}
