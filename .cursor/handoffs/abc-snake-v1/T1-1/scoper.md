# Scoper — T1-1: Game Engine Core

**handoff_id:** `abc-snake-v1`
**task_id:** `T1-1`

## SCOPE_SUMMARY
Implement the core game engine for the ABC Snake game: `types.ts` (all TypeScript types), `constants.ts` (grid, speeds, colors), `engine.ts` (pure functions for game logic). Key constraint: `erasableSyntaxOnly` in tsconfig forbids enums — use `as const` + type unions instead.

## SCOPE_PACKET

### Files to create
1. `projects/abc-snake/src/game/types.ts`
2. `projects/abc-snake/src/game/constants.ts`
3. `projects/abc-snake/src/game/engine.ts`

### Acceptance Criteria
1. `types.ts` exports: Position, Direction, LetterFood, Snake, Difficulty, GameStatus, GameState
2. `constants.ts` exports: GRID_SIZE, CELL_SIZE, INITIAL_SNAKE_LENGTH, SPEEDS, SPEED_INCREASE_INTERVAL, SPEED_INCREASE_AMOUNT, MAX_LETTERS_ON_BOARD, TOTAL_LIVES, LETTER_COLORS (26 colors), ALPHABET
3. `engine.ts` exports pure functions: createInitialState, moveSnake, checkCollisions, checkLetterEaten, spawnLetter, tick, getSpeed
4. All functions pure (randomness via parameter)
5. `npm run build` passes with no type errors

### Constraints
- No enums (erasableSyntaxOnly) — use `as const` unions
- No React imports in game/
- No side effects in engine.ts

## HANDOFF_TO_CURSOR_PILOT
Status: READY
