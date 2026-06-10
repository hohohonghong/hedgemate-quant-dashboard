#!/usr/bin/env python3
"""Bee-cast safe-mode patches for the HedgeMate dashboard server.

Bee-cast runs the app on a small single tenant. Full portfolio reanalysis can be
killed by the platform while the already-built active artifact bundle is enough
for same-ticker QA and review flows. This patch is intentionally loaded only by
the Bee-cast wrapper, not by the local development server.
"""

import copy
import json
import uuid

import serve_dashboard as s


_original_launch_saved_portfolio_analysis = s.launch_saved_portfolio_analysis


def _safe_snapshot_manifest(prepared_request):
    manifest = s.read_product_manifest()
    if not isinstance(manifest, dict) or not manifest:
        return None, "active product manifest is missing"

    bundle = s.active_bundle(manifest)
    active_tickers = s.normalize_ticker_list(s.active_bundle_ticker_list(manifest, bundle))
    requested_tickers = s.normalize_ticker_list(prepared_request.get("portfolioTickers") or [])
    if not requested_tickers:
        return None, "requested portfolio tickers are missing"
    if set(active_tickers) != set(requested_tickers):
        return None, (
            "server safe mode can only reuse the active bundle for the same ticker set "
            f"(active={active_tickers}, requested={requested_tickers})"
        )

    fingerprint = prepared_request.get("portfolioInputFingerprint")
    input_sha = prepared_request.get("portfolioInputSha256")
    if not isinstance(fingerprint, dict) or not fingerprint.get("hash") or not input_sha:
        return None, "requested portfolio fingerprint is missing"

    snapshot = copy.deepcopy(manifest)
    snapshot_bundle = snapshot.setdefault("active_bundle", {})
    if not isinstance(snapshot_bundle, dict):
        snapshot_bundle = {}
        snapshot["active_bundle"] = snapshot_bundle

    snapshot["portfolio_input_fingerprint"] = fingerprint
    snapshot["portfolioInputSha256"] = input_sha
    snapshot["portfolioTickers"] = requested_tickers
    snapshot["portfolioInputPersisted"] = True
    snapshot_bundle["portfolio_input_fingerprint"] = fingerprint
    snapshot_bundle["portfolioInputSha256"] = input_sha
    snapshot_bundle["portfolioTickers"] = requested_tickers
    snapshot_bundle["portfolioInputPersisted"] = True

    snapshot.setdefault("server_safe_mode_snapshots", [])
    if isinstance(snapshot["server_safe_mode_snapshots"], list):
        snapshot["server_safe_mode_snapshots"].append(
            {
                "createdAtUtc": s._now_iso(),
                "runId": prepared_request.get("runId"),
                "sourceRunId": snapshot_bundle.get("hedgemate_run") or snapshot.get("active_hedgemate_run"),
                "portfolioFingerprintHash": fingerprint.get("hash"),
                "note": (
                    "Bee-cast server safe mode reused active analysis artifacts for a saved portfolio "
                    "with the same ticker set to avoid resource-heavy subprocess execution."
                ),
            }
        )
    return snapshot, None


