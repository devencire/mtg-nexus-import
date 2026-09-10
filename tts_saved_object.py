import json
import math
from pathlib import Path
import secrets
from typing import Any, Sequence

from card_sheets import get_indexed_output_path
from parse_xml import CardData, separate_cards


def separate_cube_sparks_tokens(
    cards: Sequence[CardData],
) -> tuple[list[CardData], list[CardData], list[CardData]]:
    """
    Separate cards into three groups:
    1. Cube cards: front faces excluding tokens.
    2. Sparks cards: double-sided card back faces.
    3. Tokens cards: token front faces.
    """
    token_cards: list[CardData] = []
    regular_cards: list[CardData] = []
    for card in cards:
        if card.main_type is not None and 'Token' in card.main_type:
            token_cards.append(card)
        else:
            regular_cards.append(card)

    front_cards, back_cards = separate_cards(regular_cards)
    return front_cards, back_cards, token_cards


def _resolve_back_url(back_url: str | Path | None) -> str:
    if back_url is None:
        default_file = Path('optimal_magic_card_back.jpg')
        if default_file.exists():
            return str(default_file.resolve())
        return "https://steamusercontent-a.akamaihd.net/ugc/14937771521355406726/A8FEBD30F1A312AD129CEDCD0637AF1BC0DDB9E2/"

    back_url_str = str(back_url)
    if back_url_str.startswith(('http://', 'https://')):
        return back_url_str

    return str(Path(back_url).resolve())


def create_deck_saved_object(
    cards: Sequence[CardData],
    sheet_base_path: str | Path = 'output_data/card_sheet.jpg',
    back_url: str | Path | None = 'optimal_magic_card_back.jpg',
    deck_name: str = "",
    cols: int = 10,
    rows: int | None = None,
    max_rows_per_sheet: int = 7,
    start_deck_id: int = 1,
) -> dict[str, Any]:
    """
    Generate a Tabletop Simulator Saved Object dictionary for a sequence of CardData cards.

    Cards are mapped to indexed card sheet textures (e.g. card_sheet_1.jpg, card_sheet_2.jpg)
    split by sheet capacity (default 10 columns by 7 rows = 70 cards).
    """
    if not cards:
        raise ValueError("Cannot create a saved object deck from an empty list of cards.")

    if cols <= 0:
        raise ValueError("Number of columns must be positive.")

    rows_per_sheet = rows if rows is not None else max_rows_per_sheet
    if rows_per_sheet <= 0:
        raise ValueError("Rows per sheet must be positive.")

    sheet_capacity = cols * rows_per_sheet
    resolved_back_url = _resolve_back_url(back_url)

    custom_deck_dict: dict[str, dict[str, Any]] = {}
    deck_ids: list[int] = []
    contained_objects: list[dict[str, Any]] = []

    sheet_idx = 1
    for offset in range(0, len(cards), sheet_capacity):
        chunk = cards[offset : offset + sheet_capacity]
        computed_rows = math.ceil(len(chunk) / cols)
        sheet_rows = rows if rows is not None else computed_rows
        face_url = str(get_indexed_output_path(sheet_base_path, sheet_idx).resolve())

        deck_id = start_deck_id + (sheet_idx - 1)
        deck_id_str = str(deck_id)

        custom_deck_entry = {
            "FaceURL": face_url,
            "BackURL": resolved_back_url,
            "NumWidth": cols,
            "NumHeight": sheet_rows,
            "BackIsHidden": True,
            "UniqueBack": False,
            "Type": 0,
        }
        custom_deck_dict[deck_id_str] = custom_deck_entry

        for card_idx_on_sheet, card in enumerate(chunk):
            card_id = deck_id * 100 + card_idx_on_sheet
            deck_ids.append(card_id)

            card_guid = secrets.token_hex(3)
            card_object = {
                "GUID": card_guid,
                "Name": "Card",
                "Transform": {
                    "posX": 0.0,
                    "posY": 1.0,
                    "posZ": 0.0,
                    "rotX": 0.0,
                    "rotY": 180.0,
                    "rotZ": 180.0,
                    "scaleX": 1.0,
                    "scaleY": 1.0,
                    "scaleZ": 1.0,
                },
                "Nickname": card.tabletop_simulator_nickname,
                "Description": card.tabletop_simulator_description,
                "GMNotes": "",
                "AltLookAngle": {"x": 0.0, "y": 0.0, "z": 0.0},
                "ColorDiffuse": {
                    "r": 0.713235259,
                    "g": 0.713235259,
                    "b": 0.713235259,
                },
                "LayoutGroupSortIndex": 0,
                "Value": 0,
                "Locked": False,
                "Grid": True,
                "Snap": True,
                "IgnoreFoW": False,
                "MeasureMovement": False,
                "DragSelectable": True,
                "Autoraise": True,
                "Sticky": True,
                "Tooltip": True,
                "GridProjection": False,
                "HideWhenFaceDown": True,
                "Hands": True,
                "CardID": card_id,
                "SidewaysCard": False,
                "CustomDeck": {deck_id_str: custom_deck_entry},
                "LuaScript": "",
                "LuaScriptState": "",
                "XmlUI": "",
                "ContainedObjects": [],
            }
            contained_objects.append(card_object)

        sheet_idx += 1

    lua_script = open("lua/booster_spawner.lua", "r")

    deck_guid = secrets.token_hex(3)
    deck_object = {
        "GUID": deck_guid,
        "Name": "Deck",
        "Transform": {
            "posX": 0.0,
            "posY": 1.0,
            "posZ": 0.0,
            "rotX": 0.0,
            "rotY": 180.0,
            "rotZ": 180.0,
            "scaleX": 1.0,
            "scaleY": 1.0,
            "scaleZ": 1.0,
        },
        "Nickname": deck_name,
        "Description": "",
        "GMNotes": "",
        "AltLookAngle": {"x": 0.0, "y": 0.0, "z": 0.0},
        "ColorDiffuse": {
            "r": 0.713235259,
            "g": 0.713235259,
            "b": 0.713235259,
        },
        "LayoutGroupSortIndex": 0,
        "Value": 0,
        "Locked": False,
        "Grid": True,
        "Snap": True,
        "IgnoreFoW": False,
        "MeasureMovement": False,
        "DragSelectable": True,
        "Autoraise": True,
        "Sticky": True,
        "Tooltip": True,
        "GridProjection": False,
        "HideWhenFaceDown": True,
        "Hands": False,
        "SidewaysCard": False,
        "DeckIDs": deck_ids,
        "CustomDeck": custom_deck_dict,
        "LuaScript": lua_script.read(),
        "LuaScriptState": "",
        "XmlUI": "",
        "ContainedObjects": contained_objects,
    }

    return {
        "SaveName": "",
        "Date": "",
        "VersionNumber": "",
        "GameMode": "",
        "GameType": "",
        "GameComplexity": "",
        "Tags": [],
        "Gravity": 0.5,
        "PlayArea": 0.5,
        "Table": "",
        "Sky": "",
        "Note": "",
        "TabStates": {},
        "LuaScript": "",
        "LuaScriptState": "",
        "XmlUI": "",
        "ObjectStates": [deck_object],
    }


