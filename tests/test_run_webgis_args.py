"""LAN binding must require explicit exposure controls."""
import os
import argparse
import unittest
from unittest.mock import patch

from run_webgis import bind_host, validate_lan_host


class BindHostTests(unittest.TestCase):
    def test_loopback_remains_available_without_lan_config(self):
        with patch.dict(os.environ, WEBGIS_ALLOWED_HOSTS='', WEBGIS_WRITE_API_KEY=''):
            validate_lan_host('127.0.0.1')

    def test_lan_binding_needs_key_and_allowed_host(self):
        with patch.dict(os.environ, WEBGIS_ALLOWED_HOSTS='', WEBGIS_WRITE_API_KEY=''):
            with self.assertRaises(ValueError):
                validate_lan_host('0.0.0.0')
        with patch.dict(os.environ, WEBGIS_ALLOWED_HOSTS='192.168.1.20', WEBGIS_WRITE_API_KEY='test-key'):
            validate_lan_host('0.0.0.0')
            validate_lan_host('192.168.1.20')
            with self.assertRaises(ValueError):
                validate_lan_host('192.168.1.21')

    def test_host_must_be_ip_address(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            bind_host('example.com')


if __name__ == '__main__':
    unittest.main()
