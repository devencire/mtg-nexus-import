import json
import tempfile
from pathlib import Path
import pytest
from PIL import Image

import main
import parse_xml
import image_download
import card_sheets
import tts_saved_object


def test_card_data_defaults_to_none():
    assert all(value is None for value in main.CardData())


def test_parse_cards_from_xml_discovers_single_xml_file(tmp_path, monkeypatch):
    input_data = tmp_path / 'input_data'
    input_data.mkdir()
    xml_path = input_data / 'cards.XML'
    xml_path.write_text('<cockatrice_carddatabase><cards /></cockatrice_carddatabase>', encoding='utf-8')
    (input_data / 'notes.txt').write_text('not XML', encoding='utf-8')
    (input_data / 'nested').mkdir()
    (input_data / 'nested' / 'ignored.xml').write_text(
        '<cockatrice_carddatabase><cards /></cockatrice_carddatabase>', encoding='utf-8'
    )
    monkeypatch.chdir(tmp_path)

    assert parse_xml.parse_cards_from_xml() == []


def test_parse_cards_from_xml_errors_when_no_xml_file_exists(tmp_path, monkeypatch):
    (tmp_path / 'input_data').mkdir()
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match='No XML files found'):
        parse_xml.parse_cards_from_xml()


def test_parse_cards_from_xml_errors_when_multiple_xml_files_exist(tmp_path, monkeypatch):
    input_data = tmp_path / 'input_data'
    input_data.mkdir()
    for filename in ('first.xml', 'second.xml'):
        (input_data / filename).write_text(
            '<cockatrice_carddatabase><cards /></cockatrice_carddatabase>', encoding='utf-8'
        )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match='exactly one XML file'):
        parse_xml.parse_cards_from_xml()


def test_parse_cards_from_xml_explicit_path_works_with_multiple_xml_files(tmp_path, monkeypatch):
    input_data = tmp_path / 'input_data'
    input_data.mkdir()
    xml_path = input_data / 'selected.xml'
    xml_path.write_text('<cockatrice_carddatabase><cards /></cockatrice_carddatabase>', encoding='utf-8')
    (input_data / 'other.xml').write_text(
        '<cockatrice_carddatabase><cards /></cockatrice_carddatabase>', encoding='utf-8'
    )
    monkeypatch.chdir(tmp_path)

    assert parse_xml.parse_cards_from_xml(xml_path) == []


def test_parse_cards_from_xml():
    cards = main.parse_cards_from_xml()

    assert len(cards) == 413
    assert cards[0] == main.CardData(
        name='Angel Soldier',
        text='Flying, vigilance',
        layout='normal',
        side='front',
        card_type='Token Creature — Angel Soldier',
        main_type='Token Creature',
        mana_cost=None,
        cmc='0',
        colors=None,
        color_identity=None,
        power_toughness='4/4',
        loyalty=None,
        set_name='GDS',
        rarity='rare',
        uuid='1eec9c70-1eec-9c70-1eec-9c701eec9c70',
        image_url='https://www.mtgnexus.com/img/ccc/ren/11648/399318.jpg',
        number='1',
        related_card=None,
        table_row=2,
    )


def test_parse_cards_from_xml_includes_both_transform_sides():
    cards = main.parse_cards_from_xml()
    shard = next(card for card in cards if card.name == 'Shard of Family')
    spark = next(card for card in cards if card.name == 'Spark of Family')

    assert shard.side == 'front'
    assert shard.related_card == spark.name
    assert spark.side == 'back'
    assert spark.related_card == shard.name


def test_create_card_sheet_grid():
    # Create 5 mock images (100x150)
    images = [Image.new('RGB', (100, 150), color=(i * 40, 50, 100)) for i in range(5)]

    # Default scale is 1x: 2 columns -> ceil(5 / 2) = 3 rows
    sheet = main.create_card_sheet(images, cols=2)
    assert sheet.size == (200, 450)
    assert sheet.mode == 'RGB'

    sheet_2x = main.create_card_sheet(images, cols=2, scale=2.0)
    assert sheet_2x.size == (400, 900)


