import { defineConfig } from 'vite';

const repository = process.env.GITHUB_REPOSITORY?.split('/')[1];
const base = process.env.VITE_BASE_PATH || (repository ? `/${repository}/` : '/');

export default defineConfig({ base });
