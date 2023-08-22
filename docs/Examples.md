# Examples

## Scanning a single directory for malware

A basic example of recursively scanning the `/var/www` directory and writing the results to `/home/wordfence/wordfence-cli.csv`. 

	wordfence scan --output-path /home/wordfence/wordfence-cli.csv /var/www

## Running Wordfence CLI in a cron

Run Wordfence CLI in a cron job daily to scan `/var/www` and write the results to `/home/wordfence/wordfence-cli.csv`. This would be similar to how a scheduled scan works within the Wordfence plugin.

	0 0 * * *  wordfence /usr/bin/flock -w 0 /home/wordfence/wordfence-cli.lock /home/wordfence/wordfence scan --output-path /home/wordfence/wordfence-cli.csv /var/www; /usr/bin/rm /home/wordfence/wordfence-cli.lock

The cronjob uses a lock file at `/home/wordfence/wordfence-cli.lock` to prevent duplicate scans from running at the same time.

## Piping files from `find` to Wordfence CLI

Find files under the directory `/var/www/` that have changed in the last hour and scan them with Wordfence CLI:

	find /var/www/ -cmin -60 -type f -print0 | wordfence scan --output-path /home/wordfence/wordfence-cli.csv

We recommend that you use `ctime` over `mtime` and `atime` as changing the `ctime` of a file requires root access to the file system. `mtime` and `atime` can be arbitrarily set by the file owner using the `touch` command.
