#!/usr/bin/env node
import { Command } from 'commander';
import { validateCommand } from './validate.js';
import { newCommand } from './new.js';

const program = new Command();

program
  .name('maestro-cli')
  .description('CLI oficial de Maestro Platform para desarrolladores de apps huésped.')
  .version('0.1.0-dev');

program
  .command('validate')
  .description('Valida el contrato maestro.yaml contra el JSON Schema oficial.')
  .option('-f, --file <path>', 'Ruta al archivo maestro.yaml', 'maestro.yaml')
  .action(validateCommand);

program
  .command('new <name>')
  .description('Genera un scaffold de app huésped compatible con Maestro.')
  .option('-t, --template <name>', 'Template a usar', 'node-express')
  .option('-d, --dir <path>', 'Directorio destino (default: ./<name>)')
  .action(newCommand);

program.parse();
