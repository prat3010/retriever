"""Continuous DPO / ORPO Preference Fine-Tuning Domain Abstractions (Milestone 120).

Defines pure domain entities, preference pair data models, mathematical loss parameters,
and abstract port interfaces for autonomous continuous preference learning and LoRA adapter
swapping. Contains strictly zero framework or infrastructure imports.
"""

from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel, Field


class TuningObjective(StrEnum):
    """Supported preference alignment objective algorithms."""

    DPO = "dpo"    # Direct Preference Optimization (Rafailov et al.)
    ORPO = "orpo"  # Odds Ratio Preference Optimization (Hong et al.)
    KTO = "kto"    # Kahneman-Tversky Optimization (Ethayarajh et al.)


class TuningJobStatus(StrEnum):
    """Lifecycle states of an autonomous preference fine-tuning job."""

    COLLECTING = "collecting"
    QUEUED = "queued"
    TRAINING = "training"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class PreferencePair(BaseModel):
    """A harvested or curated preference sample with winning and losing completions."""

    pair_id: str = Field(..., description="Unique UUID identifier for the preference pair")
    tenant_id: str = Field(..., description="Tenant owning this preference datum")
    prompt: str = Field(..., description="The user query or prompt (x)")
    winning_response: str = Field(..., description="The chosen/upvoted completion (y_w)")
    losing_response: str = Field(..., description="The rejected/downvoted completion (y_l)")
    source_message_id: str | None = Field(default=None, description="Linked chat message UUID if harvested")
    feedback_rating: int = Field(default=1, description="Rating score (+1 upvote, -1 downvote/correction)")
    tags: list[str] = Field(default_factory=list, description="Categorical taxonomy tags (e.g. ['factual', 'concise'])")
    is_verified: bool = Field(default=True, description="Whether pair has passed automated quality filtering")
    created_at: str = Field(..., description="ISO 8601 timestamp of creation")


class TuningHyperparameters(BaseModel):
    """Hyperparameters configuring preference optimization runs."""

    learning_rate: float = Field(default=5e-6, description="Optimizer learning rate")
    beta: float = Field(default=0.1, description="DPO temperature scaling factor (beta)")
    lambda_orpo: float = Field(default=0.1, description="ORPO odds-ratio loss weight (lambda)")
    lora_r: int = Field(default=16, description="LoRA rank dimension")
    lora_alpha: float = Field(default=32.0, description="LoRA scaling multiplier")
    batch_size: int = Field(default=4, description="Training micro-batch size")
    epochs: int = Field(default=3, description="Training epochs over preference dataset")
    auto_trigger_threshold: int = Field(default=50, description="Number of harvested pairs needed to trigger auto-train")
    eval_split_ratio: float = Field(default=0.2, description="Held-out validation dataset fraction")


class TuningLossStep(BaseModel):
    """Convergence telemetry recorded per training step."""

    step: int = Field(..., description="Iteration step number")
    epoch: int = Field(..., description="Current epoch index")
    train_loss: float = Field(..., description="Calculated preference loss")
    reward_margin: float = Field(..., description="Implicit reward difference: r(x, y_w) - r(x, y_l)")
    accuracy: float = Field(..., description="Batch pairwise accuracy (fraction where r_w > r_l)")
    odds_ratio: float = Field(..., description="Odds ratio of chosen vs rejected probabilities")


class EvaluationGateResult(BaseModel):
    """Post-training validation gate outcome benchmarked against held-out validation split."""

    passed: bool = Field(..., description="Whether the trained model passed quality gates")
    validation_accuracy: float = Field(..., description="Preference accuracy on held-out validation split (min 0.75)")
    avg_reward_margin: float = Field(..., description="Mean implicit reward separation on validation split")
    validation_loss: float = Field(..., description="Validation loss")
    total_eval_pairs: int = Field(..., description="Number of validation samples evaluated")
    recommendation: str = Field(..., description="'promote_to_active' or 'reject_and_rollback'")


class ContinuousTuningConfig(BaseModel):
    """Tenant configuration governing automatic preference harvesting and tuning."""

    tenant_id: str = Field(..., description="Tenant identifier")
    objective: TuningObjective = Field(default=TuningObjective.DPO, description="Default alignment objective")
    base_model: str = Field(default="meta-llama/Meta-Llama-3.1-8B-Instruct", description="Base model identifier")
    active_adapter_id: str | None = Field(default=None, description="Currently active hot-swapped LoRA adapter ID")
    auto_train_enabled: bool = Field(default=True, description="Whether to automatically dispatch jobs at threshold")
    hyperparameters: TuningHyperparameters = Field(default_factory=TuningHyperparameters)
    total_pairs_harvested: int = Field(default=0, description="Total preference pairs collected to date")
    active_pairs_in_buffer: int = Field(default=0, description="Unprocessed pairs awaiting next training batch")


