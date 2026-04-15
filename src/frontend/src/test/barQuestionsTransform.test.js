import { describe, it, expect } from 'vitest';
import { buildBalancedQuestions } from '../utils/barQuestionsTransform';

describe('buildBalancedQuestions', () => {
  it('normalizes from sub_topic so combined paper subject does not mis-bucket', () => {
    const data = [
      {
        id: 1,
        year: 2024,
        subject: 'Commercial and Taxation Laws',
        sub_topic: 'Taxation',
        text: 'Tax Q',
        answer: 'A',
      },
      {
        id: 2,
        year: 2024,
        subject: 'Commercial and Taxation Laws',
        sub_topic: 'Commercial Law',
        text: 'Comm Q',
        answer: 'A',
      },
    ];
    const out = buildBalancedQuestions(data);
    const tax = out.find((q) => q.id === 1);
    const comm = out.find((q) => q.id === 2);
    expect(tax.subject).toBe('Taxation Law');
    expect(comm.subject).toBe('Commercial Law');
  });
});
