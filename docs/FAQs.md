# Frequently Asked Questions

#### How do I get a license?

Licenses can be obtained at [https://www.wordfence.com/products/wordfence-cli/](https://www.wordfence.com/products/wordfence-cli/).

#### The scanner has identified malware.  What do I do now?

If you do not know what the file is, we recommend making a backup before you remove it, in case it was a false positive. We always recommend saving a backup copy of the file first, whether by making a full backup of the system or by saving only the file and the location where it belongs, so you can replace it if necessary.

#### What permissions are required to install/run CLI?

Wordfence CLI can be installed and run as any user, including `root`. When installing using `pip` as root, `pip` will return a warning about running as root. Using that installation method, we recommend installing using `pip` as a non-priveledged user. 

#### What the difference is between Wordfence CLI and WP-CLI?

Wordfence CLI is a stand-alone, command-line, malware scanner written in Python. WP-CLI is a WordPress command-line utility for managing a WordPress installation written in PHP. They are 2 separate and distinct pieces of software and are unrelated.

#### If I have Wordfence CLI, do I need the Wordfence plugin too?

If you are a WordPress site owner who is looking for a security solution, the Wordfence plugin offers comprehensive protection and intrustion detection. Wordfence CLI can be used alongside the Wordfence plugin. Wordfence CLI would be used instead of the malware detection functionality of the Wordfence plugin's scan. 

#### If I want to run Wordfence CLI alongside the Wordfence plugin, as a replacement for the malware scanner. Are there any scanner settings I can turn off in the plugin to reduce redundancy?

Yes. Within the Wordfence plugin scan options, you can disable the "Scan file contents for backdoors, trojans and suspicious code" scan option and rely on Wordfence CLI to perform the malware scan.

#### I got the error "Failed to locate libpcre". What do I do?

Wordfence CLI uses the `libprce` library to run our signatures against files. There's a few ways to install it depending on your system:

For Debian/Ubuntu flavors of Linux:

	apt-get install libpcre

Or 

	apt-get install libpcre3

For Red Hat/Fedora based Linux distributions:

	yum install libpcre

Or

	yum install libpcre3

#### How often are signatures refreshed locally?

Once every 24 hours. You can use the `--purge-cache` command line argument to refresh the siganture set.

#### How many workers can I run on my system?

That's really up to you, but we recommend for a fast scan two workers per CPU core.

#### What is the most performant way recommended to run a scan?

We recommend two workers per CPU core for the fastest possible scan. For busy production systems, we recommend limiting the worker count to reduce the impact on the availability of production services.

#### What file types are scanned by default?

The default scan will scan .php, .phtml, .html, .js, and .svg files by default. Using the `--images` option will expand the file list to .jpg, .jpeg, .mp3, .avi, .m4v, .mov, .mp4, .gif, .png, .tiff, .svg, .sql, .js, .tbz2, .bz2, .xz, .zip, .tgz, .gz, .tar, .log, .err. If there are specific file types you want to match, you can use the `--include-files` or `--include-files-pattern` to define a custom set of files/file types to scan. See the [configuration](Configuration.md#command-line-arguments) for more details.

