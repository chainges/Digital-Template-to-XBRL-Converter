# Python Backend Instructions: Asynchronous XBRL Report Generation

## Scope

Implement the Python-backend portion of asynchronous XBRL report generation only.

The Python backend currently runs locally. The production target is Google Cloud Functions. Preserve the existing Python backend and XBRL conversion logic wherever possible.

## Goal

The existing HTTP request performs the full report generation synchronously. Refactor the Python backend so that:

1. An HTTP endpoint accepts a report job request and returns quickly with `202 Accepted`.
2. A separate worker processes the job asynchronously.
3. The worker obtains the required report data from Convex using the project's existing integration, generates XBRL, and stores the resulting file in private object storage.
4. The worker records job progress and outcome through a clearly isolated Convex integration layer.
5. Failures are handled explicitly and safely.
6. The code can run locally during development and later be dispatched through Google Cloud Tasks in production.

## First: inspect the existing codebase

Before editing:

- Identify the Python framework and entry points (for example, FastAPI, Flask, or `functions-framework`).
- Find the existing endpoint that generates the XBRL report.
- Trace how it fetches data from Convex and invokes the XBRL mapper/builder.
- Identify current storage, email, authentication, configuration, logging, and dependency patterns.
- Reuse existing code and conventions. Avoid rewriting the XBRL transformation logic unless necessary.
- Check current tests and add tests consistent with the repository.
- Do not invent Convex table names, field names, endpoint URLs, or authentication schemes. Use existing definitions and configuration; if required details are missing, isolate them behind interfaces and document the missing configuration.

## Required design

Separate the backend into the following responsibilities. Names are suggestions; adapt them to the existing repository.

### 1. HTTP job-submission endpoint

Add or refactor an endpoint such as `POST /generate-report`.

Responsibilities:

- Authenticate the caller using the existing backend authentication approach.
- Validate the request and verify that the caller may generate a report for the requested company and reporting year.
- Accept a stable job identifier (`jobId`) or create one through the established job-creation integration.
- Enqueue the job using an abstraction such as `ReportJobDispatcher`.
- Return `202 Accepted` promptly with a small response such as:
  ```json
  {
    "jobId": "example-job-id",
    "status": "queued"
  }
  ```
- Do not fetch the full report dataset, convert XBRL, upload the file, or send completion email within this request.
- Do not accept arbitrary user-provided file paths, storage keys, or trusted identity fields.
- Handle dispatch failures explicitly. Do not return success if dispatch failed unless a durable dispatch/reconciliation mechanism guarantees recovery.
- Prevent duplicate work through idempotency or deterministic job identifiers where feasible.

### 2. Job dispatcher abstraction

Create a small interface for dispatching jobs, with implementations appropriate to each environment.

**Local development:**

- A simple in-process queue may be used temporarily for local development only.
- Clearly document that in-memory queued work is lost on process restart and is not production-safe.
- Use a worker loop that consumes jobs and always acknowledges/completes queue bookkeeping in a `finally` block.
- Do not use an untracked `asyncio.create_task()` or fire-and-forget thread as the sole production mechanism.

**Production:**

- Add a Google Cloud Tasks dispatcher (or a clearly defined adapter point if production credentials/configuration are not available in the current environment).
- The task should contain only the job identifier and necessary non-sensitive metadata, not the full company dataset.
- Configure the task to call a protected worker endpoint.
- Use authenticated service-to-service invocation, such as Cloud Tasks OIDC authentication, with correct audience and IAM permissions.
- Use deterministic task names or equivalent duplicate protection where practical. Treat an “already exists” response as an idempotency case when appropriate.
- Configure queue retry settings and HTTP dispatch timeout in line with the actual Cloud Function generation and its execution timeout.
- Do not assume the function timeout exceeds the Cloud Tasks timeout. If expected work can exceed either limit, document that a separately managed Cloud Run Job/worker will be needed instead.

### 3. Worker endpoint and report service

Provide a protected worker entry point, such as `POST /internal/process-report`.

Responsibilities:

