import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import { parse as parseYaml } from 'yaml';
import kleur from 'kleur';

interface ValidateOptions {
  file: string;
}

// Schema embebido: el CLI distribuye su propio snapshot del JSON Schema.
// En producción se podría fetchear del Maestro si se quiere versioning dinámico.
const SCHEMA_URL = new URL('../../../docs/schemas/maestro.yaml.schema.json', import.meta.url);

export async function validateCommand(opts: ValidateOptions): Promise<void> {
  const yamlPath = path.resolve(process.cwd(), opts.file);

  let yamlContent: string;
  try {
    yamlContent = await readFile(yamlPath, 'utf-8');
  } catch (err) {
    console.error(kleur.red(`✗ No se pudo leer ${yamlPath}`));
    console.error(String(err));
    process.exit(1);
  }

  let doc: unknown;
  try {
    doc = parseYaml(yamlContent);
  } catch (err) {
    console.error(kleur.red('✗ maestro.yaml no es YAML válido:'));
    console.error(String(err));
    process.exit(1);
  }

  let schemaJson: string;
  try {
    schemaJson = await readFile(fileURLToPath(SCHEMA_URL), 'utf-8');
  } catch {
    console.error(kleur.red('✗ No se encontró el JSON Schema. Reinstalar maestro-cli.'));
    process.exit(1);
  }
  const schema = JSON.parse(schemaJson);

  const ajv = new Ajv({ allErrors: true, strict: false });
  addFormats(ajv);
  const validate = ajv.compile(schema);

  if (validate(doc)) {
    console.log(kleur.green('✓ maestro.yaml es válido.'));
    process.exit(0);
  }

  console.error(kleur.red('✗ maestro.yaml no pasa la validación:'));
  for (const err of validate.errors ?? []) {
    console.error(`  ${kleur.yellow(err.instancePath || '/')} ${err.message ?? ''}`);
    if (err.params) {
      console.error(`    ${kleur.gray(JSON.stringify(err.params))}`);
    }
  }
  process.exit(1);
}
