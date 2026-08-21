tc     = [18, 23, 39, 0]          # test-case directories built
y1b    = [1203354, 1141359, 1654454, 934104]
cost   = [18.34, 15.52, 18.26, 13.98]
runs   = ["C3-01","C3-02","C3-03","C3-04"]
def ranks(v):
    s = sorted(range(len(v)), key=lambda i: v[i])
    r = [0]*len(v)
    for pos, i in enumerate(s): r[i] = pos + 1
    return r
def spearman(a, b):
    ra, rb = ranks(a), ranks(b)
    n = len(a)
    d2 = sum((x-y)**2 for x, y in zip(ra, rb))
    return 1 - 6*d2/(n*(n*n-1))
print(f"{'run':8}{'test dirs':>11}{'Y1b':>12}{'cost':>9}")
for i,r in enumerate(runs):
    print(f"{r:8}{tc[i]:11}{y1b[i]:12,}{cost[i]:9.2f}")
print(f"\nSpearman rho(test dirs, Y1b)  = {spearman(tc,y1b):+.2f}")
print(f"Spearman rho(test dirs, cost) = {spearman(tc,cost):+.2f}")
print("\nn=4: NOT testable (min attainable p for Spearman at n=4 is 0.0833).")
print("Reported as a descriptive pattern only. The run that built NO test")
print("scaffolding (C3-04) was also the cheapest and lightest of the four,")
print("which is consistent with scaffolding driving the cost -- but four")
print("points cannot establish that.")
