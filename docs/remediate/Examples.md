# Examples

## Restore the original contents of a plugin file

```
wordfence remediate /var/www/html/wp-content/plugins/hello.php
```

## Restore all files in a theme directory and output the results to a CSV file

```
wordfence remediate --output-format csv --output-path /tmp/wfcli-remediation-results.csv --output-headers /var/www/html/wp-content/themes/twentytwentythree
```

## Automatically deletect and remediate malware under /var/www/wordpress

```
wordfence malware-scan --output-columns filename -m null-delimited /var/www/wordpress | wordfence remediate
```
