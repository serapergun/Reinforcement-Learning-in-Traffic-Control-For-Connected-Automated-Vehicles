import unittest
from evaluate_v8_policy_diagnostics import choose, design

class DiagnosticsTests(unittest.TestCase):
    def test_design(self):
        d=design()
        self.assertEqual(len(d),26)
        self.assertEqual(len(set(d)),26)
        self.assertEqual(2*(1+len(d)),54)
    def test_native(self):
        self.assertEqual(choose([.8,.1,.1],[True,True,True],0),0)
    def test_mask(self):
        self.assertEqual(choose([.1,.2,.7],[True,False,False],0),0)
    def test_margin(self):
        self.assertEqual(choose([.3,.1,.6],[True]*3,.15),2)
        self.assertEqual(choose([.3,.1,.6],[True]*3,.35),0)
    def test_short_extension(self):
        self.assertEqual(choose([.2,.7,.1],[True]*3,.15),1)
    def test_tie(self):
        self.assertEqual(choose([.5,.5,0],[True]*3,0),0)
    def test_invalid(self):
        with self.assertRaises(ValueError):
            choose([float('nan'),0,1],[True]*3,.15)

if __name__=='__main__':
    unittest.main()
