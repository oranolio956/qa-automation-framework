import type { Config } from 'jest';

const config: Config = {
  testEnvironment: 'node',
  transform: {},
  testMatch: ['**/__tests__/**/*.test.ts']
};

export default config;

