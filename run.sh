#!/usr/bin/env bash
# Repo entrypoint for local dev stacks and CI test runs.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="${ROOT_DIR}/server"
INTEGRATION_DIR="${ROOT_DIR}/integration_tests"

DEV_COMPOSE=(
  docker compose
  -f docker-compose.db.yml
  -f docker-compose.db.dev.yml
  -f docker-compose.yml
  -f docker-compose.dev.yml
)
PROD_COMPOSE=(
  docker compose
  -f docker-compose.db.yml
  -f docker-compose.yml
  -f docker-compose.prod.yml
)

usage() {
  cat <<'EOF'
Usage: ./run.sh <command> [options]

Commands:
  api-dev             Start dev stack (db + app on localhost:8090)
  api-prod            Start prod stack (db + app + caddy)
  unit-tests          Run Python unit tests (tests/)
  integration-tests   Run Bruno integration tests (integration_tests/)
  mypy                Run mypy static type checks
  autopep8-check      Fail if Python files need autopep8 formatting

Options:
  --clear-volumes, -V   Remove Docker volumes before starting api-dev/api-prod
  --tags <tags>         Bruno tags for integration-tests (default: smoke)
  -h, --help            Show this help

Examples:
  ./run.sh api-dev
  ./run.sh api-dev --clear-volumes
  ./run.sh api-prod -V
  ./run.sh unit-tests
  ./run.sh integration-tests --tags smoke
  ./run.sh mypy
  ./run.sh autopep8-check
EOF
}

require_env() {
  if [[ ! -f "${SERVER_DIR}/.env" ]]; then
    echo "Missing ${SERVER_DIR}/.env — copy .env.example to .env and fill in values." >&2
    exit 1
  fi
}

require_docker() {
  if ! command -v docker &>/dev/null; then
    echo "Docker is required but not installed." >&2
    exit 1
  fi
  if ! docker compose version &>/dev/null 2>&1; then
    echo "Docker Compose v2 is required (docker compose)." >&2
    exit 1
  fi
}

clear_volumes() {
  local -a compose=("$@")
  echo "Stopping stack and removing volumes..."
  (cd "${SERVER_DIR}" && "${compose[@]}" down -v --remove-orphans)
}

start_api_dev() {
  require_docker
  require_env
  if [[ "${CLEAR_VOLUMES}" == "true" ]]; then
    clear_volumes "${DEV_COMPOSE[@]}"
  fi
  echo "Starting dev stack..."
  (cd "${SERVER_DIR}" && "${DEV_COMPOSE[@]}" up -d --build --wait)
  echo "Dev API ready at http://127.0.0.1:8090"
}

start_api_prod() {
  require_docker
  require_env
  if [[ "${CLEAR_VOLUMES}" == "true" ]]; then
    clear_volumes "${PROD_COMPOSE[@]}"
  fi
  echo "Starting prod stack..."
  (cd "${SERVER_DIR}" && "${PROD_COMPOSE[@]}" up -d --build --wait)
  echo "Prod stack started (Caddy TLS on ports 80/443)."
}

ensure_venv() {
  local python="${PYTHON:-python3.11}"
  if ! command -v "${python}" &>/dev/null; then
    python=python3
  fi

  local venv_dir="${SERVER_DIR}/.venv"
  if [[ ! -d "${venv_dir}" ]]; then
    echo "Creating virtualenv with ${python}..."
    "${python}" -m venv "${venv_dir}"
  fi

  # shellcheck disable=SC1091
  source "${venv_dir}/bin/activate"
  echo "Installing dependencies..."
  pip install -q -e "${ROOT_DIR}[dev]"
}

run_unit_tests() {
  ensure_venv
  echo "Running unit tests..."
  (
    cd "${ROOT_DIR}"
    PYTHONPATH=. python -m unittest discover -s tests -p "test_*.py"
  )
}

run_mypy() {
  ensure_venv
  echo "Running mypy..."
  (
    cd "${ROOT_DIR}"
    PYTHONPATH=server mypy server/ tests/ --exclude 'server/migrations/'
  )
}

run_autopep8_check() {
  ensure_venv
  echo "Checking autopep8 formatting..."
  autopep8 \
    --recursive \
    --diff \
    --exit-code \
    --exclude=.venv \
    server/ tests/
}

wait_for_health() {
  local url="${1:-http://127.0.0.1:8090/health}"
  local max_attempts="${2:-60}"
  local attempt=0

  echo "Waiting for ${url}..."
  until curl -sf "${url}" >/dev/null; do
    attempt=$((attempt + 1))
    if [[ "${attempt}" -ge "${max_attempts}" ]]; then
      echo "API not healthy after ${max_attempts} attempts." >&2
      exit 1
    fi
    sleep 5
  done
  echo "API is healthy."
}

run_integration_tests() {
  local tags="${INTEGRATION_TAGS:-smoke}"
  local -a bru_cmd=()

  if command -v bru &>/dev/null; then
    bru_cmd=(bru)
  elif command -v npx &>/dev/null; then
    bru_cmd=(npx --yes @usebruno/cli)
  else
    echo "Bruno CLI not found — install @usebruno/cli or Node.js npx." >&2
    exit 1
  fi

  wait_for_health
  echo "Running Bruno integration tests (tags: ${tags})..."
  (cd "${INTEGRATION_DIR}" && "${bru_cmd[@]}" run --env local --tags "${tags}")
}

COMMAND=""
CLEAR_VOLUMES=false
INTEGRATION_TAGS="smoke"

if [[ $# -eq 0 ]]; then
  usage
  exit 1
fi

COMMAND="$1"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --clear-volumes|-V)
      CLEAR_VOLUMES=true
      shift
      ;;
    --tags)
      if [[ $# -lt 2 ]]; then
        echo "--tags requires a value." >&2
        exit 1
      fi
      INTEGRATION_TAGS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

case "${COMMAND}" in
  api-dev)
    start_api_dev
    ;;
  api-prod)
    start_api_prod
    ;;
  unit-tests)
    run_unit_tests
    ;;
  integration-tests)
    run_integration_tests
    ;;
  mypy)
    run_mypy
    ;;
  autopep8-check)
    run_autopep8_check
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown command: ${COMMAND}" >&2
    usage
    exit 1
    ;;
esac
