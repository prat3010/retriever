"""Comprehensive test suite for Kubernetes Native Operator and Helm Charts (Milestone 112)."""

import ast
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from apps.api.src.adapters.operator.cluster_reconciler import (
    ClusterReconciler,
    InMemoryKubernetesClient,
)
from apps.api.src.domain.abstractions.operator import (
    ClusterBackupPolicy,
    ClusterGpuConfig,
    RetrieverClusterSpec,
)
from apps.api.src.main import app
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_hexagonal_architecture_operator() -> None:
    """Verify domain/abstractions/operator.py has zero forbidden framework/adapter imports."""
    target = REPO_ROOT / "apps" / "api" / "src" / "domain" / "abstractions" / "operator.py"
    with open(target) as f:
        tree = ast.parse(f.read(), filename=str(target))

    forbidden_prefixes = ("src.adapters", "apps.api.src.adapters", "src.routers", "sqlalchemy", "fastapi")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in forbidden_prefixes:
                    assert not alias.name.startswith(forbidden), f"Forbidden import '{alias.name}' in {target}"
        elif isinstance(node, ast.ImportFrom) and node.module:
            for forbidden in forbidden_prefixes:
                assert not node.module.startswith(forbidden), f"Forbidden import '{node.module}' in {target}"


def test_retriever_cluster_spec_validation() -> None:
    """Validate specification defaults and boundary conditions."""
    spec = RetrieverClusterSpec(
        name="test-cluster",
        namespace="retriever-test",
        replicas=3,
        web_replicas=2,
        image_tag="v1.2.0-alpha1",
        postgres_pvc_size="30Gi",
    )
    assert spec.name == "test-cluster"
    assert spec.namespace == "retriever-test"
    assert spec.replicas == 3
    assert spec.web_replicas == 2
    assert spec.image_tag == "v1.2.0-alpha1"
    assert spec.gpu.enabled is False
    assert spec.backup_policy.enabled is True

    # Pydantic validation constraints
    with pytest.raises(Exception):
        RetrieverClusterSpec(name="", replicas=0)  # min_length 1, replicas ge 1


@pytest.mark.asyncio
async def test_reconciliation_pending_to_running() -> None:
    """Test full initial reconciliation lifecycle: Pending -> Provisioning -> Running."""
    k8s = InMemoryKubernetesClient()
    reconciler = ClusterReconciler(client=k8s)

    spec = RetrieverClusterSpec(
        name="alpha-cluster",
        namespace="default",
        replicas=2,
        web_replicas=1,
        image_tag="v1.2.0-alpha1",
    )

    # Initial reconciliation
    status = await reconciler.reconcile(spec)
    assert status.phase == "Running"
    assert status.ready_replicas == 2
    assert status.desired_replicas == 2
    assert status.web_ready_replicas == 1
    assert status.database_healthy is True
    assert status.active_image_tag == "v1.2.0-alpha1"

    # Verify conditions
    cond_map = {c.type: c for c in status.conditions}
    assert "Available" in cond_map
    assert cond_map["Available"].status == "True"
    assert "DatabaseReady" in cond_map
    assert cond_map["DatabaseReady"].status == "True"
    assert cond_map["Progressing"].status == "False"


@pytest.mark.asyncio
async def test_rolling_upgrade_on_image_tag_change() -> None:
    """Test that altering image_tag triggers rolling upgrade reconciliation."""
    k8s = InMemoryKubernetesClient()
    reconciler = ClusterReconciler(client=k8s)

    spec = RetrieverClusterSpec(
        name="upgrade-cluster",
        namespace="default",
        replicas=2,
        image_tag="v1.2.0-alpha1",
    )
    status_v1 = await reconciler.reconcile(spec)
    assert status_v1.phase == "Running"
    assert status_v1.active_image_tag == "v1.2.0-alpha1"

    # Bump image tag to v1.2.0-beta1
    upgraded_spec = spec.model_copy(update={"image_tag": "v1.2.0-beta1"})
    status_v2 = await reconciler.reconcile(upgraded_spec, current_status=status_v1)

    assert status_v2.phase == "Running"
    assert status_v2.active_image_tag == "v1.2.0-beta1"
    assert "v1.2.0-beta1" in status_v2.message