def test_create_card_sheet_with_custom_rows_and_size():
    images = [Image.new('RGB', (50, 50), color=(255, 0, 0)) for _ in range(3)]
    sheet = main.create_card_sheet(images, cols=2, rows=4, card_size=(100, 200), background_color=(10, 20, 30))
    assert sheet.size == (200, 800)
    # Background in unused area
    assert sheet.getpixel((150, 750)) == (10, 20, 30)

    sheet_2x = main.create_card_sheet(images, cols=2, rows=4, card_size=(100, 200), scale=2.0, background_color=(10, 20, 30))
    assert sheet_2x.size == (400, 1600)
    assert sheet_2x.getpixel((300, 1500)) == (10, 20, 30)


def test_create_card_sheet_validation_errors():
    with pytest.raises(ValueError, match="Cannot create a card sheet from an empty list"):
        main.create_card_sheet([])

    with pytest.raises(ValueError, match="Number of columns must be positive"):
        main.create_card_sheet([Image.new('RGB', (10, 10))], cols=0)

    with pytest.raises(ValueError, match="cannot fit"):
        main.create_card_sheet([Image.new('RGB', (10, 10)) for _ in range(5)], cols=2, rows=2)

    with pytest.raises(ValueError, match="Scale multiplier must be positive"):
        main.create_card_sheet([Image.new('RGB', (10, 10))], scale=-1)


def test_get_indexed_output_path():
    assert main.get_indexed_output_path('card_sheet.jpg', 1) == Path('card_sheet_1.jpg')
    assert main.get_indexed_output_path('card_sheet.jpg', 2) == Path('card_sheet_2.jpg')
    assert main.get_indexed_output_path('output/decks/sheet.jpeg', 3) == Path('output/decks/sheet_3.jpeg')
    assert main.get_indexed_output_path('sheet_{index}.jpg', 5) == Path('sheet_5.jpg')
    assert main.get_indexed_output_path('sheet_{i}.jpg', 5) == Path('sheet_5.jpg')


def test_create_card_sheets_splitting():
    # 150 mock images with 10 cols, max_rows=7 -> capacity 70
    images = [Image.new('RGB', (10, 20), color=(i % 256, 0, 0)) for i in range(150)]
    sheets = main.create_card_sheets(images, cols=10, max_rows_per_sheet=7)
    assert len(sheets) == 3
    assert sheets[0].size == (100, 140)
    assert sheets[1].size == (100, 140)
    assert sheets[2].size == (100, 20)

    sheets_2x = main.create_card_sheets(images, cols=10, max_rows_per_sheet=7, scale=2.0)
    assert sheets_2x[0].size == (200, 280)
    assert sheets_2x[1].size == (200, 280)
    assert sheets_2x[2].size == (200, 40)


def test_create_card_sheets_with_fixed_rows():
    # 5 images with 2 cols, fixed rows=2 -> capacity 4 per sheet
    images = [Image.new('RGB', (10, 20)) for _ in range(5)]
    sheets = main.create_card_sheets(images, cols=2, rows=2)
    assert len(sheets) == 2
    assert sheets[0].size == (20, 40)
    assert sheets[1].size == (20, 40)

    sheets_2x = main.create_card_sheets(images, cols=2, rows=2, scale=2.0)
    assert sheets_2x[0].size == (40, 80)
    assert sheets_2x[1].size == (40, 80)


def test_download_and_create_card_sheet_sample():
    cards = main.parse_cards_from_xml()[:3]
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / 'test_sheet.jpg'
        sheets = main.download_and_create_card_sheet(
            cards=cards,
            output_path=out_path,
            cols=2,
            max_workers=3,
        )
        assert len(sheets) == 1
        expected_file = Path(tmpdir) / 'test_sheet_1.jpg'
        assert expected_file.exists()
        with Image.open(expected_file) as loaded:
            assert loaded.format == 'JPEG'
            assert loaded.size == sheets[0].size


def test_separate_cards_uses_xml_side_metadata():
    front = main.CardData(name='Front', side='front', image_url='back-looking-b.jpg')
    back = main.CardData(name='Back', side='back', image_url='front-looking-a.jpg')

    front_cards, back_cards = main.separate_cards([front, back])

    assert front_cards == [front]
    assert back_cards == [back]


