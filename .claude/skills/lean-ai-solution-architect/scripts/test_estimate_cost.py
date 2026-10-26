import unittest
from estimate_cost import estimate

class TestCost(unittest.TestCase):
    def test_identical_cost_when_no_cache_or_routing(self):
        r=estimate(100, 1000, 100, 1, 5, 0.1, 0.5, 0, 0)
        self.assertAlmostEqual(r['daily_baseline_usd'],r['daily_optimized_usd'])
    def test_zero_requests_with_infra(self):
        r=estimate(0, 1000, 100, 1, 5, 0.1, 0.5, 0.5, 0.2, infra_day=5)
        self.assertEqual(r['optimized_usd_per_1000_requests'],0)
        self.assertEqual(r['daily_optimized_usd'],5)
    def test_complete_cache_saves_model_calls(self):
        r=estimate(100, 1000, 100, 1, 5, 0.1, 0.5, 0.5, 1)
        self.assertEqual(r['daily_optimized_usd'],0)
        self.assertGreater(r['daily_baseline_usd'],0)

if __name__=='__main__': unittest.main()
