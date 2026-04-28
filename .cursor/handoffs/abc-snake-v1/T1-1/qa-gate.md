# QA Gate — T1-1: Game Engine Core

**handoff_id:** `abc-snake-v1`
**task_id:** `T1-1`
**date:** 2026-04-28

---

```
GATE_RESULTS
  handoff_id: "abc-snake-v1"
  verdict: PASS
  acceptance_criteria:
    - criterion: "types.ts exports: Position, Direction, LetterFood, Snake, Difficulty, GameStatus, GameState"
      status: PASS
      covering_tests:
        - "src/game/engine.test.ts::AC1: types.ts exports > Position is a shape with x and y"
        - "src/game/engine.test.ts::AC1: types.ts exports > Direction accepts all four directions"
        - "src/game/engine.test.ts::AC1: types.ts exports > LetterFood has letter, position, color"
        - "src/game/engine.test.ts::AC1: types.ts exports > Snake has body and direction"
        - "src/game/engine.test.ts::AC1: types.ts exports > Difficulty accepts EASY | MEDIUM | HARD"
        - "src/game/engine.test.ts::AC1: types.ts exports > GameStatus accepts IDLE | PLAYING | PAUSED | GAME_OVER | WIN"
        - "src/game/engine.test.ts::AC1: types.ts exports > GameState has all required fields"
      run_result: "pass — 7/7 tests green"

    - criterion: "constants.ts exports: GRID_SIZE, CELL_SIZE, INITIAL_SNAKE_LENGTH, SPEEDS, SPEED_INCREASE_INTERVAL, SPEED_INCREASE_AMOUNT, MAX_LETTERS_ON_BOARD, TOTAL_LIVES, LETTER_COLORS (26 colors), ALPHABET"
      status: PASS
      covering_tests:
        - "src/game/engine.test.ts::AC2: constants.ts exports > GRID_SIZE is a number"
        - "src/game/engine.test.ts::AC2: constants.ts exports > CELL_SIZE is a number"
        - "src/game/engine.test.ts::AC2: constants.ts exports > INITIAL_SNAKE_LENGTH is a positive number"
        - "src/game/engine.test.ts::AC2: constants.ts exports > SPEEDS has EASY, MEDIUM, HARD entries"
        - "src/game/engine.test.ts::AC2: constants.ts exports > SPEED_INCREASE_INTERVAL and SPEED_INCREASE_AMOUNT are positive"
        - "src/game/engine.test.ts::AC2: constants.ts exports > MAX_LETTERS_ON_BOARD is a positive number"
        - "src/game/engine.test.ts::AC2: constants.ts exports > TOTAL_LIVES is a positive number"
        - "src/game/engine.test.ts::AC2: constants.ts exports > LETTER_COLORS has exactly 26 entries"
        - "src/game/engine.test.ts::AC2: constants.ts exports > ALPHABET has exactly 26 uppercase letters A-Z"
      run_result: "pass — 9/9 tests green; LETTER_COLORS has 26 entries each matching /^#[0-9A-Fa-f]{6}$/"

    - criterion: "engine.ts exports pure functions: createInitialState, moveSnake, checkCollisions, checkLetterEaten, spawnLetter, tick, getSpeed"
      status: PASS
      covering_tests:
        - "src/game/engine.test.ts::AC3: engine.ts exports > createInitialState returns valid GameState"
        - "src/game/engine.test.ts::AC3: engine.ts exports > moveSnake moves head forward in direction"
        - "src/game/engine.test.ts::AC3: engine.ts exports > moveSnake grows when grow=true"
        - "src/game/engine.test.ts::AC3: engine.ts exports > checkCollisions returns false for valid snake"
        - "src/game/engine.test.ts::AC3: engine.ts exports > checkCollisions returns true for wall hit"
        - "src/game/engine.test.ts::AC3: engine.ts exports > checkCollisions returns true for self collision"
        - "src/game/engine.test.ts::AC3: engine.ts exports > checkLetterEaten returns null when not on any letter"
        - "src/game/engine.test.ts::AC3: engine.ts exports > checkLetterEaten returns letter when head matches correct letter"
        - "src/game/engine.test.ts::AC3: engine.ts exports > checkLetterEaten returns null for wrong letter (out-of-order)"
        - "src/game/engine.test.ts::AC3: engine.ts exports > spawnLetter returns a LetterFood with correct letter and color"
        - "src/game/engine.test.ts::AC3: engine.ts exports > spawnLetter avoids occupied cells"
        - "src/game/engine.test.ts::AC3: engine.ts exports > getSpeed decreases as letters eaten increase"
        - "src/game/engine.test.ts::AC3: engine.ts exports > getSpeed floors at 50ms"
        - "src/game/engine.test.ts::AC3: engine.ts exports > tick does nothing when status is not PLAYING"
        - "src/game/engine.test.ts::AC3: engine.ts exports > tick advances the snake forward"
        - "src/game/engine.test.ts::AC3: engine.ts exports > tick detects wall collision and decrements lives"
        - "src/game/engine.test.ts::AC3: engine.ts exports > tick sets WIN when last letter eaten"
      run_result: "pass — 17/17 tests green"

    - criterion: "All functions pure (randomness via parameter)"
      status: PASS
      covering_tests:
        - "src/game/engine.test.ts::AC4: functions are pure > createInitialState is deterministic with fixed random"
        - "src/game/engine.test.ts::AC4: functions are pure > spawnLetter is deterministic with fixed random"
        - "src/game/engine.test.ts::AC4: functions are pure > tick is deterministic with fixed random"
        - "src/game/engine.test.ts::AC4: functions are pure > moveSnake does not mutate input"
      run_result: "pass — 4/4 determinism + no-mutation tests green; code inspection confirms no global writes"

    - criterion: "npm run build passes with no type errors"
      status: PASS
      covering_tests:
        - "src/game/engine.test.ts::AC5: TypeScript build compatibility > all imports resolve without runtime errors"
      run_result: "pass — `npm run build` (tsc -b && vite build) exited 0; 16 modules transformed; no TS errors"

  iterations: 0
  regression_checked: true
  remaining_gaps: []
  notes: "All 38 vitest tests passed on first run (0 iterations). Build exited 0. Static checks confirmed: no enums anywhere in game/ (rg found none), no React imports in game/ files, LETTER_COLORS has 26 hex-color entries, ALPHABET is A-Z. The implementation adds a `pendingGrow: boolean` field to GameState beyond the spec minimum — this is additive and does not violate any AC."
END_GATE_RESULTS
```

## Evidence

| Check | Result |
|---|---|
| `types.ts` file exists | ✓ |
| `constants.ts` file exists | ✓ |
| `engine.ts` file exists | ✓ |
| No enums in `game/` (`rg "^enum "`) | ✓ NO_ENUMS |
| No React imports in `game/` | ✓ NO_REACT |
| `npm run build` exit code | ✓ 0 |
| Vitest suite (38 tests) | ✓ 38/38 PASS |
| Test file written | `src/game/engine.test.ts` |