def test_separate_cards_from_xml():
    cards = main.parse_cards_from_xml()
    front_cards, back_cards = main.separate_cards(cards)
    assert len(front_cards) == 388
    assert len(back_cards) == 25
    assert len(front_cards) + len(back_cards) == 413
    assert all(card.side == 'back' for card in back_cards)
    assert not any(card.side == 'back' for card in front_cards)


def test_download_and_create_card_sheet_with_two_sided_cards():
    all_cards = main.parse_cards_from_xml()
    back_cards = [card for card in all_cards if card.side == 'back'][:2]
    paired_front_names = {card.related_card for card in back_cards}
    paired_fronts = [card for card in all_cards if card.name in paired_front_names]
    single_sided = next(
        card for card in all_cards
        if card.layout == 'normal' and not (card.main_type and 'Token' in card.main_type)
    )
    cards = [single_sided, *paired_fronts, *back_cards]
    with tempfile.TemporaryDirectory() as tmpdir:
        out_main = Path(tmpdir) / 'card_sheet.jpg'
        out_backs = Path(tmpdir) / 'card_sheet_double_sided_backs.jpg'
        sheets = main.download_and_create_card_sheet(
            cards=cards,
            output_path=out_main,
            backs_output_path=out_backs,
            cols=2,
            max_workers=5,
        )
        assert len(sheets) == 1
        out_main_1 = Path(tmpdir) / 'card_sheet_1.jpg'
        out_backs_1 = Path(tmpdir) / 'card_sheet_double_sided_backs_1.jpg'
        assert out_main_1.exists()
        assert out_backs_1.exists()

        with Image.open(out_main_1) as main_img:
            assert main_img.format == 'JPEG'
            assert main_img.size == (800, 1120)

        with Image.open(out_backs_1) as backs_img:
            assert backs_img.format == 'JPEG'
            assert backs_img.size == (800, 560)


def test_download_and_create_card_sheet_no_backs_does_not_create_backs_file():
    cards = main.parse_cards_from_xml()[:2]
    with tempfile.TemporaryDirectory() as tmpdir:
        out_main = Path(tmpdir) / 'card_sheet.jpg'
        out_backs = Path(tmpdir) / 'card_sheet_double_sided_backs.jpg'
        main.download_and_create_card_sheet(
            cards=cards,
            output_path=out_main,
            backs_output_path=out_backs,
            cols=2,
            max_workers=2,
        )
        assert (Path(tmpdir) / 'card_sheet_1.jpg').exists()
        assert not (Path(tmpdir) / 'card_sheet_double_sided_backs_1.jpg').exists()


def test_download_and_create_card_sheet_splitting_files():
    # 5 front urls with cols=2, max_rows_per_sheet=1 -> capacity 2 per sheet -> 3 sheets
    cards = [
        card for card in main.parse_cards_from_xml()
        if not (card.main_type and 'Token' in card.main_type)
    ][:5]
    with tempfile.TemporaryDirectory() as tmpdir:
        out_main = Path(tmpdir) / 'card_sheet.jpg'
        sheets = main.download_and_create_card_sheet(
            cards=cards,
            output_path=out_main,
            backs_output_path=None,
            cols=2,
            max_rows_per_sheet=1,
            max_workers=5,
        )
        assert len(sheets) == 3
        for i in range(1, 4):
            sheet_file = Path(tmpdir) / f'card_sheet_{i}.jpg'
            assert sheet_file.exists()
            with Image.open(sheet_file) as img:
                assert img.format == 'JPEG'


