from ..exceptions import CliException, ConfigurationException


class VulnScanningException(CliException):
    pass


class VulnScanningConfigurationException(
            VulnScanningException,
            ConfigurationException
        ):
    pass
