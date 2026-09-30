#!/usr/bin/env bash
# Test e2e: wysyła wiadomości do API i sprawdza w MailHogu adresata (To) oraz Reply-To.
# Wymaga uruchomionego środowiska (docker compose up -d) oraz curl i python3.
set -u

API_URL="${API_URL:-http://localhost:8000}"
MAILHOG_URL="${MAILHOG_URL:-http://localhost:8025}"
API_PREFIX="${API_PREFIX:-/api/v1}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-300}"

# nadawca|oczekiwany adresat|wiadomość
CASES=(
  "anna.it@example.com|it@example.com|Laptop nie łączy się z VPN i nie mogę się zalogować do systemów firmowych."
  "jan.kadry@example.com|kadry@example.com|Chciałbym złożyć wniosek o urlop wypoczynkowy w dniach 5-16 sierpnia."
  "ewa.hr@example.com|human-resources@example.com|Jakie szkolenia i ścieżki awansu są dostępne dla programistów w naszej firmie?"
  "piotr.biuro@example.com|help-desk@example.com|Jak mogę zarezerwować salę konferencyjną na piątkowe spotkanie zespołu?"
  "ola.nonsens@example.com|other@example.com|asdf qwerty zxcv 12345 !!!"
)

failures=0

fail() {
  echo "  FAIL: $*"
  failures=$((failures + 1))
}

json_field() {
  python3 -c 'import json,sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$1"
}

# Wypisuje "<To>|<Reply-To>" maila z danym Reply-To (pusty wynik, gdy nie znaleziono).
find_mail() {
  python3 -c '
import json, sys
for m in json.load(sys.stdin)["items"]:
    h = m["Content"]["Headers"]
    if h.get("Reply-To", [""])[0] == sys.argv[1]:
        print(h["To"][0] + "|" + h["Reply-To"][0])
        break
' "$1"
}

echo "Czekam na API (${API_URL})..."
for _ in $(seq 1 30); do
  curl -sf "${API_URL}${API_PREFIX}/health" >/dev/null && break
  sleep 2
done
curl -sf "${API_URL}${API_PREFIX}/health" >/dev/null || { echo "API niedostępne"; exit 1; }
curl -sf "${MAILHOG_URL}/api/v2/messages" >/dev/null || { echo "MailHog niedostępny (${MAILHOG_URL})"; exit 1; }

curl -sf -X DELETE "${MAILHOG_URL}/api/v1/messages" >/dev/null

for entry in "${CASES[@]}"; do
  IFS='|' read -r sender expected message <<<"${entry}"
  echo "-> ${sender}: ${message}"
  failures_before=${failures}

  payload=$(python3 -c 'import json,sys; print(json.dumps({"email": sys.argv[1], "message": sys.argv[2]}))' "${sender}" "${message}")
  response=$(curl -s -m "${REQUEST_TIMEOUT}" -w '\n%{http_code}' -X POST "${API_URL}${API_PREFIX}/messages" \
    -H 'Content-Type: application/json' -d "${payload}")
  status="${response##*$'\n'}"
  body="${response%$'\n'*}"

  if [[ "${status}" != "200" ]]; then
    fail "HTTP ${status}: ${body}"
    continue
  fi

  routed_to=$(json_field routed_to <<<"${body}")
  [[ "${routed_to}" == "${expected}" ]] || fail "API routed_to=${routed_to}, oczekiwano ${expected}"

  mail=$(curl -s "${MAILHOG_URL}/api/v2/messages" | find_mail "${sender}")
  if [[ -z "${mail}" ]]; then
    fail "w MailHogu brak maila z Reply-To=${sender}"
    continue
  fi
  mail_to="${mail%%|*}"
  [[ "${mail_to}" == "${expected}" ]] || fail "MailHog To=${mail_to}, oczekiwano ${expected}"

  [[ ${failures} -eq ${failures_before} ]] && echo "  OK: To=${mail_to}, Reply-To=${sender}"
done

echo
if [[ ${failures} -eq 0 ]]; then
  echo "Smoke test: wszystko OK (${#CASES[@]} wiadomości)"
else
  echo "Smoke test: ${failures} błędów"
  exit 1
fi
