"""Download stabilityai/sd-turbo into a local folder for CPU inference."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Download SD-Turbo for local CPU generation")
    parser.add_argument(
        "--out",
        default="storage/models/sd-turbo",
        help="Local directory for model files",
    )
    parser.add_argument(
        "--repo",
        default="stabilityai/sd-turbo",
        help="Hugging Face repo id",
    )
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import snapshot_download

    print(f"Downloading {args.repo} -> {out.resolve()}")
    snapshot_download(
        repo_id=args.repo,
        local_dir=str(out),
    )
    print("Done. Set IMAGE_MODEL=sd-turbo and IMAGE_MODEL_PATH=" + str(out).replace("\\", "/"))


if __name__ == "__main__":
    main()
