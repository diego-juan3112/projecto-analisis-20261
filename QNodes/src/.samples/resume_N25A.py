import numpy as np
import os
import time
import sys
import argparse

# Resume generator: continues writing remaining rows to existing CSV using same seed
# It advances RNG by re-simulating previous rows (without writing) to keep RNG state identical.

def count_lines(filepath):
    # Count lines efficiently by reading in chunks
    cnt = 0
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.raw.read(1024*1024), b''):
            cnt += chunk.count(b'\n')
    return cnt


def advance_rng_for_rows(rng, N, rows, batch=200000):
    # Simulate binary states and consume accompanying randoms (scales) to advance RNG state
    remaining = rows
    while remaining > 0:
        bs = min(batch, remaining)
        states = rng.integers(0, 2, size=(bs, N), dtype=np.int8)
        counts = states.sum(axis=1)
        nz_mask = counts > 0
        nz_count = int(nz_mask.sum())
        if nz_count > 0:
            # consume nz_count random floats
            _ = rng.random(size=nz_count)
        remaining -= bs


def resume(N: int = 25, seed: int = 42, out_path: str = 'QNodes/src/.samples/N25A.csv', batch_size: int = 200000, start_rows: int = None):
    num_states = 2 ** N
    if not os.path.exists(out_path):
        print('ERROR: output file does not exist; cannot resume')
        return None

    if start_rows is None:
        print('Counting existing rows in file (this may take a while)...')
        start_rows = count_lines(out_path)
    print(f'Existing rows: {start_rows}')

    if start_rows >= num_states:
        print('File already complete.')
        return None

    rng = np.random.default_rng(seed)

    # Advance RNG state to match previous generation
    t0 = time.time()
    print(f'Advancing RNG to skip first {start_rows} rows...')
    advance_rng_for_rows(rng, N, start_rows, batch=batch_size)
    print(f'RNG advanced in {time.time()-t0:.2f}s')

    total_nonzero = 0
    max_row_sum = 0.0
    written_rows = start_rows

    t_start = time.time()
    for start in range(start_rows, num_states, batch_size):
        bs = min(batch_size, num_states - start)
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
        with open(out_path, 'ab') as f:
            np.savetxt(f, probs, delimiter=',', fmt='%.10f')

        written_rows += bs
        if written_rows % (batch_size * 10) == 0 or written_rows == num_states:
            elapsed = time.time() - t_start
            percent = written_rows / num_states * 100
            print(f'Written {written_rows}/{num_states} rows ({percent:.2f}%) in {elapsed:.1f}s')

    total_time = time.time() - t_start
    file_size = os.path.getsize(out_path)

    result = {
        'out_path': out_path,
        'shape': (num_states, N),
        'nonzero_rows': total_nonzero,
        'max_row_sum': max_row_sum,
        'file_size': file_size,
        'total_time': total_time,
    }

    print('\nResume finished:')
    print(result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--N', type=int, default=25)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--out', type=str, default=None)
    parser.add_argument('--batch', type=int, default=200000)
    parser.add_argument('--start', type=int, default=None, help='If known, skip counting and use this start row')
    args = parser.parse_args()

    out_path = args.out if args.out is not None else f'QNodes/src/.samples/N{args.N}A.csv'

    try:
        res = resume(N=args.N, seed=args.seed, out_path=out_path, batch_size=args.batch, start_rows=args.start)
        if res is None:
            sys.exit(0)
        # basic checks
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

        print('\nResume completed successfully')
    except Exception as e:
        print('\nError during resume:', str(e))
        raise
