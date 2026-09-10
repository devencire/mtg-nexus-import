from collections import Counter

from card_sheets import (
    create_card_sheet,
    create_card_sheets,
    download_and_create_card_sheet,
    get_indexed_output_path,
)
from image_download import (
    download_image,
    download_images,
)
from parse_xml import (
    CardData,
    parse_cards_from_xml,
    separate_cards,
)
from tts_saved_object import (
    create_deck_saved_object,
    create_tts_saved_objects,
    save_deck_saved_object,
    separate_cube_sparks_tokens,
)

__all__ = [
    'CardData',
    'create_card_sheet',
    'create_card_sheets',
    'create_deck_saved_object',
    'create_tts_saved_objects',
    'download_and_create_card_sheet',
    'download_image',
    'download_images',
    'get_indexed_output_path',
    'parse_cards_from_xml',
    'save_deck_saved_object',
    'separate_cards',
    'separate_cube_sparks_tokens',
]

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    all_cards = parse_cards_from_xml()
    download_and_create_card_sheet(all_cards, scale=2.0)
    create_tts_saved_objects(all_cards)