1. Authenticate the dispatcher or worker caller. Do not expose an unrestricted endpoint that anyone can use to run jobs.
2. Validate the payload and load the authoritative job record.
3. Check the job's current status and enforce idempotency.
4. If already completed, acknowledge the duplicate delivery without regenerating the report.
5. Mark the job as processing using a conditional/status-aware update.
6. Fetch the report data from Convex using the existing integration.
7. Call the existing XBRL conversion logic.
8. Validate that the expected output file was created and is non-empty; apply any existing XBRL validation if available.
9. Upload the file to private object storage.
10. Persist the resulting object key and completion metadata.
11. Mark the job completed only after the upload succeeds and the file is available.
12. Trigger completion notification through a separate notification abstraction if email integration already exists or can be configured.
13. Return a success response to the queue only when the task was handled according to the retry policy.

Keep the worker orchestration separate from the HTTP framework. For example, the core service could expose `process_report(job_id)` so it can be tested and invoked independently of the HTTP endpoint.

### 4. Job status integration with Convex

Isolate Convex access behind a small repository/client interface, for example:

- `get_job(job_id)`
- `mark_processing(job_id, ...)`
- `mark_completed(job_id, file_key, ...)`
- `mark_failed(job_id, safe_error_message, ...)`

Adapt these operations to the actual Convex integration in the codebase. Do not invent API contracts.

Requirements:

- Verify the job exists and is valid before processing.
- Use conditional/status-aware updates so delayed retries cannot overwrite a completed job with `processing` or `failed`.
- Do not expose privileged Convex credentials to browser-facing responses.
- Do not allow ordinary clients to set arbitrary job statuses.
- Store safe, user-facing failure information separately from detailed internal logs.
- If the current Python backend can fetch Convex data but cannot update job records, implement a clearly isolated adapter/interface and document the required secure server-to-server Convex endpoint or mutation integration. Do not silently skip status updates.

### 5. Object storage

Use the project's existing storage integration if one exists. Otherwise, implement a storage abstraction with Google Cloud Storage as the likely production adapter, while keeping local testing possible.

Requirements:

- Store generated reports in a private bucket.
- Use deterministic object keys based on trusted job/company/report metadata, for example:
  `reports/{company_id}/{reporting_year}/{job_id}.xbrl`
- Sanitize and validate key components. Never use arbitrary user-provided paths.
- Do not make report objects publicly readable.
- Store the object key in job metadata, not a permanent public URL.
- Do not embed credentials in source code.
- Ensure upload completion and error handling occur before marking a job completed.
- Provide a secure download integration point for a future authenticated download endpoint; signed URLs should be short-lived and issued only after authorization.

### 6. Email notification

Do not make email delivery part of the core report-generation success condition.

- Trigger a notification after successful storage and completed-status persistence.
- Use the project's existing email provider if present. Otherwise, isolate notification delivery behind an interface and document the needed configuration.
- Make notification delivery retryable and idempotent where feasible.
- If email fails, the report remains completed and downloadable.
- Do not send public, permanent bucket URLs. Prefer an authenticated application download page or short-lived signed URL.
- Avoid sending duplicate emails if a queue delivery is retried.

### 7. Failure and retry policy

Classify errors into at least:

- **Permanent failures:** invalid request, missing required data, invalid reporting period, deterministic XBRL validation errors. Mark the job failed and acknowledge the task if retrying cannot help.
- **Transient failures:** temporary Convex/API errors, rate limits, storage/network errors. Return a retryable failure or use the dispatch system's retry mechanism.
- **Unexpected failures:** log the full exception with job ID and correlation details, expose only a safe error message, and apply a bounded retry policy.

Additional requirements:

- Do not swallow exceptions and then report success.
- Avoid overwriting successful job state on delayed retries.
- Prevent concurrent duplicate workers from generating the same job where feasible, using conditional status transitions, a lease/claim, or an equivalent mechanism.
- Configure bounded retries and backoff; avoid infinite retry loops.
- Add a recovery/reconciliation strategy for jobs left queued or processing after a crash.
- Keep secrets, access tokens, personal data, and full report contents out of logs.

## Suggested job lifecycle

Use the statuses already established by the application if they exist. Otherwise, use:

- `queued`
- `processing`
- `completed`
- `failed`

Optional fields may include `startedAt`, `completedAt`, `fileKey`, a safe `errorMessage`, attempt count, lease/heartbeat information, and notification state. Do not modify the Convex schema from this Python-only task; document required fields for the owner of that schema.

