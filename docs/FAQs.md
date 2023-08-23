# Frequently Asked Questions

#### The scanner has identified malware.  What do I do now?

If you do not know what the file is, we recommend making a backup before you remove it, in case it was a false positive. We always recommend saving a backup copy of the file first, whether by making a full backup of the system or by saving only the file and the location where it belongs, so you can replace it if necessary.

#### What permissions are required to install/run CLI?

Wordfence CLI can be installed and run as any user, including `root`. When installing using `pip` as root, `pip` will return a warning about running as root. Using that installation method, we recommend installing using `pip` as a non-priveledged user. 

#### What the difference is between Wordfence CLI and WP-CLI?

Wordfence CLI is a stand-alone, command-line, malware scanner written in Python. WP-CLI is a WordPress command-line utility for managing a WordPress installation written in PHP. They are 2 separate and distinct pieces of software and are unrelated.

#### If I have Wordfence CLI, do I need the Wordfence plugin too?

If you are a WordPress site owner who is looking for a security solution, the Wordfence plugin offers comprehensive protection and intrustion detection. Wordfence CLI can be used alongside the Wordfence plugin. Wordfence CLI would be used instead of the malware detection functionality of the Wordfence plugin's scan. 

