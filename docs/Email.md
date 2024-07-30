# Email

Wordfence CLI can be configured to send a summary of scan results (both the malware scan and the vulnerability scan) to an email address. The email will only send when the scan actually finds something, for instance a file contains malware, or a WordPress plugin has a vulnerability. An email will also not be sent in the event a scan fails. We recommend reviewing scan findings regularly.

## Configuration

The following command line arguments can be supplied to either the malware scan or the vulnerability scan to tell CLI how to send email. If using SMTP, we recommend storing the configuration in the INI rather than supplying credentials as command line parameters.

- `-E`, `--email`: Email address(es) to which to send reports.
	* `--email-from`: The From address to use when sending emails. If not specified, the current username and hostname will be used.
	* `--smtp-host`: The host name of the SMTP server to use for sending email.
	* `--smtp-port`: The port of the SMTP server to use for sending email.
	* `--smtp-tls-mode`: The SSL/TLS mode to use when communicating with the SMTP server. none disables TLS entirely. smtps requires TLS for all communication while starttls will negotiate TLS if supported using the STARTTLS SMTP command. Options: `none`, `smtps`, `starttls` (default: `starttls`)
	* `--smtp-user`: The username for authenticating with the SMTP server.
	* `--smtp-password`: The password for authentication with the SMTP server. This should generally be specified in an INI file as including passwords as command line arguments can expose them to other users on the same system.
	* `--sendmail-path`: The path to the sendmail executable. This will be used to send email if SMTP is not configured. (default: `sendmail`)

If you do not have access to an external SMTP server, `sendmail` can be used as a local relay. We recommend going through the process of authenticating your server as an email sender using SPF, DKIM, and DMARC to prevent emails from CLI from being flagged as spam.

## Attaching Output Files

Using the `--output-path` option in conjunction with `--email` will cause the output file to be added as an attachment to the emailed report.

## Further reading

- [Email Authentication](https://en.wikipedia.org/wiki/Email_authentication)
- [SPF](https://en.wikipedia.org/wiki/Sender_Policy_Framework)
- [DKIM](https://en.wikipedia.org/wiki/DomainKeys_Identified_Mail)
- [DMARC](https://en.wikipedia.org/wiki/DMARC)
