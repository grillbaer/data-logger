from unittest import TestCase, main

from powermeterapatorec3 import PowerMeterReading, PowerMeterApatorEC3Repeating, PowerMeterApatorEC3


class MockPowerMeterApatorEC3:
    def start(self):
        pass

    def close(self):
        pass

    def read(self):
        return PowerMeterReading(False, None, None, None)


class TestPowerMeterApatorEC3(TestCase):
    def test__parse_line_str(self):
        pm = PowerMeterApatorEC3("none")
        self.assertEqual("008482.46", pm._parse_line_str("1.8.1*00(008482.46)  "))

    def test__parse_(self):
        pm = PowerMeterApatorEC3("none")
        self.assertEqual(8482.46, pm._parse_line_float("1.8.1*00(008482.46)  "))


class TestPowerMeterApatorEC3Repeating(TestCase):
    def setUp(self):
        self.pm = PowerMeterApatorEC3Repeating(MockPowerMeterApatorEC3(), 1, 30)

    def test_update_high_power(self):
        self.pm.reading_ts = 1e9 - 200
        self.pm.reading = PowerMeterReading(False, None, None, None)
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertIsNone(self.pm.high.power)

        self.pm.reading_ts = 1e9 - 100
        self.pm.reading = PowerMeterReading(True, 3000, 1999.9, 1000)
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertIsNone(self.pm.high.power)

        self.pm.reading_ts = 1e9
        self.pm.reading = PowerMeterReading(True, 3000, 2000, 1000)
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertIsNone(self.pm.high.power)

        self.pm.reading_ts = 1e9 + 3600
        self.pm.reading = PowerMeterReading(True, 3000, 2000.1, 1000)
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertAlmostEqual(self.pm.high.power, 100.)

        self.pm.reading_ts += 600
        self.pm.reading = PowerMeterReading(True, 3000, 2000.1, 1000)
        self.pm.low.power = 123
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertAlmostEqual(self.pm.high.power, 100.)
        self.assertEqual(self.pm.low.power, 123)

        self.pm.reading_ts += 600
        self.pm.reading = PowerMeterReading(True, 3000, 2000.2, 1000)
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertAlmostEqual(self.pm.high.power, 300.)

        self.pm.reading_ts += 100
        self.pm.reading = PowerMeterReading(False, None, None, None)
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertAlmostEqual(self.pm.high.power, 300.)

        self.pm.reading_ts += 500
        self.pm.reading = PowerMeterReading(True, 3000, 2001.2, 1000)
        self.pm.low.power = 123
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertAlmostEqual(self.pm.high.power, 3600 * 1000 / 600.)
        self.assertEqual(self.pm.low.power, 0)

    def test_update_low_power(self):
        self.pm.reading_ts = 1e9 - 60
        self.pm.reading = PowerMeterReading(False, None, None, None)
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertIsNone(self.pm.low.power)

        self.pm.reading_ts = 1e9 - 30
        self.pm.reading = PowerMeterReading(True, 3000, 2000, 999.9)
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertIsNone(self.pm.low.power)

        self.pm.reading_ts = 1e9
        self.pm.reading = PowerMeterReading(True, 3000, 2000, 1000)
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertIsNone(self.pm.low.power)

        self.pm.reading_ts = 1e9 + 3600
        self.pm.reading = PowerMeterReading(True, 3000, 2000, 1000.1)
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertAlmostEqual(self.pm.low.power, 100.)

        self.pm.reading_ts += 600
        self.pm.reading = PowerMeterReading(True, 3000, 2000, 1000.1)
        self.pm.high.power = 123
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertAlmostEqual(self.pm.low.power, 100.)
        self.assertEqual(self.pm.high.power, 123)

        self.pm.reading_ts += 600
        self.pm.reading = PowerMeterReading(True, 3000, 2000, 1000.2)
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertAlmostEqual(self.pm.low.power, 300.)

        self.pm.reading_ts += 100
        self.pm.reading = PowerMeterReading(False, None, None, None)
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertAlmostEqual(self.pm.low.power, 300.)

        self.pm.reading_ts += 500
        self.pm.reading = PowerMeterReading(True, 3000, 2000, 1001.2)
        self.pm.high.power = 123
        self.pm._update_high_power()
        self.pm._update_low_power()
        self.assertAlmostEqual(self.pm.low.power, 3600 * 1000 / 600.)
        self.assertEqual(self.pm.high.power, 0)


if __name__ == '__main__':
    main()
