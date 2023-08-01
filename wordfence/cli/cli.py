#!/usr/bin/env python3

from .. import scanning, api


def main():
    license = api.license.License(
            '40d595e120456cdf17700866f23e3820368d3cee58fdd8afb660cdd87934edb9'
        )
    noc1_client = api.noc1.Client(license, base_url='http://noc1.local/v2.27/')
    signatures = noc1_client.get_malware_signatures()
    options = scanning.scanner.Options(
            paths={'/home/alex/Defiant/malicious-samples'},
            threads=1,
            signatures=signatures
        )
    scanner = scanning.scanner.Scanner(options)
    scanner.scan()


if __name__ == '__main__':
    main()
