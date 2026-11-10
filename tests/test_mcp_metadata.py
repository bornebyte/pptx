import os
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from src.main import MCP_ICON_PATH, _validate_mcp_icon, app


class McpIconMetadataTests(unittest.TestCase):
    def setUp(self):
        self.public_url = patch.dict(os.environ, {'PUBLIC_BASE_URL': 'https://ppt.example.test'})
        self.public_url.start()
        self.addCleanup(self.public_url.stop)
        self.client = app.test_client()

    @staticmethod
    def legacy_request(method, request_id, params=None, version='2025-11-25'):
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'method': method,
            'params': {'protocolVersion': version, **(params or {})} if method == 'initialize' else (params or {}),
        }

    @staticmethod
    def modern_request(method, request_id, params=None):
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'method': method,
            'params': {
                **(params or {}),
                '_meta': {
                    'io.modelcontextprotocol/protocolVersion': '2026-07-28',
                    'io.modelcontextprotocol/clientInfo': {'name': 'icon-test', 'version': '1.0'},
                    'io.modelcontextprotocol/clientCapabilities': {},
                },
            },
        }

    def post_legacy(self, method, request_id, params=None, version='2025-11-25'):
        return self.client.post(
            '/mcp',
            json=self.legacy_request(method, request_id, params, version),
            headers={'MCP-Protocol-Version': version},
        )

    def post_modern(self, method, request_id, params=None):
        return self.client.post(
            '/mcp',
            json=self.modern_request(method, request_id, params),
            headers={'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': method},
        )

    def test_legacy_initialize_advertises_server_icon(self):
        response = self.post_legacy('initialize', 1, {'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}})

        self.assertEqual(response.status_code, 200)
        server_info = response.json['result']['serverInfo']
        self.assertEqual(server_info['title'], 'PowerPoint Generator')
        self.assertEqual(server_info['icons'], [{
            'src': 'https://ppt.example.test/mcp/icon.png',
            'mimeType': 'image/png',
            'sizes': ['128x128'],
        }])

    def test_older_legacy_version_does_not_receive_new_icon_fields(self):
        response = self.post_legacy(
            'initialize', 1,
            {'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}},
            version='2025-06-18',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['result']['serverInfo'], {'name': 'ppt-generator', 'version': '1.0.0'})

    def test_tool_icons_are_advertised_for_supported_versions(self):
        legacy = self.post_legacy('tools/list', 2).json['result']['tools'][0]
        modern = self.post_modern('tools/list', 3).json['result']['tools'][0]

        self.assertEqual(legacy['icons'][0]['src'], 'https://ppt.example.test/mcp/icon.png')
        self.assertEqual(modern['icons'][0]['mimeType'], 'image/png')
        self.assertEqual(modern['icons'][0]['sizes'], ['128x128'])

    def test_modern_discovery_contains_standard_server_info_and_public_cache(self):
        response = self.post_modern('server/discover', 4)

        self.assertEqual(response.status_code, 200)
        result = response.json['result']
        server_info = result['_meta']['io.modelcontextprotocol/serverInfo']
        self.assertEqual(server_info['icons'][0]['src'], 'https://ppt.example.test/mcp/icon.png')
        self.assertEqual(result['cacheScope'], 'public')
        self.assertGreater(result['ttlMs'], 0)

    def test_icon_is_public_png_with_cache_headers(self):
        response = self.client.get('/mcp/icon.png')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'image/png')
        self.assertIn('public', response.headers['Cache-Control'])
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], '*')
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertTrue(_validate_mcp_icon(MCP_ICON_PATH))
        response.close()

    def test_image_validation_rejects_non_png_data(self):
        with tempfile.NamedTemporaryFile() as invalid_icon:
            invalid_icon.write(b'not an image')
            invalid_icon.flush()
            self.assertFalse(_validate_mcp_icon(invalid_icon.name))

    def test_invalid_non_https_base_url_does_not_get_advertised(self):
        with patch.dict(os.environ, {'PUBLIC_BASE_URL': 'http://ppt.example.test'}):
            response = self.post_legacy('initialize', 5, {'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}})

        info = response.json['result']['serverInfo']
        self.assertNotIn('icons', info)
        self.assertNotIn('websiteUrl', info)


if __name__ == '__main__':
    unittest.main()
