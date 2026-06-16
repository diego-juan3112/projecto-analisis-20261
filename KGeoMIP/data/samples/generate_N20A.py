import numpy as np
import os
import time
import sys

# Generator for N20A.csv using logic inspired by GeoMIP/data/creation.py
# - Uses seed 42 by default (no seed found for N15B)
# - Produces shape (2**N, N) with float probabilities per-row summing <= 1
# - Saves as QNodes/src/.samples/N20A.csv

def generate_NA(N: int = 20, seed: int = 42, out_path: str = 'QNodes/src/.samples/N20A.csv'):
    rng = np.random.default_rng(seed)
    num_states = 2 ** N

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    print(f'Generating N={N}, num_states={num_states}, seed={seed}')
    t0 = time.time()

    # Step 1: generate binary states (same idea as creation.py)
    states = rng.integers(0, 2, size=(num_states, N), dtype=np.int8)

    # Step 2: convert to per-row probability vectors with sum <= 1
    # - rows with no ones remain all-zero
    # - rows with m ones become (1/m) on each one, then scaled by a random factor in (0,1]
    counts = states.sum(axis=1)
    probs = np.zeros((num_states, N), dtype=np.float32)

    nz_mask = counts > 0
    if nz_mask.any():
        # normalize ones to 1/counts
        probs[nz_mask] = states[nz_mask] / counts[nz_mask].reshape(-1, 1)
        # scale each non-zero row by a random scalar in (0,1]
        scales = rng.random(size=nz_mask.sum())
        probs[nz_mask] = probs[nz_mask] * scales.reshape(-1, 1)

    gen_time = time.time() - t0
    print(f'Generated array in {gen_time:.2f}s')

    # Save to CSV
    t1 = time.time()
    np.savetxt(out_path, probs, delimiter=',', fmt='%.10f')
    save_time = time.time() - t1
    total_time = time.time() - t0

    file_size = os.path.getsize(out_path)
    print(f'Saved {out_path} ({file_size / (1024**2):.2f} MB) in {save_time:.2f}s (total {total_time:.2f}s)')

    # Verifications
    shape = probs.shape
    nonzero_rows = int((probs.sum(axis=1) > 1e-12).sum())
    max_row_sum = float(probs.sum(axis=1).max())

    print(f'Verify: shape={shape}, nonzero_rows={nonzero_rows}, max_row_sum={max_row_sum:.12f}')

    return {
        'out_path': out_path,
        'shape': shape,
        'nonzero_rows': nonzero_rows,
        'max_row_sum': max_row_sum,
        'file_size': file_size,
        'total_time': total_time,
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate NxA CSV')
    parser.add_argument('--N', type=int, default=20, help='Number of elements')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--out', type=str, default=None, help='Output file path')
    args = parser.parse_args()

    out_path = args.out if args.out is not None else f'QNodes/src/.samples/N{args.N}A.csv'

    try:
        result = generate_NA(N=args.N, seed=args.seed, out_path=out_path)
        # checks required by user (adapt to requested N)
        expected_shape = (2 ** args.N, args.N)
        if result['shape'] != expected_shape:
            print('ERROR: shape mismatch', result['shape'])
            sys.exit(1)
        if result['nonzero_rows'] < 1000:
            print('ERROR: not enough non-zero rows', result['nonzero_rows'])
            sys.exit(2)
        if result['max_row_sum'] > 1.0 + 1e-6:
            print('ERROR: row sum exceeds 1.0', result['max_row_sum'])
            sys.exit(3)

        # file size / time guard
        if result['total_time'] > 300 or result['file_size'] > 200 * 1024 * 1024:
            print('WARNING: generation exceeded time or size thresholds')

        print('\nGeneration completed successfully:')
        print(result)
    except KeyboardInterrupt:
        print('\nOperation cancelled by user')
    except Exception as e:
        print('\nError during generation:', str(e))
        raise
