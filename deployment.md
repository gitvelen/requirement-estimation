# deployment.md

## Deployment Plan
target_env: staging
deployment_date: 2026-04-21
deployment_method: manual

## Pre-deployment Checklist
- [x] all acceptance items passed
- [x] required migrations verified
- [x] rollback plan prepared
- [x] smoke checks prepared

## Deployment Steps
1. Deploy the parser-layer code changes for embedded attachment extraction to the staging backend environment.
2. Build and deploy the backend image with the newly locked parser runtime dependency `olefile`; no schema or storage migration is required.
3. Run smoke parsing against the verified regression sample set and confirm the parser returns merged requirement content plus attachment error records for degraded-only payloads.

## Verification Results
- smoke_test: pass
- key_features: recursive extraction for embedded DOCX/XLSX/PPTX/PDF payloads, attachment text merged into requirement_content, single-attachment failure isolation, count/size/depth protection all verified by full-integration tests.
- performance: no blocking regression observed in the parser regression suite; the only deployment delta is adding the locked runtime dependency `olefile`, with no schema or storage migration required.

## Acceptance Conclusion
status: pass
notes: ACC-001 to ACC-005 all have full-integration pass records in testing.md. Runtime packaging has been corrected by explicitly locking `olefile` into the backend image. Residual risk remains low. Some WPS-like OLE containers still degrade to attachment_errors instead of recovered正文 text, but this does not block overall parsing and remains within the approved design boundary.
approved_by: codex
approved_at: 2026-04-21

## Rollback Plan
trigger_conditions:
  - parser smoke test fails in staging after deployment
  - attachment_errors spike materially beyond the current known degraded-only sample profile
  - merged requirement_content causes regression in existing no-attachment parsing scenarios
rollback_steps:
  1. Revert the parser-layer changes in backend/utils/embedded_attachment_extractor.py, backend/service/document_parser.py, and backend/utils/docx_parser.py.
  2. Redeploy the previous backend package to staging.
  3. Re-run the existing parser regression suite to confirm baseline behavior is restored.

## Monitoring
metrics:
  - parser success rate for documents with embedded attachments
  - count of attachment_errors per document and per embedded object type
  - parse latency for attachment-bearing requirement documents
alerts:
  - sustained increase in unsupported embedded payload errors
  - staging smoke parse failures for the verified attachment sample set
  - regression in no-attachment document parsing results

## Post-deployment Actions
- [x] update related docs
- [x] record lessons learned if needed
- [ ] archive change dossier to versions/
