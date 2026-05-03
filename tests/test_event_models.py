from __future__ import annotations

import unittest


class PackageImportTest(unittest.TestCase):
    def test_personal_memory_service_package_imports(self) -> None:
        import phone_mem
        import phone_mem.personal_memory_service as service_package

        self.assertEqual(phone_mem.__version__, "0.1.0")
        self.assertTrue(hasattr(service_package, "__all__"))


if __name__ == "__main__":
    unittest.main()
