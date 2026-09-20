import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

if 'pymysql' not in sys.modules:
    class _PyMySqlError(Exception):
        pass

    def _connect(*args, **kwargs):
        raise _PyMySqlError()

    sys.modules['pymysql'] = SimpleNamespace(
            MySQLError=_PyMySqlError,
            connect=_connect,
            cursors=SimpleNamespace(DictCursor=object)
        )

from .config import parse_wordpress_config
from .site import WordpressSite


class WordpressConfigParserTest(unittest.TestCase):

    def _write_config(self, directory: str, content: str) -> str:
        path = os.path.join(directory, 'wp-config.php')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(content)
        return path

    def test_extracts_database_constants_with_directives(self) -> None:
        content = (
                "<?php\n"
                "ini_set( 'max_execution_time', 300 );\n"
                "@ini_set( 'log_errors', 'Off' );\n"
                "set_time_limit( 300 );\n"
                "define( 'DB_NAME', 'wordpress' );\n"
                "define( 'DB_USER', 'wp_user' );\n"
                "define( 'DB_PASSWORD', 'secret' );\n"
                "define( 'DB_HOST', 'localhost' );\n"
                "define( 'DB_COLLATE', '' );\n"
                "$table_prefix = 'wp_';\n"
            )
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(directory, content)
            state = parse_wordpress_config(os.fsencode(path))
            self.assertEqual(
                    state.get_constant_value(
                        b'DB_NAME',
                        default_to_name=False
                    ),
                    b'wordpress'
                )
            self.assertEqual(
                    state.get_constant_value(
                        b'DB_USER',
                        default_to_name=False
                    ),
                    b'wp_user'
                )
            self.assertEqual(
                    state.get_constant_value(
                        b'DB_PASSWORD',
                        default_to_name=False
                    ),
                    b'secret'
                )
            self.assertEqual(
                    state.get_constant_value(
                        b'DB_HOST',
                        default_to_name=False
                    ),
                    b'localhost'
                )
            self.assertEqual(
                    state.get_constant_value(
                        b'DB_COLLATE',
                        default_to_name=False
                    ),
                    b''
                )
            self.assertEqual(
                    state.get_variable_value(b'table_prefix'),
                    b'wp_'
                )

    def test_handles_concatenated_prefix(self) -> None:
        content = (
                "<?php\n"
                "$table_prefix = 'wp_' . 'blog';\n"
            )
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(directory, content)
            state = parse_wordpress_config(os.fsencode(path))
            self.assertEqual(
                    state.get_variable_value(b'table_prefix'),
                    b'wp_blog'
                )

    def test_extracts_constants_inside_conditional_block(self) -> None:
        content = (
                "<?php\n"
                "if ( ! defined( 'DB_NAME' ) ) {\n"
                "    define( 'DB_NAME', 'conditional' );\n"
                "}\n"
                "define( 'DB_USER', 'wp_user' );\n"
                "define( 'DB_PASSWORD', 'secret' );\n"
                "define( 'DB_HOST', 'localhost' );\n"
                "$table_prefix = 'wp_';\n"
            )
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(directory, content)
            state = parse_wordpress_config(path.encode())
            self.assertEqual(
                    state.get_constant_value(
                        b'DB_NAME',
                        default_to_name=False
                    ),
                    b'conditional'
                )

    def test_resolves_constant_function_call(self) -> None:
        content = (
                "<?php\n"
                "define( 'PRIMARY_DB', 'primary' );\n"
                "define( 'DB_NAME', constant( 'PRIMARY_DB' ) );\n"
                "define( 'DB_USER', 'wp_user' );\n"
                "define( 'DB_PASSWORD', 'secret' );\n"
                "define( 'DB_HOST', 'localhost' );\n"
                "$table_prefix = 'wp_';\n"
            )
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(directory, content)
            state = parse_wordpress_config(path.encode())
            self.assertEqual(
                    state.get_constant_value(
                        b'DB_NAME',
                        default_to_name=False
                    ),
                    b'primary'
                )

    def test_ignores_unknown_functions(self) -> None:
        content = (
                "<?php\n"
                "custom_setup();\n"
                "define( 'DB_NAME', 'wordpress' );\n"
                "define( 'DB_USER', 'wp_user' );\n"
                "define( 'DB_PASSWORD', 'secret' );\n"
                "define( 'DB_HOST', 'localhost' );\n"
                "$table_prefix = 'wp_';\n"
            )
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(directory, content)
            state = parse_wordpress_config(path.encode())
            self.assertEqual(
                    state.get_constant_value(
                        b'DB_NAME',
                        default_to_name=False
                    ),
                    b'wordpress'
                )

    def test_unresolved_values_are_skipped(self) -> None:
        content = (
                "<?php\n"
                "define( 'DB_NAME', getenv( 'WP_DB_NAME' ) );\n"
                "define( 'DB_USER', 'wp_user' );\n"
            )
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_config(directory, content)
            state = parse_wordpress_config(os.fsencode(path))
            self.assertIsNone(
                    state.get_constant_value(
                        b'DB_NAME',
                        default_to_name=False
                    )
                )
            self.assertEqual(
                    state.get_constant_value(
                        b'DB_USER',
                        default_to_name=False
                    ),
                    b'wp_user'
                )


