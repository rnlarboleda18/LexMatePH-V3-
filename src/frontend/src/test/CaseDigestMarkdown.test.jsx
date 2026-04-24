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

    it('renders GFM footnote markup (ref + section)', () => {
        const md = ['Hello[^1].', '', '[^1]: First footnote.'].join('\n');
        const { container } = render(<CaseFullTextMarkdown content={md} onCaseClick={() => {}} />);
        expect(container.querySelector('a[data-footnote-ref]')).toBeTruthy();
        expect(container.querySelector('section[data-footnotes]')).toBeTruthy();
    });

    it('centers up to eight SC caption blocks then left-aligns the rest', () => {
        const lines = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I'];
        const md = lines.map((l) => `**${l}**`).join('\n\n');
        const { container } = render(<CaseFullTextMarkdown content={md} onCaseClick={() => {}} />);
        const blocks = container.querySelectorAll('div.mb-4');
        expect(blocks).toHaveLength(9);
        for (let i = 0; i < 8; i += 1) {
            expect(blocks[i].className).toMatch(/!text-center/);
        }
        expect(blocks[8].className).toMatch(/text-left/);
        expect(blocks[8].className).not.toMatch(/!text-center/);
    });

    it('centers standalone Decision as the seventh line (long party caption)', () => {
        const md = ['**A**', '**B**', '**C**', '**D**', '**E**', '**F**', '**Decision**', '**HERNANDO, J.:**'].join(
            '\n\n'
        );
        const { container } = render(<CaseFullTextMarkdown content={md} onCaseClick={() => {}} />);
        const blocks = container.querySelectorAll('div.mb-4');
        expect(blocks[6].className).toMatch(/!text-center/);
        expect(blocks[7].className).toMatch(/text-left/);
    });

    it('left-aligns ponente line and all content after (no more centered "body" lines)', () => {
        const md = ['**A**', '**B**', '**C**', '**HERNANDO, J.:**', '**Next paragraph**'].join('\n\n');
        const { container } = render(<CaseFullTextMarkdown content={md} onCaseClick={() => {}} />);
        const blocks = container.querySelectorAll('div.mb-4');
        expect(blocks[0].className).toMatch(/!text-center/);
        expect(blocks[1].className).toMatch(/!text-center/);
        expect(blocks[2].className).toMatch(/!text-center/);
        expect(blocks[3].className).toMatch(/text-left/);
        expect(blocks[3].className).not.toMatch(/!text-center/);
        expect(blocks[4].className).toMatch(/text-left/);
    });

    it('centers SC caption when Decision is a ### heading (h3) not a paragraph', () => {
        const md = ['**FIRST**', '**G.R.**', '**CAPTION**', '### Decision', '**HERNANDO, J.:**', '**Rest**'].join(
            '\n\n'
        );
        const { container } = render(<CaseFullTextMarkdown content={md} onCaseClick={() => {}} />);
        const pBlocks = container.querySelectorAll('div.mb-4');
        const h3 = container.querySelector('h3');
        expect(pBlocks).toHaveLength(5);
        expect(pBlocks[0].className).toMatch(/!text-center/);
        expect(pBlocks[1].className).toMatch(/!text-center/);
        expect(pBlocks[2].className).toMatch(/!text-center/);
        expect(h3?.className).toMatch(/!text-center/);
        expect(pBlocks[3].className).toMatch(/text-left/);
        expect(pBlocks[3].className).not.toMatch(/!text-center/);
        expect(pBlocks[4].className).toMatch(/text-left/);
    });
});
