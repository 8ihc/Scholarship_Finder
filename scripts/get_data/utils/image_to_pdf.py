from pathlib import Path
from typing import List, Optional
from PIL import Image
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


SUPPORTED_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif'}


def _is_image_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTS


def convert_single_image_to_pdf(input_path: Path, output_path: Optional[Path] = None, quality: int = 95) -> Path:
    """Convert one image to a PDF and return the output Path.

    - Flattens alpha/transparency to white background.
    - Ensures the saved PDF uses RGB mode.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    if output_path is None:
        output_path = input_path.with_suffix('.pdf')
    else:
        output_path = Path(output_path)

    with Image.open(input_path) as im:
        # Convert palette or RGBA to RGB (flatten transparency)
        if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
            bg = Image.new('RGB', im.size, (255, 255, 255))
            try:
                alpha = im.convert('RGBA').split()[-1]
                bg.paste(im.convert('RGBA'), mask=alpha)
            except Exception:
                bg.paste(im.convert('RGB'))
            img_rgb = bg
        else:
            img_rgb = im.convert('RGB')

        # Ensure parent dir exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as PDF
        img_rgb.save(output_path, 'PDF', quality=quality)

    logging.info(f"Saved PDF: {output_path}")
    return output_path


def convert_many_images_to_pdfs(inputs: List[Path], output_dir: Optional[Path] = None, overwrite: bool = False) -> List[Path]:
    """Convert multiple image files to separate PDFs. Returns list of output paths."""
    out_paths = []
    for p in inputs:
        p = Path(p)
        if not _is_image_file(p):
            logging.debug(f"Skipping non-image: {p}")
            continue

        if output_dir:
            out = Path(output_dir) / (p.stem + '.pdf')
        else:
            out = p.with_suffix('.pdf')

        if out.exists() and not overwrite:
            logging.info(f"Output exists and overwrite is False, skipping: {out}")
            out_paths.append(out)
            continue

        out_paths.append(convert_single_image_to_pdf(p, out))

    return out_paths


def merge_images_to_pdf(inputs: List[Path], output_path: Path, overwrite: bool = False, quality: int = 95) -> Path:
    """Merge multiple images into a single multi-page PDF.

    The order of pages follows the order of `inputs`.
    """
    inputs = [Path(p) for p in inputs if _is_image_file(Path(p))]
    if not inputs:
        raise ValueError('No image inputs to merge')

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not overwrite:
        logging.info(f"Merged output exists and overwrite is False, skipping: {output_path}")
        return output_path

    # Open images and convert to RGB
    pil_images = []
    for p in inputs:
        im = Image.open(p)
        if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
            bg = Image.new('RGB', im.size, (255, 255, 255))
            try:
                alpha = im.convert('RGBA').split()[-1]
                bg.paste(im.convert('RGBA'), mask=alpha)
            except Exception:
                bg.paste(im.convert('RGB'))
            pil_images.append(bg)
        else:
            pil_images.append(im.convert('RGB'))

    first, rest = pil_images[0], pil_images[1:]
    first.save(output_path, 'PDF', save_all=True, append_images=rest, quality=quality)
    logging.info(f"Saved merged PDF: {output_path}")
    return output_path


def _collect_image_files_from_path(path: Path) -> List[Path]:
    path = Path(path)
    if path.is_dir():
        return sorted([p for p in path.iterdir() if p.suffix.lower() in SUPPORTED_EXTS])
    if path.is_file() and _is_image_file(path):
        return [path]
    return []


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Convert images to PDF(s).')
    parser.add_argument('inputs', nargs='+', help='Image file(s) or directories')
    parser.add_argument('--output-dir', help='Directory to write individual PDFs (if omitted, write next to images)')
    parser.add_argument('--merge', action='store_true', help='Merge all input images (in order) into one PDF')
    parser.add_argument('--output', help='Output file for merged PDF (required when --merge is used)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing outputs')
    parser.add_argument('--quality', type=int, default=95, help='PDF quality (Pillow option)')
    args = parser.parse_args(argv)

    # Collect image files
    collected: List[Path] = []
    for inp in args.inputs:
        collected.extend(_collect_image_files_from_path(Path(inp)))

    if not collected:
        logging.error('No image files found in inputs')
        return 2

    if args.merge:
        if not args.output:
            logging.error('--merge requires --output to be specified')
            return 2
        try:
            merge_images_to_pdf(collected, Path(args.output), overwrite=args.overwrite, quality=args.quality)
        except Exception as e:
            logging.error(f'Merge failed: {e}')
            return 1
        return 0

    # Convert each image to an individual PDF
    out_dir = Path(args.output_dir) if args.output_dir else None
    try:
        convert_many_images_to_pdfs(collected, output_dir=out_dir, overwrite=args.overwrite)
    except Exception as e:
        logging.error(f'Conversion failed: {e}')
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
