import argparse
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import config
import processor


def process_single_file(input_file: Path, bg_file: Path, output_file: Path):
    """Processes a single PDF or image file and saves the result."""
    ext = input_file.suffix.lower()
    print(f"📄 Processing: {input_file.name} ...", end=" ", flush=True)

    try:
        if ext == ".pdf":
            out_bytes, _ = processor.add_background_to_pdf(input_file, bg_file, output_path=output_file)
        elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
            out_bytes, _ = processor.add_background_to_image(input_file, bg_file, output_path=output_file)
        else:
            print(f"⚠️ Skipped (unsupported extension: {ext})")
            return False

        print(f"✅ Saved to {output_file} ({len(out_bytes) // 1024} KB)")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Invoice Logo / Background Adder CLI tool. Adds company paper design to invoices."
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to an input invoice file (PDF/Image) or a directory containing invoices."
    )
    parser.add_argument(
        "-b", "--background",
        type=str,
        default=str(config.get_background_path()),
        help=f"Path to background image or PDF (default: {config.get_background_path().name})"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (for single file) or output directory (for batch mode)."
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    bg_path = Path(args.background)

    if not bg_path.exists():
        print(f"❌ Error: Background image '{bg_path}' not found!")
        sys.exit(1)

    if not input_path.exists():
        print(f"❌ Error: Input '{input_path}' not found!")
        sys.exit(1)

    print("=" * 60)
    print(" ASC Invoice Background / Letterhead Adder")
    print(f" Background: {bg_path.resolve()}")
    print("=" * 60)

    if input_path.is_file():
        # Single file
        if args.output:
            output_file = Path(args.output)
        else:
            output_file = input_path.parent / f"{input_path.stem}_branded.pdf"

        success = process_single_file(input_path, bg_path, output_file)
        sys.exit(0 if success else 1)

    elif input_path.is_dir():
        # Directory batch mode
        out_dir = Path(args.output) if args.output else input_path / "branded_output"
        out_dir.mkdir(parents=True, exist_ok=True)

        files = [
            f for f in input_path.iterdir()
            if f.is_file() and f.suffix.lower() in [".pdf", ".jpg", ".jpeg", ".png", ".webp"]
            and not f.name.endswith("_branded.pdf")
        ]

        if not files:
            print(f"⚠️ No PDF or image files found in {input_path}")
            sys.exit(0)

        print(f"Found {len(files)} file(s) to process in {input_path} -> Outputting to {out_dir}\n")
        successful = 0
        for f in files:
            target_out = out_dir / f"{f.stem}_branded.pdf"
            if process_single_file(f, bg_path, target_out):
                successful += 1

        print(f"\n🎉 Finished: {successful}/{len(files)} files processed successfully.")
        sys.exit(0 if successful == len(files) else 1)


if __name__ == "__main__":
    main()