class TuningJob(BaseModel):
    """Autonomous preference fine-tuning job execution record."""

    job_id: str = Field(..., description="Unique UUID identifier for the tuning job")
    tenant_id: str = Field(..., description="Tenant owning this job")
    objective: TuningObjective = Field(..., description="Objective used (dpo, orpo, kto)")
    status: TuningJobStatus = Field(default=TuningJobStatus.QUEUED, description="Current execution state")
    base_model: str = Field(..., description="Foundational base model compiled against")
    output_adapter_id: str = Field(..., description="Identifier for the generated LoRA adapter")
    dataset_size: int = Field(..., description="Total preference pairs utilized for training and eval")
    hyperparameters: TuningHyperparameters = Field(..., description="Hyperparameters used for this execution")
    loss_history: list[TuningLossStep] = Field(default_factory=list, description="Step loss telemetry convergence curve")
    evaluation: EvaluationGateResult | None = Field(default=None, description="Evaluation gate metrics")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    completed_at: str | None = Field(default=None, description="ISO 8601 completion timestamp")
    error_message: str | None = Field(default=None, description="Error details if job failed")


class TuningMathSimulationResult(BaseModel):
    """Comparative mathematical simulation result evaluating DPO and ORPO loss behavior."""

    prompt: str = Field(..., description="Simulated prompt (x)")
    beta: float = Field(..., description="DPO temperature (beta)")
    lambda_orpo: float = Field(..., description="ORPO lambda parameter")
    pi_theta_win_prob: float = Field(..., description="P_theta(y_w | x)")
    pi_ref_win_prob: float = Field(..., description="P_ref(y_w | x)")
    pi_theta_lose_prob: float = Field(..., description="P_theta(y_l | x)")
    pi_ref_lose_prob: float = Field(..., description="P_ref(y_l | x)")
    dpo_reward_w: float = Field(..., description="Implicit reward r_hat(x, y_w)")
    dpo_reward_l: float = Field(..., description="Implicit reward r_hat(x, y_l)")
    dpo_reward_margin: float = Field(..., description="r_hat(x, y_w) - r_hat(x, y_l)")
    dpo_loss: float = Field(..., description="Calculated DPO loss")
    orpo_odds_w: float = Field(..., description="odds_theta(y_w | x)")
    orpo_odds_l: float = Field(..., description="odds_theta(y_l | x)")
    orpo_odds_ratio: float = Field(..., description="odds_w / odds_l")
    orpo_loss: float = Field(..., description="Calculated ORPO loss")


class ContinuousTuningPort(ABC):
    """Abstract port interface for continuous preference harvesting and fine-tuning."""

    @abstractmethod
    def harvest_preference_pair(self, tenant_id: str, pair: PreferencePair) -> PreferencePair:
        """Record or ingest a preference pair into the tenant's harvest buffer."""
        ...

    @abstractmethod
    def list_preference_pairs(
        self, tenant_id: str, limit: int = 50, offset: int = 0
    ) -> tuple[list[PreferencePair], int]:
        """List harvested preference pairs for a tenant with pagination."""
        ...

    @abstractmethod
    def delete_preference_pair(self, tenant_id: str, pair_id: str) -> bool:
        """Remove a preference pair from a tenant's dataset."""
        ...

    @abstractmethod
    def get_tuning_config(self, tenant_id: str) -> ContinuousTuningConfig:
        """Retrieve continuous tuning configuration for a tenant."""
        ...

    @abstractmethod
    def update_tuning_config(
        self, tenant_id: str, config: ContinuousTuningConfig
    ) -> ContinuousTuningConfig:
        """Update continuous tuning configuration for a tenant."""
        ...

    @abstractmethod
    def trigger_tuning_job(
        self,
        tenant_id: str,
        objective: TuningObjective = TuningObjective.DPO,
        hyperparams: TuningHyperparameters | None = None,
    ) -> TuningJob:
        """Trigger a preference fine-tuning job using buffered preference samples."""
        ...

    @abstractmethod
    def get_tuning_job(self, tenant_id: str, job_id: str) -> TuningJob | None:
        """Retrieve status and telemetry for a specific tuning job."""
        ...

    @abstractmethod
    def list_tuning_jobs(self, tenant_id: str, limit: int = 20) -> list[TuningJob]:
        """List history of tuning jobs executed for a tenant."""
        ...

    @abstractmethod
    def promote_adapter(self, tenant_id: str, job_id: str) -> ContinuousTuningConfig:
        """Promote a completed and evaluated LoRA adapter to active status."""
        ...

    @abstractmethod
    def rollback_adapter(self, tenant_id: str, target_adapter_id: str | None = None) -> ContinuousTuningConfig:
        """Roll back tenant serving to prior adapter version."""
        ...

    @abstractmethod
    def simulate_tuning_math(
        self,
        prompt: str,
        beta: float = 0.1,
        lambda_orpo: float = 0.1,
        pi_theta_w: float = 0.85,
        pi_ref_w: float = 0.50,
        pi_theta_l: float = 0.15,
        pi_ref_l: float = 0.50,
    ) -> TuningMathSimulationResult:
        """Simulate DPO and ORPO loss calculations given exact probability distributions."""
        ...
