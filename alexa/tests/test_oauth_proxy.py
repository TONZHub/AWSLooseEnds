import json
import unittest
from unittest.mock import patch

import oauth_proxy

class FakeResponse:
    status = 400
    def read(self):
        return b'{"error":"invalid_grant"}'

class ProxyTests(unittest.TestCase):
    def setUp(self):
        oauth_proxy.LWA_CLIENT_ID = "client-id"

    @patch("oauth_proxy.urlopen")
    def test_forwards_request_and_preserves_error(self, urlopen):
        urlopen.return_value = FakeResponse()
        event = {"httpMethod":"POST","headers":{"Authorization":"Basic Y2xpZW50LWlkOnNlY3JldA==","Content-Type":"application/x-www-form-urlencoded"},"body":"grant_type=authorization_code"}
        result = oauth_proxy.lambda_handler(event, type("C", (), {"aws_request_id":"r1"})())
        self.assertEqual(result["statusCode"], 400)
        self.assertEqual(json.loads(result["body"])["error"], "invalid_grant")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.data, b"grant_type=authorization_code")

    @patch("oauth_proxy.urlopen")
    def test_rejects_wrong_client_without_upstream_call(self, urlopen):
        result = oauth_proxy.lambda_handler({"httpMethod":"POST","body":"client_id=wrong"}, None)
        self.assertEqual(result["statusCode"], 401)
        urlopen.assert_not_called()

    def test_rejects_non_post(self):
        result = oauth_proxy.lambda_handler({"httpMethod":"GET"}, None)
        self.assertEqual(result["statusCode"], 405)

if __name__ == "__main__":
    unittest.main()
