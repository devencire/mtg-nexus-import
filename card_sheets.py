import math
from pathlib import Path
from typing import Sequence

from PIL import Image

from image_download import download_images
from parse_xml import CardData, separate_cards


def _get_image_urls(cards: Sequence[CardData]) -> list[str]:
    image_urls: list[str] = []
    for card in cards:
        image_url = card.image_url
        if not image_url:
            raise ValueError("One or more cards do not have an image URL.")
        image_urls.append(image_url)
    return image_urls


def get_indexed_output_path(base_path: str | Path, index: int) -> Path:
    """
    Generate an indexed file path for multi-sheet outputs.
    If base_path contains '{index}' or '{i}', format it.
    Otherwise, append '_{index}' before the file suffix.
    E.g. 'card_sheet.jpg' with index 1 -> 'card_sheet_1.jpg'
    """
    path_str = str(base_path)
    if '{index}' in path_str or '{i}' in path_str:
        return Path(path_str.format(index=index, i=index))

    p = Path(base_path)
    return p.parent / f"{p.stem}_{index}{p.suffix}"


def create_card_sheet(
    images: Sequence[Image.Image],
    cols: int = 10,
    rows: int | None = None,
    card_size: tuple[int, int] | None = None,
    scale: float = 1.0,
    background_color: tuple[int, int, int] = (0, 0, 0),
) -> Image.Image:
    """
    Tile a sequence of PIL Images into a single grid (tile map) for Tabletop Simulator.

    Tabletop Simulator custom decks use a grid of cards (typically up to 10 columns by 7 rows).
    """
    if not images:
        raise ValueError("Cannot create a card sheet from an empty list of images.")

    if cols <= 0:
        raise ValueError("Number of columns must be positive.")

    total_images = len(images)
    computed_rows = math.ceil(total_images / cols)
    actual_rows = rows if rows is not None else computed_rows
    if actual_rows < computed_rows:
        raise ValueError(
            f"Specified rows ({actual_rows}) cannot fit {total_images} images with {cols} columns (requires at least {computed_rows} rows)."
        )

    if scale <= 0:
        raise ValueError("Scale multiplier must be positive.")

    # Determine uniform card size (width, height)
    base_card_size = card_size if card_size is not None else images[0].size
    if scale != 1.0:
        target_card_size = (
            int(round(base_card_size[0] * scale)),
            int(round(base_card_size[1] * scale)),
        )
    else:
        target_card_size = base_card_size

    sheet_width = cols * target_card_size[0]
    sheet_height = actual_rows * target_card_size[1]

    sheet = Image.new('RGB', (sheet_width, sheet_height), color=background_color)

    for idx, img in enumerate(images):
        col_idx = idx % cols
        row_idx = idx // cols
        x = col_idx * target_card_size[0]
        y = row_idx * target_card_size[1]

        if img.size != target_card_size:
            resized_img = img.resize(target_card_size, Image.Resampling.LANCZOS)
            sheet.paste(resized_img, (x, y))
        else:
            sheet.paste(img, (x, y))

    return sheet


def create_card_sheets(
    images: Sequence[Image.Image],
    cols: int = 10,
    rows: int | None = None,
    max_rows_per_sheet: int = 7,
    card_size: tuple[int, int] | None = None,
    scale: float = 1.0,
    background_color: tuple[int, int, int] = (0, 0, 0),
) -> list[Image.Image]:
    """
    Tile a sequence of PIL Images into multiple grid sheets (tile maps) for Tabletop Simulator,
    splitting into multiple sheets when the number of images exceeds the capacity of a single sheet
    (by default max 70 cards: 10 columns by 7 rows).
    """
    if not images:
        raise ValueError("Cannot create a card sheet from an empty list of images.")

    if cols <= 0:
        raise ValueError("Number of columns must be positive.")

    rows_per_sheet = rows if rows is not None else max_rows_per_sheet
    if rows_per_sheet <= 0:
        raise ValueError("Rows per sheet must be positive.")

    sheet_capacity = cols * rows_per_sheet
    sheets: list[Image.Image] = []

    for i in range(0, len(images), sheet_capacity):
        chunk = images[i : i + sheet_capacity]
        sheet = create_card_sheet(
            images=chunk,
            cols=cols,
            rows=rows,
            card_size=card_size,
            scale=scale,
            background_color=background_color,
        )
        sheets.append(sheet)

    return sheets


def download_and_create_card_sheet(
    cards: Sequence[CardData],
    output_path: str | Path = 'output_data/card_sheet.jpg',
    backs_output_path: str | Path | None = 'output_data/card_sheet_double_sided_backs.jpg',
    token_output_path: str | Path | None = 'output_data/card_sheet_tokens.jpg',
    base_url: str = 'https://www.mtgnexus.com',
    cols: int = 10,
    rows: int | None = None,
    max_rows_per_sheet: int = 7,
    max_workers: int = 10,
    card_size: tuple[int, int] | None = None,
    scale: float = 1.0,
    quality: int = 95,
    subsampling: int | str = 0,
    optimize: bool = True,
    background_color: tuple[int, int, int] = (0, 0, 0),
) -> list[Image.Image]:
    """
    Download card images from parsed XML card data and
    produce Tabletop Simulator tile map JPEG card sheet(s).

    Splits images into multiple card sheets if they exceed the capacity of a single sheet
    (default 10 columns by 7 rows = 70 cards), saving them as card_sheet_1.jpg, card_sheet_2.jpg, etc.
    XML front faces and single-sided regular cards are included in the main card sheet.
    If XML back faces are present and backs_output_path is provided, they are saved as separate card sheet(s)
    (e.g. card_sheet_double_sided_backs_1.jpg).
    If token cards (main_type containing 'Token') are present and token_output_path is provided,
    they are saved as separate card sheet(s) (e.g. card_sheet_tokens_1.jpg).
    By default, card sheets are produced at double (2x) resolution for maximum text clarity in TTS.
    """
    token_cards: list[CardData] = []
    regular_cards: list[CardData] = []
    for card in cards:
        if card.main_type is not None and 'Token' in card.main_type:
            token_cards.append(card)
        else:
            regular_cards.append(card)

    front_cards, back_cards = separate_cards(regular_cards)
    front_urls = _get_image_urls(front_cards)
    back_urls = _get_image_urls(back_cards)
    token_urls = _get_image_urls(token_cards)

    def _process_and_save(urls: list[str], save_path: str | Path | None) -> list[Image.Image]:
        if not urls or save_path is None:
            return []
        images = download_images(urls, base_url=base_url, max_workers=max_workers)
        sheets = create_card_sheets(
            images=images,
            cols=cols,
            rows=rows,
            max_rows_per_sheet=max_rows_per_sheet,
            card_size=card_size,
            scale=scale,
            background_color=background_color,
        )
        for idx, sheet in enumerate(sheets, start=1):
            out_p = get_indexed_output_path(save_path, idx)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            sheet.save(
                out_p,
                format='JPEG',
                quality=quality,
                subsampling=subsampling,
                optimize=optimize,
            )
        return sheets

    main_sheets = _process_and_save(front_urls, output_path)
    backs_sheets = _process_and_save(back_urls, backs_output_path)
    token_sheets = _process_and_save(token_urls, token_output_path)

    return main_sheets if main_sheets else (backs_sheets if backs_sheets else token_sheets)