def test_download_and_create_card_sheet_tokens_separation_and_saving():
    all_cards = main.parse_cards_from_xml()
    token_cards = [card for card in all_cards if card.main_type and 'Token' in card.main_type][:2]
    regular_fronts = [
        card for card in all_cards
        if card.side != 'back' and not (card.main_type and 'Token' in card.main_type)
    ][:2]
    back_cards = [card for card in all_cards if card.side == 'back'][:1]

    cards = [*regular_fronts, *token_cards, *back_cards]

    with tempfile.TemporaryDirectory() as tmpdir:
        out_main = Path(tmpdir) / 'card_sheet.jpg'
        out_backs = Path(tmpdir) / 'card_sheet_double_sided_backs.jpg'
        out_tokens = Path(tmpdir) / 'card_sheet_tokens.jpg'

        sheets = main.download_and_create_card_sheet(
            cards=cards,
            output_path=out_main,
            backs_output_path=out_backs,
            token_output_path=out_tokens,
            cols=2,
            max_workers=5,
        )

        assert len(sheets) == 1
        out_main_1 = Path(tmpdir) / 'card_sheet_1.jpg'
        out_backs_1 = Path(tmpdir) / 'card_sheet_double_sided_backs_1.jpg'
        out_tokens_1 = Path(tmpdir) / 'card_sheet_tokens_1.jpg'

        assert out_main_1.exists()
        assert out_backs_1.exists()
        assert out_tokens_1.exists()

        # 2 regular fronts with 2 cols = 1 row (800x560)
        with Image.open(out_main_1) as main_img:
            assert main_img.size == (800, 560)

        # 1 back card with 2 cols = 1 row (800x560)
        with Image.open(out_backs_1) as backs_img:
            assert backs_img.size == (800, 560)

        # 2 token cards with 2 cols = 1 row (800x560)
        with Image.open(out_tokens_1) as token_img:
            assert token_img.size == (800, 560)


def test_download_and_create_card_sheet_no_tokens_output_when_none():
    all_cards = main.parse_cards_from_xml()
    token_cards = [card for card in all_cards if card.main_type and 'Token' in card.main_type][:2]
    regular_fronts = [
        card for card in all_cards
        if card.side != 'back' and not (card.main_type and 'Token' in card.main_type)
    ][:2]
    cards = [*regular_fronts, *token_cards]

    with tempfile.TemporaryDirectory() as tmpdir:
        out_main = Path(tmpdir) / 'card_sheet.jpg'
        main.download_and_create_card_sheet(
            cards=cards,
            output_path=out_main,
            backs_output_path=None,
            token_output_path=None,
            cols=2,
            max_workers=2,
        )

        assert (Path(tmpdir) / 'card_sheet_1.jpg').exists()
        assert not (Path(tmpdir) / 'card_sheet_tokens_1.jpg').exists()


def test_download_and_create_card_sheet_only_tokens():
    all_cards = main.parse_cards_from_xml()
    token_cards = [card for card in all_cards if card.main_type and 'Token' in card.main_type][:3]

    with tempfile.TemporaryDirectory() as tmpdir:
        out_main = Path(tmpdir) / 'card_sheet.jpg'
        out_tokens = Path(tmpdir) / 'card_sheet_tokens.jpg'

        sheets = main.download_and_create_card_sheet(
            cards=token_cards,
            output_path=out_main,
            backs_output_path=None,
            token_output_path=out_tokens,
            cols=2,
            max_workers=3,
        )

        # No regular cards so main_sheet is not created
        assert not (Path(tmpdir) / 'card_sheet_1.jpg').exists()
        assert (Path(tmpdir) / 'card_sheet_tokens_1.jpg').exists()
        assert len(sheets) == 1


def test_download_and_create_card_sheet_quality_and_subsampling():
    cards = main.parse_cards_from_xml()[:2]
    with tempfile.TemporaryDirectory() as tmpdir:
        out_main = Path(tmpdir) / 'card_sheet.jpg'
        main.download_and_create_card_sheet(
            cards=cards,
            output_path=out_main,
            backs_output_path=None,
            cols=2,
            quality=98,
            subsampling=0,
            optimize=True,
            max_workers=2,
        )
        saved_file = Path(tmpdir) / 'card_sheet_1.jpg'
        assert saved_file.exists()
        with Image.open(saved_file) as img:
            assert img.format == 'JPEG'


