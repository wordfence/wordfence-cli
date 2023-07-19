#!/usr/bin/env python3

from .. import scanning, api


def main():
    license = api.license.License(
            '<wordfence-cli-license>'
        )
    noc1_client = api.noc1.Client(license, base_url='<noc-1-url>/v2.27/')
    signatures = noc1_client.get_malware_signatures()
    options = scanning.scanner.Options(
            paths={'/path/to/scan'},
            threads=1,
            signatures=signatures
        )
    scanner = scanning.scanner.Scanner(options)
    scanner.scan()


if __name__ == '__main__':
    main()
