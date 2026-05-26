import os
import shutil
from pathlib import Path

from app.models.media import OperationType, RenamePlan


class FileOperationService:
    def execute(self, plan: RenamePlan) -> RenamePlan:
        for entry in plan.plan:
            source = Path(entry["source"])
            target = Path(entry["target"])
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                continue
            if plan.operation == OperationType.HARDLINK:
                os.link(source, target)
            elif plan.operation == OperationType.COPY:
                shutil.copy2(source, target)
            elif plan.operation == OperationType.MOVE:
                shutil.move(str(source), str(target))
        plan.status = "completed"
        return plan
