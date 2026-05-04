export const GRID_SIZE = 20; // 20×20 grid cells
export const CELL_SIZE = 28; // pixels per cell (for rendering)
export const INITIAL_SNAKE_LENGTH = 3; // starting snake length

// Speed in milliseconds per tick per difficulty
export const SPEEDS: Record<string, number> = {
  easy: 200,
  medium: 140,
  hard: 90,
};

export const SPEED_INCREASE_INTERVAL = 5; // every N letters eaten, speed increases
export const SPEED_INCREASE_AMOUNT = 5; // ms reduction per speed step (minimum 50ms)
export const MAX_LETTERS_ON_BOARD = 4; // max simultaneous letters visible
export const TOTAL_LIVES = 3;

// 26 distinct colors for A–Z
export const LETTER_COLORS: string[] = [
  '#FF6B6B',
  '#FF8E53',
  '#FFA500',
  '#FFD93D',
  '#6BCB77',
  '#4D96FF',
  '#845EC2',
  '#FF6F91',
  '#00C9A7',
  '#C34A36',
  '#FF9671',
  '#00B8D9',
  '#B39CD0',
  '#F9F871',
  '#C4FCEF',
  '#FF6060',
  '#52B4F3',
  '#E8A838',
  '#45B7D1',
  '#96CEB4',
  '#DDA0DD',
  '#20B2AA',
  '#F0E68C',
  '#DB7093',
  '#3CB371',
  '#9370DB',
];

// All 26 letters in order
export const ALPHABET: string[] = Array.from({ length: 26 }, (_, i) =>
  String.fromCharCode(65 + i),
);
