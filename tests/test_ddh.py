"""Unit tests for the delta-hedging package.

Run with::

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import math
import unittest

import numpy as np

from ddh.config import Paths, Task2Config
from ddh.option import Option
from ddh.pnl import PnLCalculator
from ddh.pricing import OptionPricer
from ddh.simulation import StockPriceSimulator
from ddh import task2 as task2_module
from ddh import validation


class TestPricing(unittest.TestCase):
    def setUp(self) -> None:
        self.option = Option(strike=105.0, spot=100.0, rate=0.025,
                             maturity=0.4, volatility=0.24)

    def test_known_call_value(self) -> None:
        price, delta = OptionPricer("C").bsm(self.option)
        self.assertAlmostEqual(price, 4.391680, places=5)
        self.assertAlmostEqual(delta, 0.428711, places=5)

    def test_put_call_parity(self) -> None:
        call = OptionPricer("C").price(self.option)
        put = OptionPricer("P").price(self.option)
        o = self.option
        expected = o.spot - o.strike * math.exp(-o.rate * o.maturity)
        self.assertAlmostEqual(call - put, expected, places=10)

    def test_delta_matches_finite_difference(self) -> None:
        pricer = OptionPricer("C")
        h = 1e-4
        up = pricer.price(self.option.with_(spot=self.option.spot + h))
        down = pricer.price(self.option.with_(spot=self.option.spot - h))
        self.assertAlmostEqual(pricer.delta(self.option), (up - down) / (2 * h), places=6)

    def test_zero_maturity_is_intrinsic(self) -> None:
        pricer = OptionPricer("C")
        price, delta = pricer.bsm(self.option.with_(spot=120.0, maturity=0.0))
        self.assertAlmostEqual(price, 15.0, places=10)
        self.assertAlmostEqual(delta, 1.0, places=10)

    def test_implied_volatility_round_trip(self) -> None:
        pricer = OptionPricer("C")
        for sigma in (0.08, 0.24, 0.55, 1.2):
            target = pricer.price(self.option.with_(volatility=sigma))
            recovered = pricer.implied_volatility(self.option, target)
            self.assertAlmostEqual(recovered, sigma, places=5)

    def test_price_grid_matches_scalar_pricer(self) -> None:
        pricer = OptionPricer("C")
        spots = np.array([[90.0, 100.0, 110.0]])
        maturities = np.array([0.4, 0.2, 0.0])
        prices, deltas = pricer.price_grid(spots, self.option.strike, self.option.rate,
                                           maturities, self.option.volatility)
        for j in range(3):
            expected = pricer.bsm(
                self.option.with_(spot=spots[0, j], maturity=maturities[j])
            )
            self.assertAlmostEqual(prices[0, j], expected[0], places=10)
            self.assertAlmostEqual(deltas[0, j], expected[1], places=10)


class TestSimulation(unittest.TestCase):
    def test_shape_and_start(self) -> None:
        option = Option(strike=105.0, spot=100.0, rate=0.025,
                        maturity=0.4, volatility=0.24)
        paths = StockPriceSimulator(option, n_paths=500, n_steps=50, seed=7).simulate()
        self.assertEqual(paths.shape, (500, 51))
        self.assertTrue(np.allclose(paths[:, 0], 100.0))
        self.assertTrue((paths > 0).all())

    def test_terminal_mean_matches_risk_neutral_drift(self) -> None:
        option = Option(strike=105.0, spot=100.0, rate=0.025,
                        maturity=0.4, volatility=0.24)
        paths = StockPriceSimulator(option, n_paths=200_000, n_steps=20, seed=11).simulate()
        expected = 100.0 * math.exp(0.025 * 0.4)
        self.assertAlmostEqual(paths[:, -1].mean(), expected, delta=0.15)

    def test_seed_is_reproducible(self) -> None:
        option = Option(spot=100.0, maturity=1.0, volatility=0.2)
        a = StockPriceSimulator(option, 10, 10, seed=3).simulate()
        b = StockPriceSimulator(option, 10, 10, seed=3).simulate()
        self.assertTrue(np.array_equal(a, b))


class TestHedging(unittest.TestCase):
    def setUp(self) -> None:
        self.option = Option(strike=105.0, spot=100.0, rate=0.025,
                             maturity=0.4, volatility=0.24)
        self.pricer = OptionPricer("C")

    def test_first_step_is_zero(self) -> None:
        paths = StockPriceSimulator(self.option, 50, 40, seed=1).simulate()
        result = PnLCalculator(self.option, self.pricer, 40).run(paths)
        self.assertTrue(np.allclose(result.hedging_error[:, 0], 0.0))
        self.assertTrue(np.allclose(result.pnl_no_hedge[:, 0], 0.0))

    def test_error_shrinks_with_finer_rebalancing(self) -> None:
        spreads = []
        for steps in (20, 320):
            paths = StockPriceSimulator(self.option, 4000, steps, seed=5).simulate()
            result = PnLCalculator(self.option, self.pricer, steps).run(paths)
            spreads.append(result.final_hedging_error.std(ddof=1))
        # Discretisation error decays like 1/sqrt(steps): 16x the steps should
        # cut the spread by roughly 4x.
        self.assertLess(spreads[1], spreads[0] / 3.0)

    def test_unhedged_pnl_is_capped_by_premium(self) -> None:
        paths = StockPriceSimulator(self.option, 2000, 50, seed=2).simulate()
        result = PnLCalculator(self.option, self.pricer, 50).run(paths)
        premium = self.pricer.price(self.option)
        self.assertLessEqual(result.final_pnl_no_hedge.max(), premium + 1e-9)

    def test_rejects_wrong_path_length(self) -> None:
        calculator = PnLCalculator(self.option, self.pricer, 10)
        with self.assertRaises(ValueError):
            calculator.run(np.ones((3, 5)))


class TestTask2AgainstReport(unittest.TestCase):
    def test_reproduces_cpp_report_table(self) -> None:
        output = task2_module.run(Task2Config(make_figures=False), Paths())
        comparison = validation.compare(output.frame)
        self.assertIsNotNone(comparison, "reference table did not align with the run")
        self.assertLess(comparison.max_abs_diff["implied_vol"], 1e-5)
        self.assertLess(comparison.max_abs_diff["pnl_no_hedge"], 0.05)
        self.assertLess(comparison.max_abs_diff["pnl_hedge"], 0.05)
        self.assertTrue(comparison.matches)


if __name__ == "__main__":
    unittest.main()
