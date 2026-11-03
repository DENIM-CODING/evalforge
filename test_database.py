from uuid import uuid4

from app.database import get_engine
from app.evaluation_repository import (
    create_evaluation,
    update_evaluation_status,
    get_evaluation,
    get_evaluation_history,
)
from sqlalchemy.orm import Session


def main():

    evaluation_id = str(uuid4())

    with Session(get_engine()) as session:

        # 1. Create evaluation
        evaluation = create_evaluation(
            session,
            evaluation_id,
        )

        print("Created:", evaluation.id, evaluation.status)

        # 2. Update status
        update_evaluation_status(
            session,
            evaluation_id,
            status="running",
        )

        # 3. Retrieve evaluation
        evaluation = get_evaluation(
            session,
            evaluation_id,
        )

        print("Updated status:", evaluation.status)

        # 4. Retrieve history
        history = get_evaluation_history(
            session,
            limit=10,
        )

        print("Total history records:", len(history))

        assert evaluation.id == evaluation_id
        assert evaluation.status == "running"
        assert any(item.id == evaluation_id for item in history)

        # Clean up this temporary test record.
        session.delete(evaluation)
        session.commit()

        print("Repository test successful!")


if __name__ == "__main__":
    main()