## Configuration

Use environment variables or the project's existing configuration system. Never hardcode secrets.

Potential settings (adapt to existing conventions):

- `REPORT_DISPATCHER` (`local` or `cloud_tasks`)
- `GCP_PROJECT_ID`
- `GCP_TASKS_LOCATION`
- `GCP_TASKS_QUEUE`
- `REPORT_WORKER_URL`
- `REPORT_WORKER_AUDIENCE`
- `TASK_INVOKER_SERVICE_ACCOUNT`
- `REPORT_STORAGE_BACKEND` (`local` for development or `gcs` for production)
- `GCS_BUCKET_NAME`
- Existing Convex API URL and server-side credentials/settings
- Existing email provider settings
- Worker authentication settings

Validate required configuration on startup or when the relevant adapter is initialized. Do not print secret values.

## Local development expectations

- The backend must remain runnable on localhost.
- Use a local dispatcher/queue for initial development only, unless the project already has a durable local queue.
- Make the worker logic independently callable and testable.
- Use the existing Convex development environment only through configured credentials.
- For storage, use the configured private GCS bucket if available, or a local test adapter for development. Do not silently claim a local file is a cloud upload.
- If the frontend is on another local port, configure and restrict CORS appropriately; do not use wildcard CORS with credentials.
- Make it clear that the local queue loses pending work on process restart and must not be used for production.

## Security requirements

- Authenticate job submission and worker invocation.
- Authorize company/report access on the server.
- Protect internal worker endpoints from public arbitrary invocation.
- Keep Convex and cloud credentials server-side.
- Use least-privilege service accounts.
- Keep report files private.
- Do not trust `userId`, company ownership, status, or storage paths supplied by the caller.
- Validate all job IDs and request fields.
- Avoid exposing stack traces or internal infrastructure details to users.

## Testing requirements

Add tests appropriate to the existing project for at least:

1. Submission returns `202` and does not run XBRL generation inline.
2. Invalid or unauthorized requests are rejected.
3. Worker processes a valid queued job successfully.
4. Missing job IDs and unknown jobs are handled safely.
5. Duplicate delivery of a completed job does not regenerate the report or send duplicate email.
6. A permanent XBRL/data-validation failure marks the job failed without endless retries.
7. A transient Convex/storage error is retried according to policy.
8. Upload failure never marks the job completed.
9. Email failure does not change a completed report to failed.
10. A stale/retried task cannot overwrite a completed status.
11. Authentication is required for internal worker execution.
12. Configuration and local startup instructions are documented.

Mock external Convex, storage, queue, and email integrations in unit tests. Avoid requiring production credentials for the test suite.

## Implementation sequence

1. Inspect the repository and summarize the current flow before changing it.
2. Refactor the existing XBRL conversion into a reusable report-generation service without changing its output behavior.
3. Add or isolate the Convex job repository/status integration.
4. Add the dispatcher abstraction and a local-only development queue.
5. Add the protected worker endpoint and idempotent processing logic.
6. Add or adapt private storage handling.
7. Add a notification adapter if the project has the required email configuration.
8. Add tests and local run instructions.
9. Add the Google Cloud Tasks adapter and deployment configuration if the current project/environment supports it. Otherwise, leave a well-defined adapter and list the exact remaining configuration steps.
10. Report what was changed, what remains unimplemented, required environment variables, how to run locally, how to run tests, and production limitations.

## Explicit non-goals

Do not implement these in this task:

- TanStack Start UI changes.
- Convex schema or frontend mutations/queries.
- A new Node.js backend.
- A full cloud infrastructure migration.
- Public storage buckets.
- A permanent public download URL.
- A fabricated progress percentage.
- An in-memory queue presented as production-ready.
- A broad rewrite of the existing XBRL mapping/conversion code.

## Completion criteria

The task is complete when the Python backend can accept a report job, return promptly, process the job separately, update status through the configured integration, safely store the generated XBRL file, handle duplicate/retried deliveries, and pass the relevant tests. Local development must work without production cloud credentials when local/test adapters are selected. Clearly document any external Convex or cloud setup that cannot be completed from the repository alone.
