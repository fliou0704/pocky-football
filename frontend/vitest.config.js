import { defineConfig } from 'vitest/config';
// Bound jsdom concurrency so real-data expandable tables do not compete for every core.
export default defineConfig({test:{environment:'jsdom',include:['src/*.test.jsx'],maxWorkers:2}});
