import numpy as np
import os
import time
import sys
import argparse

def generate_stream(N: int = 25, seed: int = 42, out_path: str = 'QNodes/src/.samples/N25A.csv', batch_size: int = 100000):
    rng = np.random.default_rng(seed)
    num_states = 2 ** N

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    print(f'Generating N={N}, num_states={num_states}, seed={seed}, batch_size={batch_size}')
    t0 = time.time()

    total_nonzero = 0
    max_row_sum = 0.0
    written_rows = 0

    # Remove file if exists
    if os.path.exists(out_path):
        os.remove(out_path)

    for start in range(0, num_states, batch_size):
        bs = min(batch_size, num_states - start)
        # generate binary states for this batch
        states = rng.integers(0, 2, size=(bs, N), dtype=np.int8)
        counts = states.sum(axis=1)

        probs = np.zeros((bs, N), dtype=np.float32)
        nz_mask = counts > 0
        nz_count = int(nz_mask.sum())
        if nz_count > 0:
            probs[nz_mask] = states[nz_mask] / counts[nz_mask].reshape(-1, 1)
            scales = rng.random(size=nz_count)
            probs[nz_mask] = probs[nz_mask] * scales.reshape(-1, 1)
            total_nonzero += nz_count
            max_row_sum = max(max_row_sum, float(probs[nz_mask].sum(axis=1).max()))

        # append to CSV
        mode = 'ab' if written_rows > 0 else 'wb'
        with open(out_path, mode) as f:
            # write using savetxt to a bytes buffer
            np.savetxt(f, probs, delimiter=',', fmt='%.10f')

        written_rows += bs
        if written_rows % (batch_size * 10) == 0:
            elapsed = time.time() - t0
            print(f'Written {written_rows}/{num_states} rows ({written_rows/num_states*100:.2f}%) in {elapsed:.1f}s')

    total_time = time.time() - t0
    file_size = os.path.getsize(out_path)

    result = {
        'out_path': out_path,
        'shape': (num_states, N),
        'nonzero_rows': total_nonzero,
        'max_row_sum': max_row_sum,
        'file_size': file_size,
        'total_time': total_time,
    }

    print('\nGeneration finished:')
    print(result)
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--N', type=int, default=25)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--out', type=str, default=None)
    parser.add_argument('--batch', type=int, default=100000)
    args = parser.parse_args()

    out_path = args.out if args.out is not None else f'QNodes/src/.samples/N{args.N}A.csv'

    try:
        res = generate_stream(N=args.N, seed=args.seed, out_path=out_path, batch_size=args.batch)
        # checks
        expected_shape = (2 ** args.N, args.N)
        if res['shape'] != expected_shape:
            print('ERROR: shape mismatch', res['shape'])
            sys.exit(1)
        if res['nonzero_rows'] < 1000:
            print('ERROR: not enough non-zero rows', res['nonzero_rows'])
            sys.exit(2)
        if res['max_row_sum'] > 1.0 + 1e-6:
            print('ERROR: row sum exceeds 1.0', res['max_row_sum'])
            sys.exit(3)

        if res['file_size'] > 2 * 1024**3:
            print('WARNING: file size exceeds 2GB')

        print('\nGeneration completed successfully')
    except Exception as e:
        print('\nError during generation:', str(e))
        raise