def save_deck_saved_object(
    cards: Sequence[CardData],
    output_path: str | Path,
    sheet_base_path: str | Path = 'output_data/card_sheet.jpg',
    back_url: str | Path | None = 'optimal_magic_card_back.jpg',
    deck_name: str = "",
    cols: int = 10,
    rows: int | None = None,
    max_rows_per_sheet: int = 7,
    start_deck_id: int = 1,
    indent: int = 2,
) -> Path:
    """Save a Tabletop Simulator Saved Object JSON file for a given sequence of cards."""
    data = create_deck_saved_object(
        cards=cards,
        sheet_base_path=sheet_base_path,
        back_url=back_url,
        deck_name=deck_name,
        cols=cols,
        rows=rows,
        max_rows_per_sheet=max_rows_per_sheet,
        start_deck_id=start_deck_id,
    )
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent)
    return out_p


def create_tts_saved_objects(
    cards: Sequence[CardData],
    output_path: str | Path = 'output_data/cube.json',
    backs_output_path: str | Path | None = 'output_data/sparks.json',
    token_output_path: str | Path | None = 'output_data/tokens.json',
    sheet_output_path: str | Path = 'output_data/card_sheet.jpg',
    backs_sheet_output_path: str | Path | None = 'output_data/card_sheet_double_sided_backs.jpg',
    token_sheet_output_path: str | Path | None = 'output_data/card_sheet_tokens.jpg',
    back_url: str | Path | None = 'optimal_magic_card_back.jpg',
    cols: int = 10,
    rows: int | None = None,
    max_rows_per_sheet: int = 7,
    cube_deck_name: str = "Godshards Cube",
    sparks_deck_name: str = "Godshard Sparks",
    tokens_deck_name: str = "Godshards Tokens",
    indent: int = 2,
    **kwargs: Any,
) -> list[Path]:
    """
    Generate three Tabletop Simulator 'Saved Object' JSON files from a Sequence[CardData]:
    - Cube: front sides not including tokens
    - Sparks: double sided card backs
    - Tokens: token front sides
    """
    # Support alias keyword arguments if provided
    cube_json_path = kwargs.get('cube_output_path', kwargs.get('cube_json_path', output_path))
    sparks_json_path = kwargs.get('sparks_output_path', kwargs.get('sparks_json_path', backs_output_path))
    tokens_json_path = kwargs.get('tokens_output_path', kwargs.get('tokens_json_path', token_output_path))

    cube_cards, spark_cards, token_cards = separate_cube_sparks_tokens(cards)
    saved_files: list[Path] = []

    if cube_cards and cube_json_path is not None:
        saved_files.append(
            save_deck_saved_object(
                cards=cube_cards,
                output_path=cube_json_path,
                sheet_base_path=sheet_output_path,
                back_url=back_url,
                deck_name=cube_deck_name,
                cols=cols,
                rows=rows,
                max_rows_per_sheet=max_rows_per_sheet,
                indent=indent,
            )
        )

    if spark_cards and sparks_json_path is not None and backs_sheet_output_path is not None:
        saved_files.append(
            save_deck_saved_object(
                cards=spark_cards,
                output_path=sparks_json_path,
                sheet_base_path=backs_sheet_output_path,
                back_url=back_url,
                deck_name=sparks_deck_name,
                cols=cols,
                rows=rows,
                max_rows_per_sheet=max_rows_per_sheet,
                indent=indent,
            )
        )

    if token_cards and tokens_json_path is not None and token_sheet_output_path is not None:
        saved_files.append(
            save_deck_saved_object(
                cards=token_cards,
                output_path=tokens_json_path,
                sheet_base_path=token_sheet_output_path,
                back_url=back_url,
                deck_name=tokens_deck_name,
                cols=cols,
                rows=rows,
                max_rows_per_sheet=max_rows_per_sheet,
                indent=indent,
            )
        )

    return saved_files
