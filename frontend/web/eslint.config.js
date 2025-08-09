import js from '@eslint/js';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import reactHooks from 'eslint-plugin-react-hooks';

// Compose flat config manually using plugin's published flat config presets
// We intentionally do NOT import from an uninstalled 'typescript-eslint' meta package.

export default [
  // Apply JS + base TS to source files only so config file itself isn't parsed with type-aware rules
  {
    files: ['src/**/*.{js,ts,tsx}'],
    ...js.configs.recommended,
  },
  ...tsPlugin.configs['flat/recommended'].map((c) => ({ ...c, files: ['src/**/*.{ts,tsx}'] })),
  ...tsPlugin.configs['flat/strict-type-checked'].map((c) => ({
    ...c,
    files: ['src/**/*.{ts,tsx}'],
  })),
  ...tsPlugin.configs['flat/stylistic-type-checked'].map((c) => ({
    ...c,
    files: ['src/**/*.{ts,tsx}'],
  })),
  {
    files: ['src/**/*.{ts,tsx}'],
    ignores: ['dist/**', 'eslint.config.js', 'vite.config.*', 'tsconfig*.json'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        project: ['./tsconfig.eslint.json'],
        tsconfigRootDir: new URL('.', import.meta.url),
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
      'react-hooks': reactHooks,
    },
    rules: {
      // React hooks
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      // TS prefs
      '@typescript-eslint/consistent-type-imports': 'warn',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },
  // Turn off stylistic rules conflicting with Prettier
  {
    files: ['src/**/*.{ts,tsx,js,jsx}'],
    rules: {
      // relying on Prettier for formatting
      'max-len': 'off',
    },
  },
];
