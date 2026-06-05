import unittest

from app.services.config_service import ConfigService


class ConfigServiceResponseParsingTests(unittest.TestCase):
    def test_extracts_plain_chat_content(self):
        result = {
            "choices": [
                {"message": {"content": "OK"}}
            ]
        }

        self.assertEqual(ConfigService._extract_chat_response_text(result), "OK")

    def test_extracts_reasoning_content_for_connection_tests(self):
        result = {
            "choices": [
                {"message": {"content": "", "reasoning_content": "thinking text"}}
            ]
        }

        self.assertEqual(ConfigService._extract_chat_response_text(result), "thinking text")

    def test_extracts_list_content_blocks(self):
        result = {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": "hello"},
                            {"type": "text", "content": "world"},
                        ]
                    }
                }
            ]
        }

        self.assertEqual(ConfigService._extract_chat_response_text(result), "hello\nworld")


if __name__ == "__main__":
    unittest.main()
