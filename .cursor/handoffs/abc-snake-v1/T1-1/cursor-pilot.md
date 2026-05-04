# Cursor Pilot — T1-1: Game Engine Core

**handoff_id:** `abc-snake-v1`
**task_id:** `T1-1`

## CURSOR_PILOT_PROMPT

### ROLE
You are the implementer for ABC Snake T1-1. Create the pure TypeScript game engine files with zero React dependencies and zero side effects.

### TASK
Create three files in `projects/abc-snake/src/game/`:
1. `types.ts` — all TypeScript type definitions
2. `constants.ts` — game constants
3. `engine.ts` — pure game logic functions

Remove the existing `.gitkeep` from `projects/abc-snake/src/game/`.

### CONTEXT

**Game concept:** ABC Snake — a snake that must eat letters A→Z in order. Multiple letters appear on the board; eating the wrong letter costs a life. Completing all 26 letters wins.

**tsconfig constraints (CRITICAL — compiler will reject violations):**

| Flag | Constraint |
|------|-----------|
| `erasableSyntaxOnly: true` | NO `enum`, NO `namespace` — use string literal unions |
| `verbatimModuleSyntax: true` | Type-only imports MUST use `import type { }` syntax |
| `noUnusedLocals: true` | Every imported symbol must be used |
| `noUnusedParameters: true` | Every function parameter must be used |
| `strict: true` | Full strictness including `strictNullChecks` |

**Module resolution:** Vite bundler mode with `allowImportingTsExtensions: true` — use `./types.ts` (with `.ts` extension) in imports within the game/ folder.

---

### FILE 1: `projects/abc-snake/src/game/types.ts`

```typescript
// Position on the grid (0-indexed)
export type Position = { x: number; y: number };

// Four movement directions
export type Direction = 'UP' | 'DOWN' | 'LEFT' | 'RIGHT';

// A letter food item on the board
export type LetterFood = {
  position: Position;
  letter: string;       // single uppercase letter e.g. 'A'
  letterIndex: number;  // 0-25
  color: string;        // hex color from LETTER_COLORS
};

// The snake: head is index 0, tail is last element
export type Snake = {
  segments: Position[];  // head-first array
  direction: Direction;
};

// Game difficulty affects speed
export type Difficulty = 'easy' | 'medium' | 'hard';

// Game lifecycle state
export type GameStatus = 'idle' | 'playing' | 'paused' | 'won' | 'lost';

// Complete game state — everything needed to render one frame
export type GameState = {
  snake: Snake;
  food: LetterFood[];           // letters currently on board
  nextLetterIndex: number;      // 0-25, index of the next letter to eat
  score: number;
  lives: number;
  difficulty: Difficulty;
  status: GameStatus;
  tickCount: number;            // increments each tick, used for speed ramping
  currentSpeed: number;         // ms per tick
};
```

---

### FILE 2: `projects/abc-snake/src/game/constants.ts`

```typescript
export const GRID_SIZE = 20;           // 20×20 grid cells
export const CELL_SIZE = 28;           // pixels per cell (for rendering)
export const INITIAL_SNAKE_LENGTH = 3; // starting snake length

// Speed in milliseconds per tick per difficulty
export const SPEEDS: Record<string, number> = {
  easy: 200,
  medium: 140,
  hard: 90,
};

export const SPEED_INCREASE_INTERVAL = 5;  // every N letters eaten, speed increases
export const SPEED_INCREASE_AMOUNT = 5;    // ms reduction per speed step (minimum 50ms)
export const MAX_LETTERS_ON_BOARD = 4;     // max simultaneous letters visible
export const TOTAL_LIVES = 3;

// 26 distinct colors for A–Z
export const LETTER_COLORS: string[] = [
  '#FF6B6B', '#FF8E53', '#FFA500', '#FFD93D', '#6BCB77',
  '#4D96FF', '#845EC2', '#FF6F91', '#00C9A7', '#C34A36',
  '#FF9671', '#00B8D9', '#B39CD0', '#F9F871', '#C4FCEF',
  '#FF6060', '#52B4F3', '#E8A838', '#45B7D1', '#96CEB4',
  '#DDA0DD', '#20B2AA', '#F0E68C', '#DB7093', '#3CB371',
  '#9370DB',
];

// All 26 letters in order
export const ALPHABET: string[] = Array.from({ length: 26 }, (_, i) =>
  String.fromCharCode(65 + i)
);
```

---

### FILE 3: `projects/abc-snake/src/game/engine.ts`

All functions must be **pure** — no global mutation, no `Date.now()`, no `Math.random()` calls without being passed as a parameter.

```typescript
import type { Direction, Difficulty, GameState, LetterFood, Position, Snake } from './types.ts';
import {
  ALPHABET,
  GRID_SIZE,
  INITIAL_SNAKE_LENGTH,
  LETTER_COLORS,
  MAX_LETTERS_ON_BOARD,
  SPEEDS,
  SPEED_INCREASE_AMOUNT,
  SPEED_INCREASE_INTERVAL,
  TOTAL_LIVES,
} from './constants.ts';
```

#### `createInitialState(difficulty: Difficulty): GameState`
- Place snake horizontally centered, starting at `{ x: Math.floor(GRID_SIZE / 2), y: Math.floor(GRID_SIZE / 2) }` as head, extending left.
- Direction: `'RIGHT'`
- `lives: TOTAL_LIVES`
- `score: 0`
- `nextLetterIndex: 0`
- `status: 'idle'`
- `tickCount: 0`
- `currentSpeed: SPEEDS[difficulty]`
- `food: []` (letters spawned later on first tick or by caller)

