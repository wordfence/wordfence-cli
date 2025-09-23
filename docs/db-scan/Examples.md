# Examples

## Scanning a single WordPress database

Scan a WordPress database using explicit connection settings and prompt for the password at runtime.

	wordfence db-scan -H db.example.com -P 3306 -u wordpress -D wordpress --prompt-for-password

## Automatically locating WordPress installations

Search the supplied directories for `wp-config.php`, extract the database credentials, and scan each discovered site.

	wordfence db-scan -S /var/www/wordpress /srv/wordpress

## Scanning databases listed in a JSON file

Provide a JSON file that lists one or more database configurations. Each entry must include `name`, `user`, `password`, and `host`, with optional `port`, `collation`, and `prefix` values. Multiple JSON files can be supplied.

	wordfence db-scan /etc/wordfence/databases.json

## Writing database scan results to a CSV

Output scan results to a CSV file with headers and explicitly selected columns.

	wordfence db-scan -S /var/www/wordpress --output-format csv --output-columns table,rule_description,row --output-headers --output-path /home/username/db-scan-results.csv
