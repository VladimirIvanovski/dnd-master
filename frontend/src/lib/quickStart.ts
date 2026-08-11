const ADJECTIVES = [
  "Shattered",
  "Forgotten",
  "Burning",
  "Silent",
  "Gilded",
  "Cursed",
  "Wandering",
  "Hollow",
  "Stormbound",
  "Obsidian",
  "Emerald",
  "Ashen",
];

const PLACES = [
  "Dunes",
  "Marches",
  "Crown",
  "Reach",
  "Spire",
  "Expanse",
  "Depths",
  "Archipelago",
  "Wastes",
  "Vale",
  "Coast",
  "Thrones",
];

const HOOKS = [
  "Caravans vanish along the trade roads and locals blame lights in the hills.",
  "An ancient seal cracked open and the weather turned wrong overnight.",
  "A rival city offers gold for a map that should not exist.",
  "Refugees speak of a tower that walks when no one watches.",
  "A noble's heir went missing after bargaining with a masked stranger.",
  "The wells taste of iron and the priests refuse to pray aloud.",
  "Smugglers found a vault under the sand filled with singing glass.",
  "A border fort went silent; only one rider returned without a tongue.",
];

const FIRST = [
  "Aric",
  "Lyra",
  "Torin",
  "Sable",
  "Nessa",
  "Kael",
  "Mira",
  "Rook",
  "Vesper",
  "Joren",
  "Ilya",
  "Briar",
];

const LAST = [
  "Ashfall",
  "Reed",
  "Nightmark",
  "Vale",
  "Storm",
  "Hollow",
  "Cinder",
  "Thorn",
  "Glass",
  "Kestrel",
];

const RACES = ["Human", "Elf", "Dwarf", "Halfling", "Tiefling", "Half-Orc"];
const CLASSES = ["Fighter", "Rogue", "Ranger", "Cleric", "Wizard", "Bard"];

function pick<T>(items: T[]): T {
  return items[Math.floor(Math.random() * items.length)]!;
}

export function randomCampaignName(): string {
  return `${pick(ADJECTIVES)} ${pick(PLACES)}`;
}

export function randomCampaignDescription(name: string): string {
  return `${name}: ${pick(HOOKS)} You arrive as an outsider with little but your wits and steel.`;
}

export function randomCharacter(): {
  name: string;
  race: string;
  class_name: string;
} {
  const name =
    Math.random() < 0.55 ? pick(FIRST) : `${pick(FIRST)} ${pick(LAST)}`;
  return {
    name,
    race: pick(RACES),
    class_name: pick(CLASSES),
  };
}
