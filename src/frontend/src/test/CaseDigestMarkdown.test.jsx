import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CaseFullTextMarkdown } from '../components/CaseDigestMarkdown';

describe('CaseFullTextMarkdown', () => {
    it('renders GFM pipe tables as a table element', () => {
        const md = ['| Col A | Col B |', '| --- | --- |', '| 1 | 2 |'].join('\n');
        render(<CaseFullTextMarkdown content={md} onCaseClick={() => {}} />);
        expect(screen.getByRole('table')).toBeTruthy();
        expect(screen.getByRole('columnheader', { name: /Col A/i })).toBeTruthy();
    });
});
