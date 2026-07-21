from pydantic import BaseModel, Field


class CreateEvalDatasetRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class AddEvalQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)
    ground_truth_answer: str = Field(...)
    relevant_chunk_ids: list[str] = Field(default_factory=list)


class BulkImportQuestionsRequest(BaseModel):
    questions: list[AddEvalQuestionRequest]
