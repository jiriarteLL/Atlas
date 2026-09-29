import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'dist_nuevo', 'dist_viejo', '_archivo_versiones_viejas']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
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
])
