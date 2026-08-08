"""
test_agent.py
Unit tests for NL2Pandas Engine core modules.
"""

import unittest
import pandas as pd
from executor import execute_plan, _validate_columns
from validator import validate_execution


class TestNL2PandasEngine(unittest.TestCase):

    def setUp(self):
        """Set up a mock dataset for testing execution primitives."""
        self.sample_df = pd.DataFrame({
            "Department": ["Sales", "Sales", "Engineering", "Engineering", "HR"],
            "Salary": [100000, 120000, 140000, 160000, 90000],
            "Gender": ["Female", "Male", "Female", "Male", "Female"]
        })

    def test_column_validation_pass(self):
        """Test that column validation succeeds when referenced columns exist."""
        plan = {"target_column": "Salary", "group_by": "Department"}
        err = _validate_columns(self.sample_df, plan)
        self.assertIsNone(err)

    def test_column_validation_fail(self):
        """Test that column validation fails when referenced columns are missing."""
        plan = {"target_column": "NonExistentColumn"}
        err = _validate_columns(self.sample_df, plan)
        self.assertIsNotNone(err)
        self.assertIn("Columns not found", err)

    def test_aggregate_sum_execution(self):
        """Test scalar aggregation (sum) execution."""
        plan = {
            "operation": "aggregate",
            "target_column": "Salary",
            "aggregation": "sum",
            "filters": []
        }
        res = execute_plan(self.sample_df, plan)
        self.assertTrue(res["success"])
        self.assertEqual(res["result_data"], 610000)

    def test_group_aggregate_execution(self):
        """Test grouped mean calculation."""
        plan = {
            "operation": "group_aggregate",
            "target_column": "Salary",
            "group_by": "Department",
            "aggregation": "mean",
            "filters": []
        }
        res = execute_plan(self.sample_df, plan)
        self.assertTrue(res["success"])
        self.assertIsInstance(res["result_data"], pd.DataFrame)

    def test_validator_defensive_null_guard(self):
        """Test that validator defensively handles invalid execution objects."""
        is_valid, err_msg = validate_execution(None)
        self.assertFalse(is_valid)
        self.assertIn("Execution failed", err_msg)


if __name__ == "__main__":
    unittest.main()