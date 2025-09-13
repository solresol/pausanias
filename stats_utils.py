import numpy as np
from scipy.stats import fisher_exact, chi2

def compute_p_q_values(pos_counts, neg_counts, total_pos, total_neg):
    """Compute p-values and Benjamini-Hochberg corrected q-values."""
    p_values = []
    for a, b in zip(pos_counts, neg_counts):
        table = np.array([[a, total_pos - a], [b, total_neg - b]], dtype=float)
        if (table < 5).any():
            _, p = fisher_exact(table)
        else:
            expected = np.outer(table.sum(axis=1), table.sum(axis=0)) / table.sum()
            mask = table > 0
            g2 = 2.0 * np.sum(table[mask] * np.log(table[mask] / expected[mask]))
            p = chi2.sf(g2, 1)
        p_values.append(p)
    p_values = np.array(p_values)
    n = len(p_values)
    order = np.argsort(p_values)
    ranked = p_values[order]
    q = np.empty(n)
    prev = 1.0
    for i in range(n - 1, -1, -1):
        rank = i + 1
        val = ranked[i] * n / rank
        prev = min(prev, val)
        q[i] = prev
    q_values = np.empty(n)
    q_values[order] = q
    return p_values, q_values
