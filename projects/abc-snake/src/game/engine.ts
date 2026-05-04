import type {
  Difficulty,
  Direction,
  GameState,
  GameStatus,
  LetterFood,
  Position,
  Snake,
} from './types.ts';
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

function computeNextHead(head: Position, direction: Direction): Position {
  let nx = head.x;
  let ny = head.y;
  switch (direction) {
    case 'UP':
      ny -= 1;
      break;
    case 'DOWN':
      ny += 1;
      break;
    case 'LEFT':
      nx -= 1;
      break;
    case 'RIGHT':
      nx += 1;
      break;
  }
  return {
    x: ((nx % GRID_SIZE) + GRID_SIZE) % GRID_SIZE,
    y: ((ny % GRID_SIZE) + GRID_SIZE) % GRID_SIZE,
  };
}

function createCenterSnake(): Snake {
  const cx = Math.floor(GRID_SIZE / 2);
  const cy = Math.floor(GRID_SIZE / 2);
  const segments: Position[] = [];
  for (let i = 0; i < INITIAL_SNAKE_LENGTH; i++) {
    segments.push({ x: cx - i, y: cy });
  }
  return { segments, direction: 'RIGHT' };
}

export function createInitialState(difficulty: Difficulty): GameState {
  return {
    snake: createCenterSnake(),
    food: [],
    nextLetterIndex: 0,
    score: 0,
    lives: TOTAL_LIVES,
    difficulty,
    status: 'idle',
    tickCount: 0,
    currentSpeed: SPEEDS[difficulty] ?? SPEEDS.easy,
  };
}

export function moveSnake(snake: Snake, grow: boolean): Snake {
  const head = snake.segments[0];
  if (!head) {
    return snake;
  }
  const newHead = computeNextHead(head, snake.direction);
  const extended = [newHead, ...snake.segments];
  const segments = grow ? extended : extended.slice(0, -1);
  return { ...snake, segments };
}

export function checkCollisions(snake: Snake): boolean {
  const head = snake.segments[0];
  if (!head) return false;
  for (let i = 1; i < snake.segments.length; i++) {
    const seg = snake.segments[i];
    if (seg && seg.x === head.x && seg.y === head.y) return true;
  }
  return false;
}

export function checkLetterEaten(
  snakeHead: Position,
  food: LetterFood[],
): LetterFood | null {
  for (const item of food) {
    if (item.position.x === snakeHead.x && item.position.y === snakeHead.y) {
      return item;
    }
  }
  return null;
}

export function spawnLetter(
  food: LetterFood[],
  snake: Snake,
  nextLetterIndex: number,
  random: () => number,
): LetterFood[] {
  if (food.length >= MAX_LETTERS_ON_BOARD) return food;

  const idx = ((nextLetterIndex % 26) + 26) % 26;
  const letter = ALPHABET[idx];
  const color = LETTER_COLORS[idx];
  if (letter === undefined || color === undefined) return food;

  const isOccupied = (x: number, y: number): boolean => {
    for (const s of snake.segments) {
      if (s.x === x && s.y === y) return true;
    }
    for (const f of food) {
      if (f.position.x === x && f.position.y === y) return true;
    }
    return false;
  };

  for (let attempt = 0; attempt < 100; attempt++) {
    const x = Math.floor(random() * GRID_SIZE);
    const y = Math.floor(random() * GRID_SIZE);
    if (isOccupied(x, y)) continue;
    const newLetter: LetterFood = {
      position: { x, y },
      letter,
      letterIndex: idx,
      color,
    };
    return [...food, newLetter];
  }
  return food;
}

export function getSpeed(difficulty: Difficulty, lettersEaten: number): number {
  const base = SPEEDS[difficulty] ?? SPEEDS.easy;
  const reduction =
    Math.floor(lettersEaten / SPEED_INCREASE_INTERVAL) * SPEED_INCREASE_AMOUNT;
  return Math.max(50, base - reduction);
}

export function tick(state: GameState, random: () => number): GameState {
  if (state.status !== 'playing') {
    return state;
  }

  const head = state.snake.segments[0];
  if (!head) {
    return state;
  }

  const newHead = computeNextHead(head, state.snake.direction);

  const eaten = checkLetterEaten(newHead, state.food);

  const grow =
    eaten !== null &&
    eaten.letter === ALPHABET[state.nextLetterIndex];

  const newSnake = moveSnake(state.snake, grow);

  const collided = checkCollisions(newSnake);

  let nextLetterIndex = state.nextLetterIndex;
  let score = state.score;
  let lives = state.lives;
  let status: GameStatus = state.status;
  let food: LetterFood[];
  let snakeOut: Snake;

  if (collided) {
    lives = state.lives - 1;
    if (lives <= 0) {
      status = 'lost';
    }
    snakeOut = createCenterSnake();
    food = [...state.food];
  } else if (
    eaten !== null &&
    eaten.letter === ALPHABET[state.nextLetterIndex]
  ) {
    snakeOut = newSnake;
    food = state.food.filter(
      (f) =>
        !(f.position.x === eaten.position.x && f.position.y === eaten.position.y),
    );
    nextLetterIndex = state.nextLetterIndex + 1;
    score = state.score + 10 * nextLetterIndex;
    if (nextLetterIndex === 26) {
      status = 'won';
    }
  } else if (eaten !== null) {
    snakeOut = newSnake;
    food = [...state.food];
    lives = state.lives - 1;
    if (lives <= 0) {
      status = 'lost';
    }
  } else {
    snakeOut = newSnake;
    food = [...state.food];
  }

  const tickCount = state.tickCount + 1;
  const currentSpeed = getSpeed(state.difficulty, nextLetterIndex);

  let foodFinal = food;
  while (foodFinal.length < MAX_LETTERS_ON_BOARD) {
    const lenBefore = foodFinal.length;
    foodFinal = spawnLetter(foodFinal, snakeOut, nextLetterIndex, random);
    if (foodFinal.length === lenBefore) break;
  }

  return {
    ...state,
    snake: snakeOut,
    food: foodFinal,
    nextLetterIndex,
    score,
    lives,
    status,
    tickCount,
    currentSpeed,
  };
}
