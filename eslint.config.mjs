import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["node_modules/**", ".expo/**", "**/.venv/**", "babel.config.js"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: { globals: { __DEV__: "readonly", process: "readonly", console: "readonly", fetch: "readonly", AbortController: "readonly", setTimeout: "readonly", clearTimeout: "readonly", setInterval: "readonly", clearInterval: "readonly" } },
    rules: { "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }] }
  }
);
