// Position on the grid (0-indexed)
export type Position = { x: number; y: number };

// Four movement directions
export type Direction = 'UP' | 'DOWN' | 'LEFT' | 'RIGHT';

// A letter food item on the board
export type LetterFood = {
  position: Position;
  letter: string; // single uppercase letter e.g. 'A'
  letterIndex: number; // 0-25
  color: string; // hex color from LETTER_COLORS
};

// The snake: head is index 0, tail is last element
export type Snake = {
  segments: Position[]; // head-first array
  direction: Direction;
};

// Game difficulty affects speed
export type Difficulty = 'easy' | 'medium' | 'hard';

// Game lifecycle state
export type GameStatus = 'idle' | 'playing' | 'paused' | 'won' | 'lost';

// Complete game state — everything needed to render one frame
export type GameState = {
  snake: Snake;
  food: LetterFood[]; // letters currently on board
  nextLetterIndex: number; // 0-25, index of the next letter to eat
  score: number;
  lives: number;
  difficulty: Difficulty;
  status: GameStatus;
  tickCount: number; // increments each tick, used for speed ramping
  currentSpeed: number; // ms per tick
};