def test_download_and_create_card_sheet_scale_options():
    cards = main.parse_cards_from_xml()[:2]
    with tempfile.TemporaryDirectory() as tmpdir:
        # Default scale is 1x: two 400x560 cards -> sheet: 800x560
        out_1x = Path(tmpdir) / 'sheet_1x.jpg'
        main.download_and_create_card_sheet(
            cards=cards,
            output_path=out_1x,
            backs_output_path=None,
            cols=2,
            max_workers=2,
        )
        with Image.open(Path(tmpdir) / 'sheet_1x_1.jpg') as img:
            assert img.size == (800, 560)

        # Explicit 2x scale: sheet: 1600x1120
        out_2x = Path(tmpdir) / 'sheet_2x.jpg'
        main.download_and_create_card_sheet(
            cards=cards,
            output_path=out_2x,
            backs_output_path=None,
            cols=2,
            scale=2.0,
            max_workers=2,
        )
        with Image.open(Path(tmpdir) / 'sheet_2x_1.jpg') as img:
            assert img.size == (1600, 1120)

        # Explicit custom scale factor: scale=1.5 -> cards: 600x840 -> sheet: 1200x840
        out_scale = Path(tmpdir) / 'sheet_scale.jpg'
        main.download_and_create_card_sheet(
            cards=cards,
            output_path=out_scale,
            backs_output_path=None,
            cols=2,
            scale=1.5,
            max_workers=2,
        )
        with Image.open(Path(tmpdir) / 'sheet_scale_1.jpg') as img:
            assert img.size == (1200, 840)


def test_image_download_empty():
    assert image_download.download_images([]) == []


def test_direct_module_exports():
    assert parse_xml.CardData is main.CardData
    assert parse_xml.parse_cards_from_xml is main.parse_cards_from_xml
    assert parse_xml.separate_cards is main.separate_cards
    assert image_download.download_image is main.download_image
    assert image_download.download_images is main.download_images
    assert card_sheets.create_card_sheet is main.create_card_sheet
    assert card_sheets.create_card_sheets is main.create_card_sheets
    assert card_sheets.download_and_create_card_sheet is main.download_and_create_card_sheet
    assert card_sheets.get_indexed_output_path is main.get_indexed_output_path
    assert tts_saved_object.create_deck_saved_object is main.create_deck_saved_object
    assert tts_saved_object.save_deck_saved_object is main.save_deck_saved_object
    assert tts_saved_object.create_tts_saved_objects is main.create_tts_saved_objects
    assert tts_saved_object.separate_cube_sparks_tokens is main.separate_cube_sparks_tokens


def test_separate_cube_sparks_tokens():
    cube_card = main.CardData(name='Llanowar Elves', side='front', main_type='Creature')
    spark_card = main.CardData(name='Spark of Hope', side='back', main_type='Enchantment')
    token_card = main.CardData(name='Angel Soldier', side='front', main_type='Token Creature')

    cube_cards, spark_cards, token_cards = main.separate_cube_sparks_tokens([cube_card, spark_card, token_card])
    assert cube_cards == [cube_card]
    assert spark_cards == [spark_card]
    assert token_cards == [token_card]


def test_create_deck_saved_object_validation_errors():
    with pytest.raises(ValueError, match="Cannot create a saved object deck from an empty list"):
        main.create_deck_saved_object([])

    with pytest.raises(ValueError, match="Number of columns must be positive"):
        main.create_deck_saved_object([main.CardData(name='Test')], cols=0)

    with pytest.raises(ValueError, match="Rows per sheet must be positive"):
        main.create_deck_saved_object([main.CardData(name='Test')], rows=0)


def test_create_deck_saved_object_single_sheet():
    cards = [main.CardData(name=f'Card {i}') for i in range(25)]
    data = main.create_deck_saved_object(
        cards=cards,
        sheet_base_path='output_data/card_sheet.jpg',
        back_url='optimal_magic_card_back.jpg',
        deck_name='Test Deck',
        cols=10,
        start_deck_id=1,
    )

    assert data["SaveName"] == ""
    assert data["ObjectStates"][0]["Name"] == "Deck"
    assert data["ObjectStates"][0]["Nickname"] == "Test Deck"
    deck = data["ObjectStates"][0]
    assert len(deck["DeckIDs"]) == 25
    assert deck["DeckIDs"] == [100 + i for i in range(25)]
    assert "1" in deck["CustomDeck"]
    assert deck["CustomDeck"]["1"]["NumWidth"] == 10
    assert deck["CustomDeck"]["1"]["NumHeight"] == 3  # ceil(25 / 10)
    assert Path(deck["CustomDeck"]["1"]["FaceURL"]).is_absolute()
    assert Path(deck["CustomDeck"]["1"]["FaceURL"]).name == 'card_sheet_1.jpg'
    assert Path(deck["CustomDeck"]["1"]["BackURL"]).is_absolute()
    assert len(deck["ContainedObjects"]) == 25
    assert deck["ContainedObjects"][0]["Nickname"] == 'Card 0 '
    assert deck["ContainedObjects"][0]["CardID"] == 100
    assert deck["ContainedObjects"][0]["Hands"] is True


