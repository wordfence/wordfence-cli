from wordfence import scanning, api


def main(config) -> int:
    license = api.license.License(config.license)
    if config.license is None:
        print('A license must be specified')
        return 1
    noc1_client = api.noc1.Client(license)
    signatures = noc1_client.get_malware_signatures()
    paths = set()
    for argument in config.trailing_arguments:
        paths.add(argument)
    options = scanning.scanner.Options(
            paths=paths,
            threads=int(config.threads),
            signatures=signatures
        )
    scanner = scanning.scanner.Scanner(options)
    scanner.scan()
    return 0
