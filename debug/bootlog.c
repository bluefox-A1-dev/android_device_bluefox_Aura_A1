/* SPDX-FileCopyrightText: 2026 The LineageOS Project
 * SPDX-License-Identifier: Apache-2.0 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#define LOG_DIR "aura-bootlogs"
#define RESERVE_BYTES (16ULL * 1024 * 1024)
#define BUFFER_SIZE (1024 * 1024)
#define KMSG_LIMIT (2 * 1024 * 1024)
#define INIT_LIMIT (512 * 1024)
#define STATUS_LIMIT (64 * 1024)

/* Separate files for the bootstrap and managed daemon; keep one previous boot
 * and one within-boot rotation. Maximum log content is below 21 MiB. */
static const char *files[] = {"early-kmsg.log", "early-init.log", "kmsg.log", "init.log",
                              "early-status.log", "status.log"};
static char pending[BUFFER_SIZE];
static char record[65537];

static int write_all(int fd, const void *data, size_t len) {
    const char *p = data;
    while (len) {
        ssize_t n = write(fd, p, len);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return -1;
        p += n;
        len -= (size_t)n;
    }
    return 0;
}

static int status_message(int fd, const char *format, ...) {
    char line[512];
    va_list args;
    va_start(args, format);
    int n = vsnprintf(line, sizeof(line), format, args);
    va_end(args);
    if (n <= 0) { errno = EIO; return -1; }
    size_t len = (size_t)n < sizeof(line) ? (size_t)n : sizeof(line) - 1;
    if (fd != STDERR_FILENO) {
        struct stat st;
        if (fstat(fd, &st)) return -1;
        if (st.st_size < 0 || (unsigned long long)st.st_size + len > STATUS_LIMIT) return 0;
    }
    /* Best effort: a filesystem failure or SELinux may also block this write. */
    if (write_all(fd, line, len)) return -1;
    return fd == STDERR_FILENO ? 0 : fdatasync(fd);
}

static void pause_poll(void) {
    struct timespec t = {.tv_sec = 0, .tv_nsec = 50000000};
    while (nanosleep(&t, &t) && errno == EINTR) {}
}

