"""
Edge Lab CLI

Command-line interface for running Edge Lab pipelines.
"""

import sys
import json
import uuid
from datetime import datetime
from typing import Optional

import click

from .db.session import get_session, init_db
from .adapters import AdapterRegistry
from .pipelines import SnapshotPipeline, FeatureEngine, PredictionPipeline, EvaluationPipeline
from .config import get_config


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Edge Lab - Point-in-time financial prediction system"""
    pass


@cli.command("init-db")
@click.option("--drop", is_flag=True, help="Drop existing schema first")
def init_database(drop: bool):
    """Initialize the edgelab database schema"""
    click.echo("Initializing Edge Lab database...")
    
    try:
        init_db(drop_existing=drop)
        click.echo("✓ Database initialized successfully")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command("daily-scan")
@click.option("--as-of", required=True, help="Point-in-time timestamp (ISO format)")
@click.option("--policy", default="US_LIQUID_V1", help="Universe policy name")
@click.option("--adapter", default=None, help="Data adapter (mock, yfinance)")
@click.option("--history-days", default=252, help="Days of history to fetch")
@click.option("--output", "-o", default=None, help="Output file for results")
def daily_scan(
    as_of: str,
    policy: str,
    adapter: Optional[str],
    history_days: int,
    output: Optional[str]
):
    """
    Run daily scan pipeline.
    
    Creates snapshot and generates daily scan predictions.
    """
    try:
        as_of_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    except ValueError:
        click.echo(f"✗ Invalid date format: {as_of}", err=True)
        sys.exit(1)
    
    config = get_config()
    adapter_name = adapter or config.default_adapter
    
    click.echo(f"Running daily scan for {as_of_dt.isoformat()}")
    click.echo(f"  Policy: {policy}")
    click.echo(f"  Adapter: {adapter_name}")
    
    with get_session() as session:
        try:
            # Get adapter
            data_adapter = AdapterRegistry.get(adapter_name)
            
            # Run snapshot pipeline
            click.echo("\n[1/3] Creating snapshot...")
            snapshot_pipeline = SnapshotPipeline(session, data_adapter)
            snapshot, snap_warnings = snapshot_pipeline.run(
                as_of=as_of_dt,
                policy_name=policy,
                history_days=history_days
            )
            
            for w in snap_warnings:
                click.echo(f"  ⚠ {w}")
            
            click.echo(f"  ✓ Snapshot created: {snapshot.snapshot_id}")
            click.echo(f"    Hash: {snapshot.snapshot_hash[:16]}...")
            
            # Run feature engine
            click.echo("\n[2/3] Computing features...")
            feature_engine = FeatureEngine(session)
            feature_set_id, feature_count = feature_engine.run(snapshot.snapshot_id)
            click.echo(f"  ✓ Computed {feature_count} feature rows")
            
            # Run prediction
            click.echo("\n[3/3] Generating predictions...")
            pred_pipeline = PredictionPipeline(session)
            pred_run, predictions, pred_warnings = pred_pipeline.run(
                snapshot_id=snapshot.snapshot_id,
                feature_set_id=feature_set_id,
                task="daily_scan",
                horizon=1
            )
            
            for w in pred_warnings:
                click.echo(f"  ⚠ {w}")
            
            click.echo(f"  ✓ Generated {len(predictions)} predictions")
            
            # Output results
            result = {
                "ok": True,
                "ids": {
                    "snapshot_id": str(snapshot.snapshot_id),
                    "prediction_run_id": str(pred_run.prediction_run_id),
                },
                "warnings": snap_warnings + pred_warnings,
                "audit": {
                    "as_of": as_of_dt.isoformat(),
                    "snapshot_hash": snapshot.snapshot_hash,
                    "policy": policy,
                    "adapter": adapter_name,
                },
                "top_20": [
                    {
                        "symbol": p.symbol,
                        "score": float(p.score),
                        "confidence": float(p.confidence),
                        "risk_flags": p.risk_flags,
                    }
                    for p in predictions[:20]
                ],
            }
            
            if output:
                with open(output, "w") as f:
                    json.dump(result, f, indent=2)
                click.echo(f"\n✓ Results written to {output}")
            else:
                click.echo("\n" + "=" * 60)
                click.echo("TOP 20 CANDIDATES:")
                click.echo("=" * 60)
                for i, p in enumerate(predictions[:20], 1):
                    flags = ", ".join(p.risk_flags) if p.risk_flags else "none"
                    click.echo(f"{i:2}. {p.symbol:6} score={p.score:+.3f} conf={p.confidence:.2f} flags=[{flags}]")
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            click.echo(f"\n✗ Error: {e}", err=True)
            sys.exit(1)


@cli.command("weekly-predict")
@click.option("--as-of", required=True, help="Point-in-time timestamp (ISO format)")
@click.option("--policy", default="US_LIQUID_V1", help="Universe policy name")
@click.option("--horizon", default=5, help="Prediction horizon in trading days")
@click.option("--adapter", default=None, help="Data adapter")
@click.option("--output", "-o", default=None, help="Output file")
def weekly_predict(
    as_of: str,
    policy: str,
    horizon: int,
    adapter: Optional[str],
    output: Optional[str]
):
    """
    Run weekly prediction pipeline.
    
    Creates snapshot, computes features, and generates weekly predictions.
    """
    try:
        as_of_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    except ValueError:
        click.echo(f"✗ Invalid date format: {as_of}", err=True)
        sys.exit(1)
    
    config = get_config()
    adapter_name = adapter or config.default_adapter
    
    click.echo(f"Running weekly prediction for {as_of_dt.isoformat()}")
    click.echo(f"  Policy: {policy}")
    click.echo(f"  Horizon: {horizon} trading days")
    
    with get_session() as session:
        try:
            # Get adapter
            data_adapter = AdapterRegistry.get(adapter_name)
            
            # Run snapshot pipeline
            click.echo("\n[1/3] Creating snapshot...")
            snapshot_pipeline = SnapshotPipeline(session, data_adapter)
            snapshot, snap_warnings = snapshot_pipeline.run(
                as_of=as_of_dt,
                policy_name=policy
            )
            
            click.echo(f"  ✓ Snapshot: {snapshot.snapshot_id}")
            
            # Run feature engine
            click.echo("\n[2/3] Computing features...")
            feature_engine = FeatureEngine(session)
            feature_set_id, feature_count = feature_engine.run(snapshot.snapshot_id)
            click.echo(f"  ✓ Features: {feature_count} symbols")
            
            # Run prediction
            click.echo("\n[3/3] Generating predictions...")
            pred_pipeline = PredictionPipeline(session)
            pred_run, predictions, pred_warnings = pred_pipeline.run(
                snapshot_id=snapshot.snapshot_id,
                feature_set_id=feature_set_id,
                task="weekly_predict",
                horizon=horizon
            )
            
            click.echo(f"  ✓ Predictions: {len(predictions)}")
            
            # Build output
            result = {
                "ok": True,
                "ids": {
                    "snapshot_id": str(snapshot.snapshot_id),
                    "prediction_run_id": str(pred_run.prediction_run_id),
                },
                "warnings": snap_warnings + pred_warnings,
                "audit": {
                    "as_of": as_of_dt.isoformat(),
                    "snapshot_hash": snapshot.snapshot_hash,
                    "model_hash": pred_run.run_hash[:16],
                    "policy": policy,
                },
                "candidates": [
                    {
                        "rank": i,
                        "symbol": p.symbol,
                        "score": float(p.score),
                        "p_beat_spy": float(p.p_beat_spy) if p.p_beat_spy else None,
                        "exp_return": float(p.exp_return) if p.exp_return else None,
                        "exp_vol": float(p.exp_vol) if p.exp_vol else None,
                        "confidence": float(p.confidence),
                        "risk_flags": p.risk_flags,
                        "top_features": p.top_features,
                    }
                    for i, p in enumerate(predictions[:20], 1)
                ],
            }
            
            if output:
                with open(output, "w") as f:
                    json.dump(result, f, indent=2)
                click.echo(f"\n✓ Written to {output}")
            else:
                click.echo("\n" + json.dumps(result, indent=2))
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            click.echo(f"\n✗ Error: {e}", err=True)
            sys.exit(1)


@cli.command("evaluate")
@click.option("--prediction-run-id", required=True, help="Prediction run ID to evaluate")
@click.option("--top-n", default=20, help="Number of top predictions to evaluate")
@click.option("--output", "-o", default=None, help="Output file")
def evaluate(
    prediction_run_id: str,
    top_n: int,
    output: Optional[str]
):
    """
    Evaluate a prediction run.
    
    Computes metrics like hit rate, average return, and calibration.
    """
    try:
        run_id = uuid.UUID(prediction_run_id)
    except ValueError:
        click.echo(f"✗ Invalid UUID: {prediction_run_id}", err=True)
        sys.exit(1)
    
    click.echo(f"Evaluating prediction run: {run_id}")
    
    with get_session() as session:
        try:
            eval_pipeline = EvaluationPipeline(session)
            eval_run, metrics, warnings = eval_pipeline.run(
                prediction_run_id=run_id,
                top_n=top_n
            )
            
            for w in warnings:
                click.echo(f"  ⚠ {w}")
            
            if metrics:
                result = {
                    "ok": True,
                    "evaluation_run_id": str(eval_run.evaluation_run_id),
                    "prediction_run_id": str(run_id),
                    "metrics": metrics.to_dict(),
                    "warnings": warnings,
                }
                
                if output:
                    with open(output, "w") as f:
                        json.dump(result, f, indent=2)
                    click.echo(f"\n✓ Written to {output}")
                else:
                    click.echo(f"\n✓ Evaluation complete")
                    click.echo(f"  Hit Rate: {metrics.hit_rate:.1%}")
                    click.echo(f"  Top {top_n} Return: {metrics.top_n_return:.2%}")
                    click.echo(f"  Benchmark Return: {metrics.benchmark_return:.2%}")
                    click.echo(f"  Rank Correlation: {metrics.rank_correlation:.3f}")
            else:
                click.echo("  ✗ Evaluation failed - insufficient data")
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            click.echo(f"\n✗ Error: {e}", err=True)
            sys.exit(1)


@cli.command("list-adapters")
def list_adapters():
    """List available data adapters"""
    adapters = AdapterRegistry.list_adapters()
    click.echo("Available adapters:")
    for name in adapters:
        click.echo(f"  - {name}")


if __name__ == "__main__":
    cli()