def test_create_deck_saved_object_multi_sheet():
    cards = [main.CardData(name=f'Card {i}') for i in range(150)]
    data = main.create_deck_saved_object(
        cards=cards,
        sheet_base_path='output_data/card_sheet.jpg',
        deck_name='Cube Deck',
        cols=10,
        max_rows_per_sheet=7,
        start_deck_id=10,
    )

    deck = data["ObjectStates"][0]
    assert len(deck["DeckIDs"]) == 150
    # Capacity is 70 cards per sheet -> 3 sheets (70, 70, 10)
    assert "10" in deck["CustomDeck"]
    assert "11" in deck["CustomDeck"]
    assert "12" in deck["CustomDeck"]
    assert deck["CustomDeck"]["10"]["NumHeight"] == 7
    assert deck["CustomDeck"]["11"]["NumHeight"] == 7
    assert deck["CustomDeck"]["12"]["NumHeight"] == 1  # ceil(10 / 10)
    assert deck["DeckIDs"][:70] == [1000 + i for i in range(70)]
    assert deck["DeckIDs"][70:140] == [1100 + i for i in range(70)]
    assert deck["DeckIDs"][140:] == [1200 + i for i in range(10)]


def test_create_tts_saved_objects_full_from_xml():
    all_cards = main.parse_cards_from_xml()
    with tempfile.TemporaryDirectory() as tmpdir:
        cube_p = Path(tmpdir) / 'cube.json'
        sparks_p = Path(tmpdir) / 'sparks.json'
        tokens_p = Path(tmpdir) / 'tokens.json'

        saved = main.create_tts_saved_objects(
            cards=all_cards,
            output_path=cube_p,
            backs_output_path=sparks_p,
            token_output_path=tokens_p,
            sheet_output_path=Path(tmpdir) / 'card_sheet.jpg',
            backs_sheet_output_path=Path(tmpdir) / 'card_sheet_double_sided_backs.jpg',
            token_sheet_output_path=Path(tmpdir) / 'card_sheet_tokens.jpg',
        )

        assert len(saved) == 3
        assert cube_p.exists()
        assert sparks_p.exists()
        assert tokens_p.exists()

        with open(cube_p, 'r', encoding='utf-8') as f:
            cube_data = json.load(f)
            cube_deck = cube_data["ObjectStates"][0]
            # 360 cube cards
            assert len(cube_deck["DeckIDs"]) == 360
            assert len(cube_deck["ContainedObjects"]) == 360
            # 360 / 70 = 5 full sheets (70) + 1 sheet (10) = 6 sheets
            assert len(cube_deck["CustomDeck"]) == 6
            for sheet_id, sheet_spec in cube_deck["CustomDeck"].items():
                face_url = sheet_spec["FaceURL"]
                assert Path(face_url).is_absolute()
                assert 'card_sheet_' in face_url

        with open(sparks_p, 'r', encoding='utf-8') as f:
            sparks_data = json.load(f)
            sparks_deck = sparks_data["ObjectStates"][0]
            # 25 sparks cards
            assert len(sparks_deck["DeckIDs"]) == 25
            assert len(sparks_deck["ContainedObjects"]) == 25
            assert len(sparks_deck["CustomDeck"]) == 1
            face_url = sparks_deck["CustomDeck"]["1"]["FaceURL"]
            assert Path(face_url).is_absolute()
            assert 'card_sheet_double_sided_backs_1.jpg' in face_url

        with open(tokens_p, 'r', encoding='utf-8') as f:
            tokens_data = json.load(f)
            tokens_deck = tokens_data["ObjectStates"][0]
            # 27 tokens cards
            assert len(tokens_deck["DeckIDs"]) == 28
            assert len(tokens_deck["ContainedObjects"]) == 28
            assert len(tokens_deck["CustomDeck"]) == 1
            face_url = tokens_deck["CustomDeck"]["1"]["FaceURL"]
            assert Path(face_url).is_absolute()
            assert 'card_sheet_tokens_1.jpg' in face_url