static int metadata_fd(int procfd, int early) {
    /* The parent may switch root. A pinned proc directory follows PID1's current
     * root, rather than the child's obsolete ramdisk root. */
    int fd = early ? openat(procfd, "1/root/metadata", O_RDONLY | O_DIRECTORY | O_CLOEXEC)
                   : open("/metadata", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (fd < 0) return -1;
    struct statfs st;
    if (fstatfs(fd, &st) || ((unsigned long)st.f_type != 0xef53UL &&
                           (unsigned long)st.f_type != 0xf2f52010UL)) {
        close(fd);
        return -1;
    }
    return fd;
}

static int enough_space(int fd) {
    struct statfs st;
    return !fstatfs(fd, &st) &&
           (unsigned long long)st.f_bavail * (unsigned long long)st.f_bsize >= RESERVE_BYTES;
}

static int log_directory(int meta, const char *id) {
    if (!enough_space(meta)) { errno = ENOSPC; return -1; }
    if (mkdirat(meta, LOG_DIR, 0700) && errno != EEXIST) return -1;
    int dir = openat(meta, LOG_DIR, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (dir < 0) return -1;
    int lock = openat(dir, "lock", O_CREAT | O_RDWR | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (lock < 0 || flock(lock, LOCK_EX)) {
        if (lock >= 0) close(lock);
        close(dir);
        return -1;
    }
    char previous[80] = {0};
    int marker = openat(dir, "boot-id", O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (marker >= 0) {
        ssize_t ignored = read(marker, previous, sizeof(previous) - 1);
        (void)ignored;
        close(marker);
    }
    if (strcmp(previous, id)) {
        for (size_t i = 0; i < sizeof(files) / sizeof(files[0]); ++i) {
            char old[64], rotated[64], rotated_old[64];
            snprintf(old, sizeof(old), "%s.prev", files[i]);
            snprintf(rotated, sizeof(rotated), "%s.1", files[i]);
            snprintf(rotated_old, sizeof(rotated_old), "%s.1.prev", files[i]);
            unlinkat(dir, old, 0);
            unlinkat(dir, rotated_old, 0);
            renameat(dir, files[i], dir, old);
            renameat(dir, rotated, dir, rotated_old);
        }
        marker = openat(dir, "boot-id", O_CREAT | O_TRUNC | O_WRONLY | O_NOFOLLOW | O_CLOEXEC | O_DSYNC, 0600);
        if (marker < 0 || write_all(marker, id, strlen(id))) {
            if (marker >= 0) close(marker);
            close(lock);
            close(dir);
            return -1;
        }
        close(marker);
        fsync(dir);
    }
    close(lock);
    return dir;
}

static int append_record(int dir, const char *name, const char *data, size_t len, size_t limit) {
    if (!enough_space(dir)) { errno = ENOSPC; return -1; }
    struct stat st;
    if (!fstatat(dir, name, &st, AT_SYMLINK_NOFOLLOW) &&
        (unsigned long long)st.st_size + len > limit) {
        char rotated[64];
        snprintf(rotated, sizeof(rotated), "%s.1", name);
        unlinkat(dir, rotated, 0);
        if (renameat(dir, name, dir, rotated)) return -1;
        fsync(dir);
    }
    int fd = openat(dir, name, O_CREAT | O_APPEND | O_WRONLY | O_NOFOLLOW | O_CLOEXEC | O_DSYNC, 0600);
    if (fd < 0) return -1;
    int rc = write_all(fd, data, len);
    if (!rc) rc = fdatasync(fd);
    int saved_errno = errno;
    close(fd);
    if (rc) errno = saved_errno;
    return rc;
}

static int save_record(int dir, int early, const char *record, size_t len) {
    if (append_record(dir, files[early ? 0 : 2], record, len, KMSG_LIMIT)) return -1;
    if (strstr(record, "init:") || strstr(record, "init first stage") ||
        strstr(record, "scontext=u:r:init")) {
        if (append_record(dir, files[early ? 1 : 3], record, len, INIT_LIMIT)) return -1;
    }
    return 0;
}

static int collect(int early) {
    int proc = -1, kmsg = -1, dir = -1, status = -1;
    int exit_error = 0, open_error = 0;
    const char *reason = "timeout";
    char id[80] = {0};
    size_t buffered = 0;
    unsigned long long records = 0, bytes = 0, overruns = 0, dropped = 0;
    time_t last_status = -5;
    struct timespec start, now;
    clock_gettime(CLOCK_MONOTONIC, &start);
    for (;;) {
        clock_gettime(CLOCK_MONOTONIC, &now);
        if (early && now.tv_sec - start.tv_sec >= 120) break;
        if (proc < 0) {
            int candidate = open("/proc", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
            if (candidate >= 0) {
                struct statfs st;
                /* PID1 has not necessarily mounted procfs yet. Pinning the
                 * empty ramdisk directory would hide that later mount forever,
                 * preventing both boot-id reads and following PID1's root. */
                if (!fstatfs(candidate, &st) && (unsigned long)st.f_type == 0x9fa0UL) {
                    proc = candidate;
                } else {
                    close(candidate);
                }
            }
        }
        if (proc >= 0 && !id[0]) {
            int fd = openat(proc, "sys/kernel/random/boot_id", O_RDONLY | O_CLOEXEC);
            if (fd >= 0) {
                ssize_t n = read(fd, id, sizeof(id) - 1);
                if (n > 0) id[n] = 0;
                close(fd);
            }
        }
        if (kmsg < 0) {
            kmsg = open("/dev/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
            if (kmsg >= 0) lseek(kmsg, 0, SEEK_SET);
            open_error = kmsg < 0 ? errno : 0;
        }
        if (dir < 0 && id[0] && (!early || proc >= 0)) {
            int meta = metadata_fd(proc, early);
            if (meta >= 0) {
                dir = log_directory(meta, id);
                close(meta);
            }
            if (dir >= 0) {
                /* Keep this descriptor open so reporting a later openat failure
                 * does not depend on opening another file. SELinux can still
                 * deny writes to an existing descriptor. */
                status = openat(dir, files[early ? 4 : 5],
                                O_CREAT | O_APPEND | O_WRONLY | O_NOFOLLOW | O_CLOEXEC | O_DSYNC,
                                0600);
                if (status < 0) {
                    reason = "open-status"; exit_error = errno; goto done;
                }
                if (status_message(status, "start phase=%s pid=%ld boot-id=%sbuffered=%zu\n",
                                   early ? "early" : "init-service", (long)getpid(), id, buffered)) {
                    reason = "write-status"; exit_error = errno; goto done;
                }
                if (fsync(dir)) {
                    reason = "sync-directory"; exit_error = errno; goto done;
                }
                char header[160];
                int n = snprintf(header, sizeof(header), "# Aura bootlog phase=%s pid=%ld boot-id=%s",
                                 early ? "early" : "init-service", (long)getpid(), id);
                if (save_record(dir, early, header, (size_t)n)) {
                    reason = "write-header"; exit_error = errno; goto done;
                }
                size_t pos = 0;
                while (pos < buffered) {
                    char *end = memchr(pending + pos, '\n', buffered - pos);
                    size_t count = end ? (size_t)(end - pending - pos) + 1 : buffered - pos;
                    char saved = pending[pos + count];
                    pending[pos + count] = 0;
                    int rc = save_record(dir, early, pending + pos, count);
                    pending[pos + count] = saved;
                    if (rc) {
                        reason = "flush-buffer"; exit_error = errno; goto done;
                    }
                    pos += count;
                }
                buffered = 0;
                if (fsync(dir)) {
                    reason = "sync-directory"; exit_error = errno; goto done;
                }
                if (status_message(status, "buffer-flushed elapsed=%ld\n", (long)(now.tv_sec - start.tv_sec))) {
                    reason = "write-status"; exit_error = errno; goto done;
                }
            }
        }
        if (status >= 0 && now.tv_sec - start.tv_sec - last_status >= 5) {
            last_status = now.tv_sec - start.tv_sec;
            if (fsync(dir)) {
                reason = "sync-directory"; exit_error = errno; goto done;
            }
            if (status_message(status, "running elapsed=%ld records=%llu bytes=%llu overruns=%llu dropped=%llu kmsg_open_errno=%d\n",
                               (long)last_status, records, bytes, overruns, dropped, open_error)) {
                reason = "write-status"; exit_error = errno; goto done;
            }
        }
        if (kmsg >= 0) {
            ssize_t n = read(kmsg, record, sizeof(record) - 1);
            if (n > 0) {
                ++records;
                bytes += (unsigned long long)n;
                record[n] = 0;
                if (dir >= 0) {
                    if (save_record(dir, early, record, (size_t)n)) {
                        reason = "write-record"; exit_error = errno; goto done;
                    }
                } else {
                    if (buffered + (size_t)n >= sizeof(pending)) {
                        char *cut = memchr(pending + buffered / 2, '\n', buffered - buffered / 2);
                        size_t drop = cut ? (size_t)(cut - pending) + 1 : buffered;
                        dropped += drop;
                        memmove(pending, pending + drop, buffered - drop);
                        buffered -= drop;
                    }
                    memcpy(pending + buffered, record, (size_t)n);
                    buffered += (size_t)n;
                    pending[buffered] = 0;
                }
                continue;
            }
            if (n < 0 && errno == EPIPE) { ++overruns; continue; }
            if (n < 0 && errno != EAGAIN && errno != EINTR) {
                reason = "read-kmsg"; exit_error = errno; goto done;
            }
        }
        pause_poll();
    }
done:
    clock_gettime(CLOCK_MONOTONIC, &now);
    status_message(status >= 0 ? status : STDERR_FILENO,
            "exit reason=%s errno=%d (%s) elapsed=%ld records=%llu bytes=%llu buffered=%zu overruns=%llu dropped=%llu kmsg_open_errno=%d\n",
            reason, exit_error, exit_error ? strerror(exit_error) : "none",
            (long)(now.tv_sec - start.tv_sec), records, bytes, buffered, overruns, dropped, open_error);
    if (dir >= 0) fsync(dir);
    if (status >= 0) close(status);
    if (dir >= 0) close(dir);
    if (kmsg >= 0) close(kmsg);
    if (proc >= 0) close(proc);
    return exit_error ? 1 : 0;
}

int main(int argc, char **argv) {
    (void)argc;
#ifdef AURA_INIT_WRAPPER
    if (getpid() != 1) return 1;
    pid_t child = fork();
    if (child == 0) _exit(collect(1));
    /* No wait: the real init remains PID1, including when fork failed. */
    execv("/init.aura.real", argv);
    _exit(127);
#else
    (void)argv;
    return collect(0);
#endif
}
