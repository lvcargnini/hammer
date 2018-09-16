#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Tests for unit classes.
#
#  Copyright 2018 Edward Wang <edward.c.wang@compdigitec.com>

import unittest

import hammer_vlsi


class VoltageValueTest(unittest.TestCase):
    """
    Test voltages and other features of ValueWithUnits.
    """
    def test_voltage(self) -> None:
        """
        Test that voltages generally work as expected.
        """
        v8m = hammer_vlsi.units.VoltageValue("888 mV")
        v8 = hammer_vlsi.units.VoltageValue("0.888 V")
        self.assertAlmostEqual(v8m.value, 0.888)
        self.assertAlmostEqual(v8.value, 0.888)

        v105 = hammer_vlsi.units.VoltageValue("1.05 V")
        self.assertAlmostEqual(v105.value_in_units("mV"), 1050)

        v4 = hammer_vlsi.units.VoltageValue("400 mV")
        self.assertEqual(v4.str_value_in_units("V"), "0.4 V")

    def test_compare(self) -> None:
        """
        Test that comparison operators work properly.
        """
        value_125_mV = hammer_vlsi.units.VoltageValue("125 mV")
        value_125_mV2 = hammer_vlsi.units.VoltageValue("0.125")
        value_250_mV = hammer_vlsi.units.VoltageValue("250 mV")
        value_111_uV = hammer_vlsi.units.VoltageValue("111 uV")

        # Equality
        self.assertTrue(value_125_mV == value_125_mV2)
        self.assertTrue(value_125_mV2 == value_125_mV)
        self.assertFalse(value_250_mV == value_125_mV)
        self.assertTrue(value_250_mV != value_125_mV)

        # Less than
        self.assertTrue(value_125_mV <= value_125_mV)
        self.assertTrue(value_125_mV < value_250_mV)
        self.assertTrue(value_125_mV2 < value_250_mV)

        # Greater than
        self.assertTrue(value_125_mV >= value_125_mV)
        self.assertTrue(value_125_mV > value_111_uV)
        self.assertTrue(value_125_mV2 > value_111_uV)

        # Check that comparing against the wrong type leads to TypeError
        with self.assertRaises(TypeError):
            value_125_mV == "125 mV"  # type: ignore
        with self.assertRaises(TypeError):
            value_125_mV2 == hammer_vlsi.units.TimeValue("0.125")  # type: ignore
        with self.assertRaises(TypeError):
            value_125_mV < 1  # type: ignore
        with self.assertRaises(TypeError):
            value_125_mV > 0.111  # type: ignore


class TimeValueTest(unittest.TestCase):
    def test_read_and_write(self) -> None:
        """
        Test that we can parse and emit time values.
        """
        tv = hammer_vlsi.units.TimeValue("1000 ns")
        self.assertEqual(tv.str_value_in_units("ns"), "1000 ns")
        self.assertEqual(tv.str_value_in_units("us"), "1 us")
        self.assertEqual(tv.value_in_units("ps"), 1000000.0)

    def test_default_prefix(self) -> None:
        """
        Test that we can parse and emit time values.
        """
        tv = hammer_vlsi.units.TimeValue("1000")
        self.assertEqual(tv.value_in_units("ns"), 1000)
        tv2 = hammer_vlsi.units.TimeValue("42", "m")
        self.assertEqual(tv2.value_in_units("ms"), 42)
        self.assertEqual(tv2.value_in_units("", round_zeroes=False), 0.042)

    def test_errors(self) -> None:
        """
        Test that errors get caught.
        """

        def bad_1():
            hammer_vlsi.units.TimeValue("bugaboo")

        def bad_2():
            hammer_vlsi.units.TimeValue("1.1.1.1 ps")

        def bad_3():
            hammer_vlsi.units.TimeValue("420 xs")

        def bad_4():
            hammer_vlsi.units.TimeValue("12 noobs")

        def bad_5():
            hammer_vlsi.units.TimeValue("666......")

        self.assertRaises(ValueError, bad_1)
        self.assertRaises(ValueError, bad_2)
        self.assertRaises(ValueError, bad_3)
        self.assertRaises(ValueError, bad_4)
        self.assertRaises(ValueError, bad_5)


class TemperatureValueTest(unittest.TestCase):
    def test_temperature(self) -> None:
        t125 = hammer_vlsi.units.TemperatureValue("125 C")
        self.assertAlmostEqual(t125.value, 125)

        t40 = hammer_vlsi.units.TemperatureValue("40 C")
        self.assertAlmostEqual(t40.value, 40)

        t28_5 = hammer_vlsi.units.TemperatureValue("28.5 C")
        self.assertAlmostEqual(t28_5.value, 28.5)

        t25 = hammer_vlsi.units.TemperatureValue("25 C")
        self.assertAlmostEqual(t25.value, 25)
        self.assertAlmostEqual(t25.value_in_units("C"), 25)
        self.assertEqual(t25.str_value_in_units("C"), "25 C")


if __name__ == '__main__':
    unittest.main()
