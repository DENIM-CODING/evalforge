from pydantic import BaseModel, Field


class TestCaseBase(BaseModel):
    input: str = Field(min_length=1)
    actual_output: str = Field(min_length=1)
    expected_output: str = Field(min_length=1)
    context: list[str] = Field(min_length=1)


class CreateTestCaseRequest(TestCaseBase):
    pass


class UpdateTestCaseRequest(TestCaseBase):
    pass


class TestCaseResponse(TestCaseBase):
    id: str