#### `moveSnake(snake: Snake, grow: boolean): Snake`
- Compute new head position from `snake.direction` (wrap around grid edges using `% GRID_SIZE` with `(x + GRID_SIZE) % GRID_SIZE` for negative wrapping).
- If `grow` is `false`: return new snake with `[newHead, ...snake.segments.slice(0, -1)]`
- If `grow` is `true`: return new snake with `[newHead, ...snake.segments]`
- Direction unchanged.

#### `checkCollisions(snake: Snake): boolean`
- Returns `true` if head collides with any other segment (self-collision).
- Wall collisions are handled by wrapping, so no wall check needed.
- Compare `snake.segments[0]` against `snake.segments.slice(1)`.

#### `checkLetterEaten(snakeHead: Position, food: LetterFood[]): LetterFood | null`
- Returns the `LetterFood` whose `position` matches `snakeHead`, or `null`.
- Use exact `x === snakeHead.x && y === snakeHead.y` comparison.

#### `spawnLetter(food: LetterFood[], snake: Snake, nextLetterIndex: number, random: () => number): LetterFood[]`
- If `food.length >= MAX_LETTERS_ON_BOARD`, return `food` unchanged.
- Generate a random position not occupied by snake segments or existing food.
  - Use `random()` (returns 0–1) to pick `x = Math.floor(random() * GRID_SIZE)`, same for `y`.
  - Retry up to 100 times to find a free cell; if no free cell found, return unchanged.
- The new letter is `ALPHABET[nextLetterIndex % 26]` with color `LETTER_COLORS[nextLetterIndex % 26]`.
- Return `[...food, newLetter]`.

#### `getSpeed(difficulty: Difficulty, lettersEaten: number): number`
- Base speed: `SPEEDS[difficulty]`
- Reduction: `Math.floor(lettersEaten / SPEED_INCREASE_INTERVAL) * SPEED_INCREASE_AMOUNT`
- Return `Math.max(50, base - reduction)`

#### `tick(state: GameState, random: () => number): GameState`

Step order (critical — do not reorder):

1. If `state.status !== 'playing'`, return `state` unchanged.
2. Compute new head: apply direction to `state.snake.segments[0]` with grid wrapping.
3. Check `eaten = checkLetterEaten(newHead, state.food)` BEFORE moving.
4. Determine `grow = eaten !== null && eaten.letter === ALPHABET[state.nextLetterIndex]`.
5. Move snake: `newSnake = moveSnake(state.snake, grow)`.
6. Check self-collision: `collided = checkCollisions(newSnake)`.
7. Compute `midState`:
   - If `collided`: decrement lives. If `lives <= 0` set `status: 'lost'`. Reset snake to center. Keep food.
   - Else if `eaten !== null && eaten.letter === ALPHABET[state.nextLetterIndex]`:
     - Remove eaten letter from food.
     - Increment `nextLetterIndex`.
     - Increment `score` by `10 * (state.nextLetterIndex)` (score on the incremented index for bonus feel).
     - If `nextLetterIndex === 26`: set `status: 'won'`.
   - Else if `eaten !== null` (wrong letter):
     - Decrement lives. If `lives <= 0` set `status: 'lost'`.
     - Keep food as-is (wrong letter stays on board).
   - Update `currentSpeed = getSpeed(state.difficulty, midState.nextLetterIndex)`.
   - Increment `tickCount`.
8. Refill food: loop calling `spawnLetter` until `food.length >= MAX_LETTERS_ON_BOARD`, using the `nextLetterIndex` for new spawns.
   - IMPORTANT: spawn letters beyond `nextLetterIndex` too (up to `nextLetterIndex + MAX_LETTERS_ON_BOARD - 1`) so the board has a mix. Or simpler: always pass `nextLetterIndex` — multiple letters of the same target is fine.
   - Actually: spawn using indices `nextLetterIndex, nextLetterIndex+1, nextLetterIndex+2...` up to `MAX_LETTERS_ON_BOARD` distinct letters. Track how many you've spawned vs how many slots remain.
   - Simplest correct implementation: call `spawnLetter` in a while loop passing `nextLetterIndex` each time (duplicates allowed on board). Stop when `food.length >= MAX_LETTERS_ON_BOARD`.
9. Return `filledState`.

---

### ACCEPTANCE CRITERIA CHECKLIST
Before finishing, verify:
- [ ] `types.ts` exports exactly: `Position`, `Direction`, `LetterFood`, `Snake`, `Difficulty`, `GameStatus`, `GameState`
- [ ] `constants.ts` exports exactly: `GRID_SIZE`, `CELL_SIZE`, `INITIAL_SNAKE_LENGTH`, `SPEEDS`, `SPEED_INCREASE_INTERVAL`, `SPEED_INCREASE_AMOUNT`, `MAX_LETTERS_ON_BOARD`, `TOTAL_LIVES`, `LETTER_COLORS` (length 26), `ALPHABET` (length 26)
- [ ] `engine.ts` exports exactly: `createInitialState`, `moveSnake`, `checkCollisions`, `checkLetterEaten`, `spawnLetter`, `tick`, `getSpeed`
- [ ] No `enum` keyword anywhere
- [ ] No `import React` or any react imports in any of the three files
- [ ] `import type` used for type-only imports in engine.ts
- [ ] Run `npm run build` from `projects/abc-snake/` — must exit 0 with no TypeScript errors

### STOP CONDITION
Stop after `npm run build` exits 0 from `projects/abc-snake/`. Do not add React components or tests.