@pytest.mark.asyncio
async def test_replica_scaling() -> None:
    """Test scaling replicas from 2 to 6."""
    k8s = InMemoryKubernetesClient()
    reconciler = ClusterReconciler(client=k8s)

    spec = RetrieverClusterSpec(name="scale-cluster", replicas=2)
    status = await reconciler.reconcile(spec)
    assert status.ready_replicas == 2

    # Scale replicas up
    scaled_spec = spec.model_copy(update={"replicas": 6})
    status_scaled = await reconciler.reconcile(scaled_spec, current_status=status)
    assert status_scaled.ready_replicas == 6
    assert status_scaled.desired_replicas == 6


@pytest.mark.asyncio
async def test_gpu_allocation_conditions() -> None:
    """Test condition changes when GPU configuration is toggled."""
    k8s = InMemoryKubernetesClient()
    reconciler = ClusterReconciler(client=k8s)

    spec_gpu = RetrieverClusterSpec(
        name="gpu-cluster",
        gpu=ClusterGpuConfig(enabled=True, gpu_type="nvidia.com/gpu", gpu_count=2),
    )
    status = await reconciler.reconcile(spec_gpu)
    cond_map = {c.type: c for c in status.conditions}
    assert cond_map["GpuAllocated"].status == "True"
    assert "2x nvidia.com/gpu" in cond_map["GpuAllocated"].message


@pytest.mark.asyncio
async def test_automated_and_manual_backup_jobs() -> None:
    """Test manual and automated backup dispatching."""
    k8s = InMemoryKubernetesClient()
    reconciler = ClusterReconciler(client=k8s)

    spec = RetrieverClusterSpec(
        name="backup-cluster",
        backup_policy=ClusterBackupPolicy(enabled=True, schedule="0 3 * * *", s3_bucket="my-backups"),
    )
    # Register cluster in in-memory client
    k8s.register_cluster({"metadata": {"name": spec.name, "namespace": spec.namespace}, "spec": spec.model_dump()})

    status = await reconciler.reconcile(spec)
    assert any(c.type == "BackupConfigured" and c.status == "True" for c in status.conditions)

    # Trigger manual backup
    job_id = await reconciler.trigger_manual_backup(spec)
    assert job_id.startswith("job-backup-backup-cluster-")
    assert len(k8s.backup_jobs) == 1
    assert k8s.backup_jobs[0]["s3_bucket"] == "my-backups"


