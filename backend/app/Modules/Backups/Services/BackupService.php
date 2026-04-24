<?php

declare(strict_types=1);

namespace App\Modules\Backups\Services;

use App\Models\Instance;
use App\Modules\AuditLog\Services\AuditLogger;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\Storage;
use Symfony\Component\Process\Process;

/**
 * Servicio de backups cifrados (RF-110/111/112 + RNF-030).
 *
 * Estrategia:
 *   - pg_dump de cada BD (Maestro + cada instancia) → gzip → cifrado AES-256-CBC → Azure Blob / local.
 *   - Frecuencia: diaria (configurable vía env BACKUP_SCHEDULE).
 *   - Retención: 30 días (DEC-019). Los backups más antiguos se purgan en el job.
 *   - Pre-migración: snapshot adicional tag "pre-migration-<timestamp>" antes de cada artisan migrate en prod.
 */
class BackupService
{
    public function __construct(private readonly AuditLogger $audit) {}

    public function backupMaestroDb(): string
    {
        return $this->dumpAndStore(
            host: (string) config('database.connections.pgsql.host'),
            port: (int) config('database.connections.pgsql.port'),
            database: (string) config('database.connections.pgsql.database'),
            user: (string) config('database.connections.pgsql.username'),
            password: (string) config('database.connections.pgsql.password'),
            filename: 'maestro-'.now()->format('Y-m-d-His').'.sql.gz.enc',
        );
    }

    public function backupInstanceDb(Instance $instance): ?string
    {
        if (! $instance->db_password_encrypted || ! $instance->db_host || ! $instance->db_name) {
            return null;
        }

        $password = Crypt::decryptString($instance->db_password_encrypted);
        $filename = "instance-{$instance->application->slug}-{$instance->company->slug}-".now()->format('Y-m-d-His').'.sql.gz.enc';

        return $this->dumpAndStore(
            host: $instance->db_host,
            port: 5432,
            database: $instance->db_name,
            user: $instance->db_user,
            password: $password,
            filename: $filename,
        );
    }

    /**
     * Purga backups más viejos que la retención mínima (DEC-019: 30 días).
     */
    public function purgeOldBackups(int $retentionDays = 30): int
    {
        $disk = $this->disk();
        $cutoff = now()->subDays($retentionDays)->timestamp;
        $removed = 0;

        foreach ($disk->files() as $path) {
            if ($disk->lastModified($path) < $cutoff) {
                $disk->delete($path);
                $removed++;
            }
        }

        return $removed;
    }

    private function dumpAndStore(
        string $host, int $port, string $database, string $user, string $password, string $filename,
    ): string {
        $tmp = sys_get_temp_dir()."/{$filename}.tmp";

        // pg_dump | gzip | openssl enc
        $cmd = sprintf(
            'PGPASSWORD=%s pg_dump -h %s -p %d -U %s -F c -Z 6 %s | openssl enc -aes-256-cbc -salt -pbkdf2 -pass pass:%s -out %s',
            escapeshellarg($password),
            escapeshellarg($host),
            $port,
            escapeshellarg($user),
            escapeshellarg($database),
            escapeshellarg($this->encryptionKey()),
            escapeshellarg($tmp),
        );

        $process = Process::fromShellCommandline($cmd, timeout: 3600);
        $process->run();

        if (! $process->isSuccessful() || ! file_exists($tmp)) {
            $this->audit->log('backup.failed', dataAfter: [
                'database' => $database,
                'stderr' => substr($process->getErrorOutput(), 0, 500),
            ]);
            throw new \RuntimeException("Backup failed for {$database}: ".$process->getErrorOutput());
        }

        $disk = $this->disk();
        $disk->put($filename, file_get_contents($tmp));
        @unlink($tmp);

        $this->audit->log('backup.success', dataAfter: [
            'database' => $database,
            'filename' => $filename,
            'size_bytes' => $disk->size($filename),
        ]);

        return $filename;
    }

    private function disk(): \Illuminate\Contracts\Filesystem\Filesystem
    {
        // Azure Blob si el driver está registrado; sino fallback a local (dev/test sin league/flysystem-azure).
        $storageAccount = env('AZURE_STORAGE_ACCOUNT');
        if ($storageAccount) {
            try {
                return Storage::build([
                    'driver' => 'azure',
                    'account' => $storageAccount,
                    'key' => env('AZURE_STORAGE_KEY'),
                    'container' => env('AZURE_STORAGE_CONTAINER', 'maestro-backups'),
                    'endpoint' => env('AZURE_STORAGE_ENDPOINT'),
                ]);
            } catch (\InvalidArgumentException $e) {
                // Driver no registrado: fallback silencioso a local. En prod el driver debe estar.
            }
        }
        return Storage::build([
            'driver' => 'local',
            'root' => storage_path('app/backups'),
        ]);
    }

    private function encryptionKey(): string
    {
        $key = (string) env('BACKUP_ENCRYPTION_KEY');
        if (! $key) {
            throw new \RuntimeException('BACKUP_ENCRYPTION_KEY no configurada en .env');
        }
        return $key;
    }
}
