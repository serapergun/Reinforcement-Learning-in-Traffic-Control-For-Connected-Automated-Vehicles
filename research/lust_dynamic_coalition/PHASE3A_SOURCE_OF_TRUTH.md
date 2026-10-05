# Phase3A manuscript source of truth

This file freezes the verified numerical claims used by `PHASE3A_FULL_MANUSCRIPT.md`. Values originate from the exact 512-coalition seed-9001 AM-peak game and the pre-specified five-seed critical-panel robustness analysis.

## Exact game (AM peak, seed 9001)

- Native baseline: queue 35.8; waiting 605.6555555556; arrivals 12081; CO2 118.2892713625.
- Grand coalition: v(N)=0.007595492418404752; queue gain 1.644941%; waiting gain 0.624667%; CO2 gain 0.367000%; arrival change -0.513203%; 54 interventions.
- Exact-game best: A3+A4+A7+A8+A9; v=0.0455069834356523; queue gain 6.098696%; waiting gain 7.956484%; CO2 gain 0.499908%; arrival change -0.471815%; 26 interventions.
- Best/grand value ratio: approximately 5.99.
- Strict no-throughput-loss best: A1+A3+A4; v=0.037443; queue gain 4.85723%; waiting gain 7.11626%; arrival change +0.07450%; CO2 gain -0.50884%.

## Allocation and stability

- Shapley: A1 0.0261654417; A2 -0.0318476519; A3 0.0205489408; A4 0.0030474996; A5 -0.0110301661; A6 -0.0016659026; A7 0.0008013258; A8 -0.0009275832; A9 0.0025035884.
- Core: empty.
- Least-core epsilon: 0.022705376418353573.
- Unique least-core/nucleolus: A1 0.0245135229; A2 -0.0295123202; A3 0.0170136493; A4 0.0062444165; A5 -0.0070448957; A6 -0.0033599663; A7 0.0021153563; A8 -0.0127501258; A9 0.0103758555.
- Binding constraints plus efficiency allocation rank: 9.
- Shapley maximum excess: 0.0328688503.
- Nucleolus maximum excess: 0.0227053764.
- Maximum-excess reduction: approximately 30.9%.
- Shapley IR failures: A4, A5. Nucleolus IR failures: A3, A4, A5.

## Five-seed critical-panel robustness

- A1+A3+A4: v=0.0439613 +/- 0.0123570; positive 5/5; queue gain 5.521679% +/- 1.609072; waiting gain 8.663893% +/- 2.147527; arrival change +0.257604% +/- 0.351269; mean CO2 gain -0.869459%.
- A3+A4+A7+A8+A9: v=0.0385123 +/- 0.0061301; positive 5/5.
- Grand coalition: v=0.00905842 +/- 0.0100663; positive 4/5.

Paired A1+A3+A4 vs grand: mean advantage 0.0349028709858; 95% CI [0.0243206442,0.0454850978]; Cohen's dz=4.0953; paired t p=0.0007894; exact two-sided Wilcoxon p=0.0625; wins 5/5.

Paired A3+A4+A7+A8+A9 vs grand: mean advantage 0.02945390391; 95% CI [0.01285138968,0.04605641814]; dz=2.20279; paired t p=0.0078977; Wilcoxon p=0.0625; wins 5/5.

## Claim boundaries

- "Exact" and "global best/optimum" apply only to the complete seed-9001 AM-peak 512-coalition game.
- Held-out seeds 9002-9005 evaluate a targeted critical panel, not all 512 coalitions.
- Multi-seed robustness claims therefore concern tested focal coalitions versus the grand coalition.
- Shapley and nucleolus are normalized performance-credit/participation-value allocations, not monetary payments.
- The nucleolus reduces worst-case excess but does not make the game core-stable.
