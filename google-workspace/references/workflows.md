# Google Workspace Workflows

Reusable helper patterns for common agent tasks.

## Session Receipt Upload

```bash
upload_session_receipt() {
  local file="$1"
  local folder_id="${2:-$RECEIPTS_FOLDER_ID}"
  local timestamp=$(date +%Y-%m-%d)
  
  gws drive files create \
    --json "{\"name\": \"receipt-${timestamp}.md\", \"parents\": [\"$folder_id\"]}" \
    --upload "$file"
}
```

## Metrics Logging to Sheets

```bash
log_metric() {
  local sheet_id="$1"
  local project="$2"
  local metric="$3"
  local value="$4"
  
  gws sheets spreadsheets values append \
    --params "{\"spreadsheetId\": \"$sheet_id\", \"range\": \"Metrics!A1\", \"valueInputOption\": \"USER_ENTERED\"}" \
    --json "{\"values\": [[\"$(date -Iseconds)'\", \"$project\", \"$metric\", $value]]}"
}

# Usage
log_metric "SHEET_ID" "meta" "tokens_used" 15420
```

## Pipeline Failure Notification

```bash
notify_failure() {
  local pipeline="$1"
  local error="$2"
  local encoded=$(echo -e "Subject: Pipeline Failed: $pipeline\n\nError: $error\nTime: $(date)" | base64 -w 0)
  
  gws gmail users messages send \
    --params '{"userId": "me"}' \
    --json "{\"raw\": \"$encoded\"}"
}
```

## Calendar Focus Block

```bash
block_focus_time() {
  local hours="${1:-2}"
  local start=$(date -d "+1 hour" -Iseconds)
  local end=$(date -d "+1 hour +${hours} hours" -Iseconds)
  
  gws calendar events insert \
    --params '{"calendarId": "primary"}' \
    --json "{\"summary\": \"🤖 Agent Session\", \"start\": {\"dateTime\": \"$start\"}, \"end\": {\"dateTime\": \"$end\"}, \"colorId\": \"9\"}"
}
```

## Drive Upload with Metadata

```bash
upload_artifact() {
  local file="$1"
  local project="$2"
  local folder_id="$3"
  
  gws drive files create \
    --json "{\"name\": \"$(basename "$file")\", \"description\": \"Project: $project\", \"parents\": [\"$folder_id\"]}" \
    --upload "$file"
}
```

## Paginated Search to JSON

```bash
# Stream all PDFs modified this month
gws drive files list \
  --params '{"pageSize": 100, "q": "mimeType = '\''application/pdf'\'' and modifiedTime > '\''2026-02-01T00:00:00'\''"}' \
  --page-all > pdfs.json

# Extract names with jq
jq -r '.files[].name' pdfs.json
```
