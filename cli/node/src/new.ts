import { mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import kleur from 'kleur';

interface NewOptions {
  template: string;
  dir?: string;
}

const TEMPLATES_ROOT = fileURLToPath(new URL('../../templates', import.meta.url));

export async function newCommand(name: string, opts: NewOptions): Promise<void> {
  if (!/^[a-z0-9][a-z0-9-]{2,49}$/.test(name)) {
    console.error(kleur.red(`✗ Nombre inválido: debe matchear ^[a-z0-9][a-z0-9-]{2,49}$`));
    process.exit(1);
  }

  const templateDir = path.join(TEMPLATES_ROOT, opts.template);
  try {
    await stat(templateDir);
  } catch {
    console.error(kleur.red(`✗ Template no encontrado: ${opts.template}`));
    console.error(kleur.gray(`  Esperado en: ${templateDir}`));
    process.exit(1);
  }

  const destDir = path.resolve(process.cwd(), opts.dir ?? name);
  try {
    await stat(destDir);
    console.error(kleur.red(`✗ El directorio destino ya existe: ${destDir}`));
    process.exit(1);
  } catch {
    // esperado
  }

  console.log(kleur.cyan(`→ Generando ${kleur.bold(name)} en ${destDir}`));

  await copyTemplateDir(templateDir, destDir, {
    APP_NAME: name,
    APP_VERSION: '0.1.0',
  });

  console.log(kleur.green('\n✓ Proyecto creado con éxito.'));
  console.log(kleur.gray('\nPróximos pasos:'));
  console.log(kleur.gray(`  cd ${path.relative(process.cwd(), destDir)}`));
  console.log(kleur.gray('  npm install'));
  console.log(kleur.gray('  maestro-cli validate'));
}

async function copyTemplateDir(
  src: string,
  dest: string,
  substitutions: Record<string, string>,
): Promise<void> {
  await mkdir(dest, { recursive: true });
  const entries = await readdir(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destName = applySubstitutions(entry.name, substitutions);
    const destPath = path.join(dest, destName);

    if (entry.isDirectory()) {
      await copyTemplateDir(srcPath, destPath, substitutions);
    } else {
      const content = await readFile(srcPath, 'utf-8');
      await writeFile(destPath, applySubstitutions(content, substitutions), 'utf-8');
    }
  }
}

function applySubstitutions(input: string, subs: Record<string, string>): string {
  return Object.entries(subs).reduce(
    (acc, [k, v]) => acc.replaceAll(`{{${k}}}`, v),
    input,
  );
}
