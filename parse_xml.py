from pathlib import Path
from typing import NamedTuple, Sequence
from xml.etree import ElementTree


RARITY_WORD_TO_CHAR = {
    "common": "C",
    "uncommon": "U",
    "rare": "R",
    "mythic": "M",
}


class CardData(NamedTuple):
    name: str | None = None
    text: str | None = None
    layout: str | None = None
    side: str | None = None
    card_type: str | None = None
    main_type: str | None = None
    mana_cost: str | None = None
    cmc: str | None = None
    colors: str | None = None
    color_identity: str | None = None
    power_toughness: str | None = None
    loyalty: str | None = None
    set_name: str | None = None
    rarity: str | None = None
    uuid: str | None = None
    image_url: str | None = None
    number: str | None = None
    related_card: str | None = None
    table_row: int | None = None

    @property
    def tabletop_simulator_nickname(self) -> str | None:
        if self.name and self.card_type and self.cmc:
            return f"{self.name}\n{self.card_type.replace('—', '--')} "
        return f"{self.name} " if self.name else None

    @property
    def tabletop_simulator_description(self) -> str:
        description: list[str] = []
        if self.mana_cost:
            assert self.cmc
            description.append(f"{self.mana_cost} (CMC {self.cmc})")
        if self.set_name and self.rarity:
            description.append(f"{self.set_name}-{RARITY_WORD_TO_CHAR[self.rarity]}")
        return "\n".join(description)

def _element_text(element: ElementTree.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    return '\n'.join(line.strip() for line in element.text.splitlines()).strip() or None


def parse_cards_from_xml(xml_path: str | Path | None = None) -> list[CardData]:
    """Parse every card face in a Cockatrice card database XML file.

    If xml_path is not specified, discovers and parses the sole XML file in input_data/.
    """
    if xml_path is None:
        input_data_dir = Path('input_data')
        if not input_data_dir.is_dir():
            raise FileNotFoundError(f"No XML files found: directory '{input_data_dir}' does not exist.")
        xml_files = [
            path for path in input_data_dir.iterdir()
            if path.is_file() and path.suffix.casefold() == '.xml'
        ]
        if not xml_files:
            raise FileNotFoundError("No XML files found in input_data/")
        if len(xml_files) > 1:
            raise ValueError(f"Expected exactly one XML file in input_data/, found {len(xml_files)}")
        xml_path = xml_files[0]

    root = ElementTree.parse(xml_path).getroot()
    cards: list[CardData] = []

    for card_element in root.findall('./cards/card'):
        properties = card_element.find('prop')
        set_element = card_element.find('set')
        table_row_text = _element_text(card_element.find('tablerow'))

        def property_text(tag: str) -> str | None:
            return _element_text(properties.find(tag)) if properties is not None else None

        cards.append(CardData(
            name=_element_text(card_element.find('name')),
            text=_element_text(card_element.find('text')),
            layout=property_text('layout'),
            side=property_text('side'),
            card_type=property_text('type'),
            main_type=property_text('maintype'),
            mana_cost=property_text('manacost'),
            cmc=property_text('cmc'),
            colors=property_text('colors'),
            color_identity=property_text('coloridentity'),
            power_toughness=property_text('pt'),
            loyalty=property_text('loyalty'),
            set_name=_element_text(set_element),
            rarity=set_element.get('rarity') if set_element is not None else None,
            uuid=set_element.get('uuid') if set_element is not None else None,
            image_url=set_element.get('picurl') if set_element is not None else None,
            number=set_element.get('num') if set_element is not None else None,
            related_card=_element_text(card_element.find('related')),
            table_row=int(table_row_text) if table_row_text else None,
        ))

    return cards


def separate_cards(cards: Sequence[CardData]) -> tuple[list[CardData], list[CardData]]:
    """Separate front/single-sided cards from the back faces of transform cards."""
    front_cards: list[CardData] = []
    back_cards: list[CardData] = []
    for card in cards:
        side = card.side
        if side is not None and side.casefold() == 'back':
            back_cards.append(card)
        else:
            front_cards.append(card)
    return front_cards, back_cards
