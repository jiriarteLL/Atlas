import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      // __APP_VERSION__ lo inyecta vite.config.js (define) desde package.json.
      globals: { ...globals.browser, __APP_VERSION__: 'readonly' },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // Las pantallas cargan datos al abrirse con el patron setCargando(true) + fetch dentro
      // del efecto. Es intencional y no genera renders en cascada en esta app.
      'react-hooks/set-state-in-effect': 'off',
      // Solo afecta la recarga en caliente del modo dev (aca siempre se compila); varios
      // archivos exportan componentes junto con helpers o constantes a proposito.
      'react-refresh/only-export-components': 'off',
    },
  },
  {
    // Configuracion de build: corre en Node, no en el navegador.
    files: ['vite.config.js', 'eslint.config.js'],
    languageOptions: { globals: globals.node },
  },
])
