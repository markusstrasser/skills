#!/usr/bin/env python3
"""Post-estimation sensitivity analysis via PySensemakr.

Quantifies how robust a causal estimate is to unmeasured confounding
using the Cinelli-Hazlett omitted variable bias (OVB) framework.

Usage:
    uv run --with PySensemakr python3 sensitivity_check.py \
        --formula "Y ~ X + C1 + C2" --data data.csv --treatment X --benchmark C1,C2
    uv run --with PySensemakr python3 sensitivity_check.py --test

Requires: PySensemakr, statsmodels, pandas, numpy
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from typing import Any


def run_sensitivity(formula: str, data_path: str, treatment: str,
                    benchmark_covariates: list[str] | None = None,
                    alpha: float = 0.05) -> dict[str, Any]:
    """Run sensitivity analysis on a fitted OLS model."""
    try:
        import pandas as pd
        import statsmodels.formula.api as smf
        import sensemakr as sm
    except ImportError as e:
        return {"error": f"Missing dependency: {e}. Run with: uv run --with PySensemakr"}

    # Load data
    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        return {"error": f"Failed to load data: {e}"}

    # Fit model
    try:
        model = smf.ols(formula, data=df).fit()
    except Exception as e:
        return {"error": f"Failed to fit model: {e}"}

    # Check treatment is in model
    if treatment not in model.params:
        return {"error": f"Treatment '{treatment}' not found in model parameters: {list(model.params.index)}"}

    # Run sensemakr — first without benchmarks (always works), then with benchmarks
    estimate = float(model.params[treatment])
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            sensitivity = sm.Sensemakr(
                model=model,
                treatment=treatment,
                q=1.0,
                alpha=alpha,
            )
    except Exception as e:
        return {"error": f"Sensemakr failed: {e}"}

    rv = float(sensitivity.sensitivity_stats["rv_q"])
    rv_alpha = float(sensitivity.sensitivity_stats["rv_qa"])

    # Benchmark bounds (PySensemakr has pandas compat issues — handle gracefully)
    bounds: list[dict[str, Any]] = []
    benchmark_warning: str | None = None
    if benchmark_covariates:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                sens_bench = sm.Sensemakr(
                    model=model,
                    treatment=treatment,
                    benchmark_covariates=benchmark_covariates,
                    q=1.0,
                    alpha=alpha,
                )
            if hasattr(sens_bench, "bounds") and sens_bench.bounds is not None:
                for _, row in sens_bench.bounds.iterrows():
                    bounds.append({
                        "benchmark": str(row.get("bound_label", "")),
                        "r2yd_x": round(float(row.get("r2yd_x", 0)), 4),
                        "r2dz_x": round(float(row.get("r2dz_x", 0)), 4),
                        "adjusted_estimate": round(float(row.get("adjusted_estimate", 0)), 4),
                        "adjusted_se": round(float(row.get("adjusted_se", 0)), 4),
                    })
        except Exception:
            # PySensemakr has known pandas compat issues with benchmark computation.
            # Fall back to exact partial-R2 calculations using the fitted model and
            # an auxiliary treatment-on-covariates regression.
            try:
                import statsmodels.api as sm_api

                exog_names = list(model.model.exog_names)
                exog = model.model.exog
                treat_idx = exog_names.index(treatment)
                y_treat = exog[:, treat_idx]
                aux_keep = [idx for idx, name in enumerate(exog_names) if name != treatment]
                aux_names = [exog_names[idx] for idx in aux_keep]
                aux_exog = exog[:, aux_keep]
                aux_fit = sm_api.OLS(y_treat, aux_exog).fit()
                aux_dof = float(aux_fit.df_resid)

                for cov in benchmark_covariates:
                    if cov in model.params:
                        t_y = float(model.tvalues[cov])
                        dof_y = float(model.df_resid)
                        r2_y = (t_y * t_y) / (t_y * t_y + dof_y)

                        if cov not in aux_names:
                            continue
                        t_d = float(aux_fit.tvalues[aux_names.index(cov)])
                        r2_d = (t_d * t_d) / (t_d * t_d + aux_dof)
                        bounds.append({
                            "benchmark": f"1x {cov}",
                            "r2yd_x": round(r2_y, 4),
                            "r2dz_x": round(r2_d, 4),
                            "adjusted_estimate": 0.0,
                            "adjusted_se": 0.0,
                        })
                benchmark_warning = (
                    "Benchmark bounds computed via fallback. "
                    "PySensemakr ovb_bounds has a pandas compatibility issue on this stack."
                )
            except Exception:
                benchmark_warning = "Benchmark computation failed due to PySensemakr pandas compat issue."

    # Determine fragility
    max_benchmark_r2 = 0.0
    if bounds:
        max_benchmark_r2 = max(b["r2yd_x"] for b in bounds)

    if max_benchmark_r2 > 0:
        rv_ratio = rv / max_benchmark_r2
        if rv_ratio > 2:
            interpretation = (
                f"Robust. RV={rv:.3f} is {rv_ratio:.1f}x the strongest benchmark "
                f"(R2={max_benchmark_r2:.3f}). An omitted confounder would need to be "
                f"much stronger than any observed covariate to explain away the effect."
            )
            fragile = False
        elif rv_ratio > 1:
            interpretation = (
                f"Moderate. RV={rv:.3f} is {rv_ratio:.1f}x the strongest benchmark "
                f"(R2={max_benchmark_r2:.3f}). The effect is not easily explained away, "
                f"but a confounder moderately stronger than observed covariates could."
            )
            fragile = False
        else:
            interpretation = (
                f"Fragile. RV={rv:.3f} is only {rv_ratio:.1f}x the strongest benchmark "
                f"(R2={max_benchmark_r2:.3f}). A confounder as strong as an observed "
                f"covariate could explain away the effect. Revisit DAG for missing confounders."
            )
            fragile = True
    else:
        interpretation = (
            f"RV={rv:.3f}. No benchmark covariates provided for comparison. "
            f"Consider adding --benchmark to assess relative robustness."
        )
        fragile = rv < 0.05  # very weak without benchmark

    result = {
        "treatment": treatment,
        "estimate": round(estimate, 6),
        "robustness_value": round(rv, 4),
        "rv_alpha": round(rv_alpha, 4),
        "benchmark_bounds": bounds,
        "interpretation": interpretation,
        "fragile": fragile,
    }
    if benchmark_warning:
        result["benchmark_warning"] = benchmark_warning
    return result


def run_tests():
    """Built-in tests using Darfur dataset from PySensemakr."""
    passed = 0
    failed = 0

    print("Running sensitivity_check tests...\n")

    try:
        import numpy as np
        import pandas as pd
        import sensemakr as sm
    except ImportError as e:
        print(f"  [SKIP] Missing dependency: {e}")
        sys.exit(0)

    import tempfile
    import os

    # Use built-in Darfur dataset (canonical PySensemakr example)
    darfur = sm.load_darfur()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        darfur.to_csv(f, index=False)
        darfur_path = f.name

    # Test 1: Basic run (no benchmarks — avoids pandas compat issue)
    result = run_sensitivity(
        formula="peacefactor ~ directlyharmed + age + farmer_dar + herder_dar + female",
        data_path=darfur_path,
        treatment="directlyharmed",
    )
    if "error" not in result and "robustness_value" in result and result["robustness_value"] > 0:
        passed += 1
        print(f"  [PASS] Basic run (RV={result['robustness_value']:.4f})")
    else:
        failed += 1
        print(f"  [FAIL] Basic run: {result}")

    # Test 2: JSON output schema
    required_keys = {"treatment", "estimate", "robustness_value", "rv_alpha",
                     "benchmark_bounds", "interpretation", "fragile"}
    if required_keys.issubset(result.keys()):
        passed += 1
        print("  [PASS] JSON output schema complete")
    else:
        failed += 1
        missing = required_keys - result.keys()
        print(f"  [FAIL] Missing keys: {missing}")

    # Test 3: With benchmarks (may hit pandas compat — should not crash)
    result_bench = run_sensitivity(
        formula="peacefactor ~ directlyharmed + age + farmer_dar + herder_dar + female",
        data_path=darfur_path,
        treatment="directlyharmed",
        benchmark_covariates=["female", "age"],
    )
    if "error" not in result_bench and result_bench["robustness_value"] > 0:
        passed += 1
        has_bounds = len(result_bench["benchmark_bounds"]) > 0
        has_warning = "benchmark_warning" in result_bench
        print(f"  [PASS] Benchmark run (bounds={has_bounds}, fallback={'yes' if has_warning else 'no'})")
    else:
        failed += 1
        print(f"  [FAIL] Benchmark run: {result_bench}")

    # Test 4: Very low RV detection — pure noise treatment (no real effect)
    np.random.seed(123)
    n = 1000
    noise_x = np.random.normal(0, 1, n)
    y = np.random.normal(0, 1, n)  # outcome independent of treatment
    df_fragile = pd.DataFrame({"X": noise_x, "Y": y})
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df_fragile.to_csv(f, index=False)
        fragile_path = f.name

    result_fragile = run_sensitivity(
        formula="Y ~ X", data_path=fragile_path, treatment="X",
    )
    # RV should be very low for a null effect
    if "error" not in result_fragile and result_fragile["robustness_value"] < 0.1:
        passed += 1
        print(f"  [PASS] Low RV for null effect (RV={result_fragile['robustness_value']:.4f})")
    else:
        failed += 1
        print(f"  [FAIL] Expected low RV, got: {result_fragile.get('robustness_value')}")

    # Test 5: Bad data path
    result_bad = run_sensitivity(
        formula="Y ~ X", data_path="/nonexistent.csv", treatment="X"
    )
    if "error" in result_bad:
        passed += 1
        print("  [PASS] Bad data path returns error")
    else:
        failed += 1
        print("  [FAIL] Bad data path should return error")

    # Test 6: Treatment not in model
    result_missing = run_sensitivity(
        formula="peacefactor ~ age + female",
        data_path=darfur_path,
        treatment="directlyharmed",
    )
    if "error" in result_missing:
        passed += 1
        print("  [PASS] Missing treatment in model returns error")
    else:
        failed += 1
        print("  [FAIL] Missing treatment should return error")

    # Cleanup
    os.unlink(darfur_path)
    os.unlink(fragile_path)

    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)


def main():
    parser = argparse.ArgumentParser(description="Sensitivity analysis via PySensemakr")
    parser.add_argument("--formula", "-f", help="OLS formula (e.g., 'Y ~ X + C1 + C2')")
    parser.add_argument("--data", "-d", help="Path to CSV data file")
    parser.add_argument("--treatment", "-t", help="Treatment variable name")
    parser.add_argument("--benchmark", "-b", help="Benchmark covariates as 'C1,C2,...'")
    parser.add_argument("--alpha", type=float, default=0.05, help="Significance level (default: 0.05)")
    parser.add_argument("--test", action="store_true", help="Run built-in test cases")
    args = parser.parse_args()

    if args.test:
        run_tests()
        return

    if not (args.formula and args.data and args.treatment):
        parser.print_help()
        sys.exit(1)

    benchmarks = [b.strip() for b in args.benchmark.split(",")] if args.benchmark else None

    result = run_sensitivity(
        formula=args.formula,
        data_path=args.data,
        treatment=args.treatment,
        benchmark_covariates=benchmarks,
        alpha=args.alpha,
    )
    json.dump(result, sys.stdout, indent=2)
    print()
    sys.exit(1 if "error" in result else 0)


if __name__ == "__main__":
    main()
