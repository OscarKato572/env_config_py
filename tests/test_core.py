import unittest

from env_config_py import ConfigError, EnvConfig


class GetTests(unittest.TestCase):
    def test_reads_string(self):
        config = EnvConfig({"NAME": "str"}, environ={"NAME": "widget"})
        self.assertEqual(config.get("NAME"), "widget")

    def test_reads_integer(self):
        config = EnvConfig({"PORT": "int"}, environ={"PORT": "8080"})
        self.assertEqual(config.get("PORT"), 8080)
        self.assertIsInstance(config.get("PORT"), int)

    def test_reads_float(self):
        config = EnvConfig({"RATIO": "float"}, environ={"RATIO": "1.5"})
        self.assertAlmostEqual(config.get("RATIO"), 1.5)

    def test_float_parses_scientific_notation(self):
        config = EnvConfig({"RATIO": "float"}, environ={"RATIO": "1e3"})
        self.assertAlmostEqual(config.get("RATIO"), 1000.0)

    def test_bool_accepts_common_true_spellings(self):
        for raw in ("1", "true", "TRUE", "yes", "on"):
            with self.subTest(raw=raw):
                config = EnvConfig({"DEBUG": "bool"}, environ={"DEBUG": raw})
                self.assertIs(config.get("DEBUG"), True)

    def test_bool_accepts_common_false_spellings(self):
        for raw in ("0", "false", "FALSE", "no", "off"):
            with self.subTest(raw=raw):
                config = EnvConfig({"DEBUG": "bool"}, environ={"DEBUG": raw})
                self.assertIs(config.get("DEBUG"), False)

    def test_bool_rejects_unknown_spelling(self):
        config = EnvConfig({"DEBUG": "bool"}, environ={"DEBUG": "maybe"})
        with self.assertRaises(ConfigError):
            config.get("DEBUG")

    def test_list_splits_and_trims(self):
        config = EnvConfig(
            {"HOSTS": "list"}, environ={"HOSTS": " a, b ,,c "}
        )
        self.assertEqual(config.get("HOSTS"), ["a", "b", "c"])

    def test_list_of_empty_string_is_empty_list(self):
        config = EnvConfig({"HOSTS": "list"}, environ={"HOSTS": ""})
        self.assertEqual(config.get("HOSTS"), [])

    def test_default_used_when_variable_absent(self):
        config = EnvConfig({"PORT": "int"}, defaults={"PORT": 9000}, environ={})
        self.assertEqual(config.get("PORT"), 9000)

    def test_default_is_not_coerced(self):
        # Defaults are trusted Python values, not environment strings.
        config = EnvConfig(
            {"HOSTS": "list"}, defaults={"HOSTS": ["a"]}, environ={}
        )
        self.assertEqual(config.get("HOSTS"), ["a"])

    def test_missing_required_key_raises(self):
        config = EnvConfig({"PORT": "int"}, environ={})
        with self.assertRaises(ConfigError):
            config.get("PORT")

    def test_unknown_key_raises(self):
        config = EnvConfig({"PORT": "int"}, environ={})
        with self.assertRaises(ConfigError):
            config.get("OTHER")

    def test_invalid_integer_raises(self):
        config = EnvConfig({"PORT": "int"}, environ={"PORT": "eighty"})
        with self.assertRaises(ConfigError):
            config.get("PORT")

    def test_invalid_float_raises(self):
        config = EnvConfig({"RATIO": "float"}, environ={"RATIO": "fast"})
        with self.assertRaises(ConfigError):
            config.get("RATIO")

    def test_unsupported_type_in_schema_raises(self):
        with self.assertRaises(ConfigError):
            EnvConfig({"PORT": "integer"})

    def test_default_for_unknown_key_raises(self):
        with self.assertRaises(ConfigError):
            EnvConfig({"PORT": "int"}, defaults={"HOST": "localhost"})


class GetManyTests(unittest.TestCase):
    def test_returns_all_requested_keys(self):
        config = EnvConfig(
            {"HOST": "str", "PORT": "int"},
            environ={"HOST": "localhost", "PORT": "5432"},
        )
        self.assertEqual(
            config.get_many(["HOST", "PORT"]),
            {"HOST": "localhost", "PORT": 5432},
        )

    def test_preserves_request_order(self):
        config = EnvConfig(
            {"HOST": "str", "PORT": "int"},
            environ={"HOST": "localhost", "PORT": "5432"},
        )
        self.assertEqual(list(config.get_many(["PORT", "HOST"])), ["PORT", "HOST"])

    def test_propagates_error(self):
        config = EnvConfig({"PORT": "int"}, environ={})
        with self.assertRaises(ConfigError):
            config.get_many(["PORT"])


class ContainsTests(unittest.TestCase):
    def test_true_for_present_variable(self):
        config = EnvConfig({"PORT": "int"}, environ={"PORT": "80"})
        self.assertIn("PORT", config)

    def test_true_for_default(self):
        config = EnvConfig({"PORT": "int"}, defaults={"PORT": 80}, environ={})
        self.assertIn("PORT", config)

    def test_false_for_absent_required_key(self):
        config = EnvConfig({"PORT": "int"}, environ={})
        self.assertNotIn("PORT", config)

    def test_false_for_unknown_key(self):
        config = EnvConfig({"PORT": "int"}, environ={"PORT": "80"})
        self.assertNotIn("HOST", config)

    def test_presence_is_not_coercion(self):
        config = EnvConfig({"PORT": "int"}, environ={"PORT": "eighty"})
        self.assertIn("PORT", config)


if __name__ == "__main__":
    unittest.main()
