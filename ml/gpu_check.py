"""
GPU sanity check and matmul benchmark for the college-PC engine.

    backend\\.venv-ml\\Scripts\\python ml\\gpu_check.py

Prints whether PyTorch sees CUDA, the device, its memory, and square-matmul
throughput on GPU (fp32, TF32, fp16) versus CPU (fp32).
"""

from __future__ import annotations

import time

import torch


def bench(device: str, n: int, dtype: torch.dtype, reps: int) -> tuple[float, float]:
    """Return (seconds per matmul, TFLOP/s) for an n×n @ n×n product."""
    a = torch.randn(n, n, device=device, dtype=dtype)
    b = torch.randn(n, n, device=device, dtype=dtype)
    sync = torch.cuda.synchronize if device == "cuda" else (lambda: None)
    for _ in range(3):  # warm-up: kernel selection, caches, clocks
        a @ b
    sync()
    start = time.perf_counter()
    for _ in range(reps):
        a @ b
    sync()
    per = (time.perf_counter() - start) / reps
    return per, 2 * n**3 / per / 1e12


def main() -> None:
    print(f"torch {torch.__version__}, built for CUDA {torch.version.cuda}")
    print(f"cuda available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        raise SystemExit("PyTorch cannot see a CUDA device.")

    props = torch.cuda.get_device_properties(0)
    free, total = torch.cuda.mem_get_info(0)
    print(f"device: {props.name} (compute {props.major}.{props.minor}, {props.multi_processor_count} SMs)")
    print(f"memory: {total / 2**30:.1f} GiB total, {free / 2**30:.1f} GiB free")
    print(f"cpu threads used by torch: {torch.get_num_threads()}")
    print()

    n = 8192
    rows = []
    torch.backends.cuda.matmul.allow_tf32 = False
    rows.append(("GPU fp32", *bench("cuda", n, torch.float32, 20)))
    torch.backends.cuda.matmul.allow_tf32 = True
    rows.append(("GPU tf32", *bench("cuda", n, torch.float32, 20)))
    rows.append(("GPU fp16", *bench("cuda", n, torch.float16, 20)))
    rows.append(("CPU fp32", *bench("cpu", n, torch.float32, 3)))

    cpu_time = rows[-1][1]
    print(f"{n}x{n} matmul")
    print(f"{'':10} {'ms/op':>9} {'TFLOP/s':>8} {'vs CPU':>7}")
    for name, per, tflops in rows:
        print(f"{name:10} {per * 1e3:9.1f} {tflops:8.2f} {cpu_time / per:6.0f}x")


if __name__ == "__main__":
    main()
