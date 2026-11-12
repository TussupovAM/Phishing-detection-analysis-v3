# Phishing Detection Analysis

Small research-oriented Python module. It supports the dissertation *"Comparative Analysis of Traditional Machine Learning
and Deep Learning Approaches for Phishing Detection in Remote Work Environments"*.

The module extracts lexical features from URLs and trains a lightweight, interpretable Logistic
Regression classifier. It is an educational/research module, **not** a production security system.

## Features
- `extract_features(url)` - 14 lexical features (lengths, dots, hyphens, `@`, digits, subdomains,
  suspicious keywords, HTTPS, IP host incl. IPv6, port). Robust to empty/malformed input.
- `PhishingDetector` - pipeline `DictVectorizer -> StandardScaler -> LogisticRegression`
  (`class_weight="balanced"` for imbalanced data) with `fit`, `predict`, `predict_proba`,
  `evaluate`, `feature_weights` (simple explainability), `save` / `load`.
- `train_test_evaluate` (stratified hold-out) and `cross_validate` (stratified k-fold) - metrics on
  **unseen** data: accuracy, precision, recall, F1.
- `load_dataset(path)` - CSV loader that validates columns and labels.
- Command-line interface: `python -m src.cli evaluate | predict`.
- REST API (`src/api.py`, FastAPI): `GET /health`, `POST /predict`.
- DevOps: `Dockerfile`, `Jenkinsfile` (CI/CD), Jenkins-in-Docker setup (`jenkins/`), Kubernetes manifests (`k8s/`).

## Project structure
```
src/phishing_detector.py      # features, model, evaluation, data loading
src/cli.py                    # command-line interface
src/api.py                    # REST API (FastAPI)
Dockerfile  .dockerignore     # container image
Jenkinsfile                   # Jenkins CI/CD pipeline
jenkins/                      # Dockerfile + docker-compose for a local Jenkins
k8s/                          # Kubernetes manifests (Minikube)
tests/                        # 36 pytest tests (features, model, evaluation, loader, CLI, API)
data/sample_data.csv          # SYNTHETIC demo dataset: 200 URLs, 25% phishing
scripts/make_synthetic_data.py# reproducible generator of the dataset (fixed seed)
.github/workflows/tests.yml   # CI: lint -> tests (Python 3.10-3.12, coverage) -> CLI smoke test
.github/ISSUE_TEMPLATE/       # bug / feature templates;  pull_request_template.md
requirements.txt              # runtime dependencies
requirements-dev.txt          # + pytest, pytest-cov, ruff
pytest.ini  ruff.toml         # tool configuration
```

## Quick start
```bash
git clone https://github.com/YOUR_USERNAME/phishing-detection-analysis.git
cd phishing-detection-analysis
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q --cov=src      # run tests with coverage
ruff check .             # lint
```

## Usage
```bash
python -m src.cli evaluate
python -m src.cli predict "http://paypal-login-verify.test/confirm" "https://github.com"
```
```python
from src.phishing_detector import PhishingDetector, load_dataset, train_test_evaluate

data = load_dataset("data/sample_data.csv")
print(train_test_evaluate(data))                       # metrics on a held-out 30%
model = PhishingDetector().fit(data["url"], data["label"])
print(model.predict_proba(["http://192.168.1.10:8080/login"]))   # probability of phishing
print(list(model.feature_weights().items())[:3])       # most influential features
```


## Docker
```bash
docker build -t phishing-detector .
docker run --rm phishing-detector python -m src.cli evaluate      # CLI inside the container
docker run -d -p 8000:8000 --name phishing-api phishing-detector  # REST API
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" \
     -d '{"urls": ["http://paypal-login-verify.test/confirm", "https://github.com"]}'
```
Interactive API documentation: http://localhost:8000/docs

## Jenkins (CI/CD)
```bash
cd jenkins
docker compose up -d --build
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword   # unlock key
```
1. Open http://localhost:8080, unlock Jenkins, create an admin user (the plugins are pre-installed).
2. New Item -> **Pipeline** -> *Pipeline script from SCM* -> Git -> your repository URL, branch `main`, script path `Jenkinsfile`.
3. *Build Now* (the first run also registers the build parameters).

Pipeline stages: checkout, install dependencies (virtualenv), lint (ruff), unit tests (pytest, JUnit and coverage reports),
build Docker image, smoke-test the image, optional push to Docker Hub, deploy to a local test container with a post-deploy check.
It polls the repository every ~2 minutes, so every new commit triggers a build.

*Push to Docker Hub:* add a "Username with password" credential with ID `dockerhub-credentials` (use a Docker Hub access token),
then run *Build with Parameters* with `IMAGE_NAME=<your-user>/phishing-detector` and `PUSH_IMAGE` ticked.

> The Jenkins container runs as root and uses the host Docker socket - fine for a local lab, not for production.

## Kubernetes (Minikube, optional CD)
```bash
minikube start
docker build -t phishing-detector:latest .
minikube image load phishing-detector:latest
kubectl apply -f k8s/
kubectl rollout status deployment/phishing-detector
minikube service phishing-detector --url     # open the printed URL + /health
```

## CI/CD (GitHub Actions)
GitHub Actions (`.github/workflows/tests.yml`) runs on every push and pull request:
1. **lint** - `ruff check .`
2. **test** - matrix Python 3.10 / 3.11 / 3.12, `pytest` with coverage (fails below 85 %),
   coverage report uploaded as an artifact, pip dependency cache
3. **smoke-cli** - runs `python -m src.cli evaluate` on the bundled dataset
4. **docker** - builds the image, runs the CLI in it, starts the API container and calls `/health` and `/predict`

## Workflow
Work is tracked in GitHub Issues (templates provided). Changes are made in feature branches and merged
into `main` through pull requests once CI is green.

## Limitations
- The bundled dataset is **synthetic** and easy: high scores on it (F1 about 0.97-0.99) do **not**
  predict real-world performance. Use a validated real dataset (e.g. PhishTank + a benign URL list)
  for real experiments.
- Only lexical URL features are used; no page content, WHOIS, or e-mail text.
- Not a security product; do not rely on it to protect real users.

## License
MIT - see [LICENSE](LICENSE).