class WordpressSiteDatabaseTest(unittest.TestCase):

    def _create_minimal_site(self, directory: str, config: str) -> str:
        os.makedirs(directory, exist_ok=True)
        for name in ('wp-admin', 'wp-includes'):
            os.makedirs(os.path.join(directory, name), exist_ok=True)
        for name in ('wp-load.php', 'wp-blog-header.php'):
            path = os.path.join(directory, name)
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write("<?php\n")
        includes_version = os.path.join(
                directory,
                'wp-includes',
                'version.php'
            )
        with open(includes_version, 'w', encoding='utf-8') as handle:
            handle.write("<?php $wp_version = '6.4.0';")
        config_path = os.path.join(directory, 'wp-config.php')
        with open(config_path, 'w', encoding='utf-8') as handle:
            handle.write(config)
        return directory

    def test_get_database_uses_new_parser(self) -> None:
        config = (
                "<?php\n"
                "ini_set( 'max_execution_time', 300 );\n"
                "define( 'DB_NAME', 'wordpress' );\n"
                "define( 'DB_USER', 'wp_user' );\n"
                "define( 'DB_PASSWORD', 'secret' );\n"
                "define( 'DB_HOST', 'localhost' );\n"
                "define( 'DB_COLLATE', '' );\n"
                "$table_prefix = 'wp_';\n"
            )
        with tempfile.TemporaryDirectory() as directory:
            site_path = self._create_minimal_site(directory, config)
            site = WordpressSite(os.fsencode(site_path))
            database = site.get_database()
            self.assertEqual(database.name, 'wordpress')
            self.assertEqual(database.server.user, 'wp_user')
            self.assertEqual(database.server.host, 'localhost')
            self.assertEqual(database.server.password, 'secret')
            self.assertEqual(database.prefix, 'wp_')

    def test_get_database_parses_port_from_host(self) -> None:
        config = (
                "<?php\n"
                "define( 'DB_NAME', 'wordpress' );\n"
                "define( 'DB_USER', 'wp_user' );\n"
                "define( 'DB_PASSWORD', 'secret' );\n"
                "define( 'DB_HOST', '127.0.0.1:3307' );\n"
                "define( 'DB_COLLATE', '' );\n"
                "$table_prefix = 'wp_';\n"
            )
        with tempfile.TemporaryDirectory() as directory:
            site_path = self._create_minimal_site(directory, config)
            site = WordpressSite(os.fsencode(site_path))
            database = site.get_database()
            self.assertEqual(database.server.host, '127.0.0.1')
            self.assertEqual(database.server.port, 3307)


if __name__ == '__main__':
    unittest.main()