def _complete_safe_snapshot(prepared_request):
    manifest, error = _safe_snapshot_manifest(prepared_request)
    job_id = prepared_request.get("jobId") or uuid.uuid4().hex
    started_at = s._now_iso()

    if error:
        s.mark_portfolio_run_failed(prepared_request, error)
        with s.RUN_JOBS_LOCK:
            s.RUN_JOBS[job_id] = {
                "jobId": job_id,
                "status": "failed",
                "stage": "server safe mode",
                "currentStep": "server safe mode skipped heavy analysis",
                "estimatedRemainingMessage": error,
                "lastHeartbeatAt": started_at,
                "elapsedSeconds": 0,
                "timeoutSeconds": s.JOB_TIMEOUT_SECONDS,
                "runId": prepared_request.get("runId"),
                "error": error,
                "diagnostics": {"stage": "server safe mode", "summary": error},
                "result": None,
                "portfolioTickers": prepared_request.get("portfolioTickers") or [],
                "portfolioInputSha256": prepared_request.get("portfolioInputSha256"),
                "portfolioInputFingerprintHash": prepared_request.get("portfolioInputFingerprintHash"),
                "startedAt": started_at,
                "completedAt": started_at,
            }
        return s._snapshot_run_job(job_id)

    run_id = prepared_request.get("runId")
    target = s.cache_manifest_path(run_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    entry = {
        "runId": run_id,
        "cacheKey": prepared_request.get("analysisCacheKey"),
        "manifestPath": s.portable_analysis_manifest_path(target),
        "portfolioRequestHash": (prepared_request.get("portfolioRequestFingerprint") or {}).get("hash"),
        "portfolioRequestCanonical": (prepared_request.get("portfolioRequestFingerprint") or {}).get("canonical"),
        "portfolioFingerprintHash": prepared_request.get("portfolioInputFingerprintHash"),
        "portfolioInputSha256": prepared_request.get("portfolioInputSha256"),
        "portfolioTickers": prepared_request.get("portfolioTickers") or [],
        "dataVersion": prepared_request.get("dataVersion"),
        "generatedAtUtc": manifest.get("generated_at_utc") or s._now_iso(),
        "engineVersion": f"{s.ANALYSIS_ENGINE_VERSION}_server_safe_snapshot",
    }
    if entry.get("cacheKey"):
        index = s.read_analysis_cache_index()
        index.setdefault("entries", {})[entry["cacheKey"]] = entry
        s.write_analysis_cache_index(index)

    s.mark_portfolio_run_success(
        prepared_request,
        result={
            "ok": True,
            "cached": True,
            "serverSafeMode": True,
            "runId": run_id,
            "portfolioInputSha256": prepared_request.get("portfolioInputSha256"),
            "portfolioInputFingerprintHash": prepared_request.get("portfolioInputFingerprintHash"),
        },
        cache_entry=entry,
    )
    with s.RUN_JOBS_LOCK:
        s.RUN_JOBS[job_id] = {
            "jobId": job_id,
            "status": "completed",
            "stage": "server safe mode snapshot",
            "currentStep": "server safe mode reused active analysis artifacts",
            "estimatedRemainingMessage": "",
            "lastHeartbeatAt": started_at,
            "elapsedSeconds": 0,
            "timeoutSeconds": s.JOB_TIMEOUT_SECONDS,
            "runId": run_id,
            "error": None,
            "diagnostics": None,
            "result": {
                "ok": True,
                "cached": True,
                "serverSafeMode": True,
                "runId": run_id,
                "cacheKey": prepared_request.get("analysisCacheKey"),
                "portfolioInputSha256": prepared_request.get("portfolioInputSha256"),
                "portfolioInputFingerprintHash": prepared_request.get("portfolioInputFingerprintHash"),
                "portfolioTickers": prepared_request.get("portfolioTickers") or [],
            },
            "portfolioTickers": prepared_request.get("portfolioTickers") or [],
            "portfolioInputSha256": prepared_request.get("portfolioInputSha256"),
            "portfolioInputFingerprintHash": prepared_request.get("portfolioInputFingerprintHash"),
            "startedAt": started_at,
            "completedAt": started_at,
        }
    return s._snapshot_run_job(job_id)


def launch_saved_portfolio_analysis(user_id, portfolio_id, payload=None, runner=None, thread_factory=None):
    if not s.server_safe_mode():
        return _original_launch_saved_portfolio_analysis(
            user_id,
            portfolio_id,
            payload=payload,
            runner=runner or s.subprocess.run,
            thread_factory=thread_factory or s.threading.Thread,
        )

    store = s.persistence_store()
    portfolio = store.get_portfolio(user_id, portfolio_id)
    if not portfolio:
        raise FileNotFoundError("Portfolio not found")

    extra = dict(payload or {})
    for key in ("portfolioRows", "assets", "portfolioId", "portfolio_id"):
        extra.pop(key, None)
    job_id = extra.get("jobId") or uuid.uuid4().hex
    run_payload = s.portfolio_record_to_run_payload(portfolio, extra)
    run_payload["jobId"] = job_id
    prepared = s.prepare_run_request(run_payload, job_id=job_id)
    run_db_id = store.create_portfolio_run(
        user_id,
        portfolio.get("portfolioId"),
        portfolio.get("portfolioHash"),
        prepared.get("runId"),
        data_version=prepared.get("dataVersion"),
        status="RUNNING",
    )
    prepared.update(
        {
            "userId": int(user_id),
            "portfolioId": int(portfolio.get("portfolioId")),
            "portfolioHash": portfolio.get("portfolioHash"),
            "portfolioRunDbId": run_db_id,
            "forceReanalysis": bool(run_payload.get("forceReanalysis")),
            "ignoreAnalysisCache": bool(run_payload.get("ignoreAnalysisCache")),
        }
    )
    job = _complete_safe_snapshot(prepared)
    db_run = store.get_portfolio_run_by_run_id(user_id, prepared.get("runId"))
    job["portfolioId"] = str(portfolio.get("portfolioId"))
    job["portfolioHash"] = portfolio.get("portfolioHash")
    job["portfolioRun"] = s.run_row_response(db_run)
    return job


s.launch_saved_portfolio_analysis = launch_saved_portfolio_analysis
