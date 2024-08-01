import os

from enum import Enum
from typing import Optional

from ..util.io import resolve_path, get_path_components
from ..util.encoding import bytes_to_str
from .site import WordpressSite
from .exceptions import WordpressException
from .extension import Extension


class FileType(str, Enum):
    CORE = 'core'
    PLUGIN = 'plugin'
    THEME = 'theme'
    UNKNOWN = 'unknown'


class FileIdentity:

    def __init__(
                self,
                type: FileType,
                site: Optional[WordpressSite] = None,
                extension: Optional[Extension] = None,
            ):
        self.type = type
        self.site = site
        self.extension = extension

    def is_final(self) -> bool:
        return False


class GroupIdentity(FileIdentity):

    def __init__(
                self,
                type: FileType,
                path: bytes,
                site: Optional[WordpressSite] = None,
                extension: Optional[Extension] = None,
                final: bool = False
            ):
        super().__init__(type, site, extension)
        self.path = path
        self.final = final

    def is_final(self) -> bool:
        return self.final


class KnownFileIdentity(FileIdentity):

    def __init__(
                self,
                type: FileType,
                local_path: bytes,
                site: Optional[WordpressSite] = None,
                extension: Optional[Extension] = None,
            ):
        super().__init__(type, site, extension)
        self.local_path = local_path

    def is_final(self) -> bool:
        return True

    def __str__(self) -> str:
        if self.extension is None:
            software = 'WordPress'
            version = self.site.get_version()
        else:
            software = self.extension.get_name()
            version = self.extension.version
        if isinstance(version, bytes):
            version = bytes_to_str(version)
        return (
                os.fsdecode(self.local_path) +
                f' of {self.type.value} {software} ({version})'
            )


class KnownPath:

    def __init__(
                self,
                identity: Optional[FileIdentity] = None
            ):
        self.identity = identity
        self.children = {}

    def is_root(self) -> bool:
        return self.path is None

    def find_identity(self, path: bytes) -> Optional[FileIdentity]:
        node = self
        path = resolve_path(path)
        identity = None
        for component in get_path_components(path):
            if node.identity is not None:
                identity = node.identity
                if node.identity.is_final():
                    break
            try:
                node = node.children[component]
            except KeyError:
                break
        if node.identity is not None:
            return node.identity
        return identity

    def set_identity(
                self,
                path: bytes,
                identity: FileIdentity,
                resolve: bool = True
            ) -> None:
        node = self
        if resolve:
            path = resolve_path(path)
        for component in get_path_components(path):
            if component not in node.children:
                node.children[component] = KnownPath()
            node = node.children[component]
        node.identity = identity

    def __str__(self) -> str:
        if self.identity is None:
            return 'Unknown Path'
        else:
            final = self.identity.is_final()
            return f'Known Path: {self.identity.type}, {final}'

    def debug(self, indent: str = '') -> None:
        print(indent + str(self))
        for path, child in self.children.items():
            print(indent + f' {path}')
            child.debug(indent + '\t')


class FileIdentifier:

    def __init__(self):
        self.known_paths = KnownPath()

    def _identify_new_path(self, path: bytes):
        try:
            site = WordpressSite(
                        path,
                        is_child_path=True,
                        allow_io_errors=True
                    )
            core_path = site.core_path
            self.known_paths.set_identity(
                    core_path,
                    GroupIdentity(
                        type=FileType.CORE,
                        path=core_path,
                        site=site
                    )
                )
            for plugin in site.get_all_plugins():
                self.known_paths.set_identity(
                        plugin.path,
                        GroupIdentity(
                            type=FileType.PLUGIN,
                            path=plugin.path,
                            site=site,
                            extension=plugin,
                            final=True
                        ),
                        resolve=False
                    )
            for theme in site.get_themes():
                self.known_paths.set_identity(
                        theme.path,
                        GroupIdentity(
                            type=FileType.THEME,
                            path=theme.path,
                            site=site,
                            extension=theme,
                            final=True
                        ),
                        resolve=False
                    )
        except WordpressException:
            self.known_paths.set_identity(
                    path,
                    FileIdentity(
                        type=FileType.UNKNOWN
                    )
                )

    def identify(self, path: bytes, identify_new: bool = True) -> FileIdentity:
        identity = self.known_paths.find_identity(path)
        if identity is None:
            if identify_new:
                self._identify_new_path(path)
                return self.identify(path, False)
            else:
                return FileIdentity(FileType.UNKNOWN)
        elif isinstance(identity, GroupIdentity):
            local_path = os.path.relpath(path, identity.path) \
                if path != identity.path \
                else path.name
            identity = KnownFileIdentity(
                    identity.type,
                    local_path,
                    identity.site,
                    identity.extension
                )
            self.known_paths.set_identity(path, identity)
        return identity