def test_admin_api_operator_endpoints() -> None:
    """Verify /v1/admin/operator/* REST endpoints."""
    client = TestClient(app)
    headers = {"X-Admin-Master-Key": "test_admin_key"}

    with patch("src.config.settings.ADMIN_MASTER_KEY", "test_admin_key"):
        # 1. Status endpoint
        resp = client.get("/v1/admin/operator/status", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["crd_group"] == "retriever.run"
        assert data["crd_version"] == "v1alpha1"
        assert data["helm_chart_version"] == "1.2.0-alpha1"

        # 2. Reconcile endpoint
        spec_payload = {
            "name": "rest-cluster",
            "namespace": "default",
            "replicas": 3,
            "web_replicas": 1,
            "image_tag": "v1.2.0-alpha1",
            "postgres_pvc_size": "20Gi",
        }
        reconcile_resp = client.post("/v1/admin/operator/reconcile", json=spec_payload, headers=headers)
        assert reconcile_resp.status_code == 200
        rec_data = reconcile_resp.json()
        assert rec_data["phase"] == "Running"
        assert rec_data["ready_replicas"] == 3

        # 3. List clusters
        list_resp = client.get("/v1/admin/operator/clusters", headers=headers)
        assert list_resp.status_code == 200

        # 4. Backup 404 test on non-existent cluster
        backup_resp = client.post("/v1/admin/operator/clusters/non-existent/backup", headers=headers)
        assert backup_resp.status_code == 404


def test_helm_chart_structure_and_syntax() -> None:
    """Verify that all Helm 3 chart files exist, have valid structure, and YAML syntax."""
    helm_dir = REPO_ROOT / "deploy" / "helm" / "retriever"
    assert (helm_dir / "Chart.yaml").is_file()
    assert (helm_dir / "values.yaml").is_file()
    assert (helm_dir / "templates" / "_helpers.tpl").is_file()

    # Verify Chart.yaml parses
    with open(helm_dir / "Chart.yaml") as f:
        chart_data = yaml.safe_load(f)
        assert chart_data["name"] == "retriever"
        assert chart_data["version"] == "1.2.0-alpha1"
        assert chart_data["appVersion"] == "1.2.0-alpha1"

    # Verify values.yaml parses
    with open(helm_dir / "values.yaml") as f:
        values_data = yaml.safe_load(f)
        assert values_data["api"]["replicaCount"] == 2
        assert values_data["postgresql"]["enabled"] is True
        assert values_data["redis"]["enabled"] is True

    # Verify required template files exist
    expected_templates = [
        "api-deployment.yaml",
        "api-service.yaml",
        "web-deployment.yaml",
        "web-service.yaml",
        "ingress.yaml",
        "hpa.yaml",
        "configmap.yaml",
        "secret.yaml",
        "pgvector-statefulset.yaml",
        "pgvector-service.yaml",
        "redis-statefulset.yaml",
        "redis-service.yaml",
        "migration-job.yaml",
        "NOTES.txt",
    ]
    for tmpl in expected_templates:
        assert (helm_dir / "templates" / tmpl).is_file(), f"Missing template {tmpl}"


def test_crd_manifest_schema_validation() -> None:
    """Validate CRD manifest OpenAPI v3 schema, group, version, and printer columns."""
    crd_path = REPO_ROOT / "deploy" / "operator" / "crds" / "retrieverclusters.retriever.run.crd.yaml"
    assert crd_path.is_file()

    with open(crd_path) as f:
        crd_yaml = yaml.safe_load(f)

    assert crd_yaml["apiVersion"] == "apiextensions.k8s.io/v1"
    assert crd_yaml["kind"] == "CustomResourceDefinition"
    assert crd_yaml["metadata"]["name"] == "retrieverclusters.retriever.run"
    assert crd_yaml["spec"]["group"] == "retriever.run"
    assert crd_yaml["spec"]["names"]["kind"] == "RetrieverCluster"
    assert crd_yaml["spec"]["names"]["shortNames"] == ["rc", "rcluster"]

    version = crd_yaml["spec"]["versions"][0]
    assert version["name"] == "v1alpha1"
    assert version["served"] is True
    assert version["storage"] is True

    # Printer columns check
    col_names = [col["name"] for col in version["additionalPrinterColumns"]]
    assert "Phase" in col_names
    assert "Desired" in col_names
    assert "Ready" in col_names
    assert "Version" in col_names


def test_sample_manifests() -> None:
    """Validate sample production and minimal manifests."""
    samples_dir = REPO_ROOT / "deploy" / "operator" / "samples"

    prod_file = samples_dir / "retriever_cluster_production.yaml"
    min_file = samples_dir / "retriever_cluster_minimal.yaml"

    assert prod_file.is_file()
    assert min_file.is_file()

    with open(prod_file) as f:
        prod_data = yaml.safe_load(f)
    assert prod_data["kind"] == "RetrieverCluster"
    assert prod_data["spec"]["replicas"] == 3
    assert prod_data["spec"]["gpu"]["enabled"] is True

    with open(min_file) as f:
        min_data = yaml.safe_load(f)
    assert min_data["kind"] == "RetrieverCluster"
    assert min_data["spec"]["replicas"] == 1
    assert min_data["spec"]["gpu"]["enabled"] is False
