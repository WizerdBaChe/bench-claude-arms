from itertools import combinations
from math import comb
print("Mann-Whitney U (two-sided) smallest ATTAINABLE p, equal group sizes:")
for n in range(2, 7):
    total = comb(2*n, n)
    print(f"  n1=n2={n}: arrangements={total:4d}  min two-sided p = 2/{total} = {2/total:.4f}"
          + ("   <- p<0.05 IMPOSSIBLE" if 2/total > 0.05 else "   <- p<0.05 reachable"))
