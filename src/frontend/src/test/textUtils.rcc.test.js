import { describe, it, expect } from 'vitest';
import { fixRccStructuralHeadingGlue } from '../utils/textUtils';

describe('fixRccStructuralHeadingGlue', () => {
    it('inserts space in PROVISIONSDEFINITIONS', () => {
        expect(fixRccStructuralHeadingGlue('GENERAL PROVISIONSDEFINITIONS AND CORPORATE')).toContain(
            'PROVISIONS DEFINITIONS',
        );
    });

    it('fixes Title I style Provisionsdefinitions run-on', () => {
        expect(fixRccStructuralHeadingGlue('General Provisionsdefinitions and Classifications')).toContain(
            'Provisions and Definitions',
        );
    });
});
