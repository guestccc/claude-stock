#!/usr/bin/env bun
// buddy-reroll-bun.js

const crypto = require('crypto');
const SALT = 'friend-2026-401';
const SPECIES = [
  'duck',
  'goose',
  'blob',
  'cat',
  'dragon',
  'octopus',
  'owl',
  'penguin',
  'turtle',
  'snail',
  'ghost',
  'axolotl',
  'capybara',
  'cactus',
  'robot',
  'rabbit',
  'mushroom',
  'chonk',
];
const RARITIES = ['common', 'uncommon', 'rare', 'epic', 'legendary'];
const RARITY_WEIGHTS = {
  common: 60,
  uncommon: 25,
  rare: 10,
  epic: 4,
  legendary: 1,
};
const RARITY_RANK = { common: 0, uncommon: 1, rare: 2, epic: 3, legendary: 4 };

console.log('*************************************************');
console.log();

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashString(s) {
  return Number(BigInt(Bun.hash(s)) & 0xffffffffn);
}

function pick(rng, arr) {
  return arr[Math.floor(rng() * arr.length)];
}

function rollRarity(rng) {
  let roll = rng() * 100;
  for (const r of RARITIES) {
    roll -= RARITY_WEIGHTS[r];
    if (roll < 0) return r;
  }
  return 'common';
}

const TARGET = process.argv[2] || 'duck';
const MAX = parseInt(process.argv[3]) || 500000;

let best = { rarity: 'common', uid: '' };
for (let i = 0; i < MAX; i++) {
  const uid = crypto.randomBytes(32).toString('hex');
  const rng = mulberry32(hashString(uid + SALT));
  const rarity = rollRarity(rng);
  const species = pick(rng, SPECIES);
  if (species === TARGET && RARITY_RANK[rarity] > RARITY_RANK[best.rarity]) {
    best = { rarity, uid };
    console.log(`found: ${rarity} ${species} -> ${uid}`);
    if (rarity === 'legendary') break;
  }
}
console.log(`\nBest: ${best.rarity} ${TARGET} -> ${best.uid}`);
