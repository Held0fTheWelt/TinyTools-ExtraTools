"""Lane runtime for fy_platform.runtime.

"""
from __future__ import annotations

from fy_platform.ir.catalog import IRCatalog
from fy_platform.ir.models import LaneExecutionRecord
from fy_platform.runtime.execution_plan import ExecutionPlan
from fy_platform.ai.workspace import utc_now


class LaneRuntime:
    """Coordinate lane runtime behavior.
    """
    def __init__(self, ir_catalog: IRCatalog) -> None:
        """Initialize LaneRuntime.

        Args:
            ir_catalog: Primary ir catalog used by this step.
        """
        self.ir_catalog = ir_catalog

    def begin(self, *, run_id: str, public_command: str, mode_name: str, plan: ExecutionPlan) -> list[LaneExecutionRecord]:
        """Begin the requested operation.

        The implementation iterates over intermediate items before it
        returns.

        Args:
            run_id: Identifier used to select an existing run or record.
            public_command: Primary public command used by this step.
            mode_name: Primary mode name used by this step.
            plan: Primary plan used by this step.

        Returns:
            list[LaneExecutionRecord]:
                Collection produced from the parsed or
                accumulated input data.
        """
        out: list[LaneExecutionRecord] = []
        # Process step one item at a time so begin applies the same rule across the full
        # collection.
        for step in plan.steps:
            record = LaneExecutionRecord(
                lane_execution_id=self.ir_catalog.new_id('lane'),
                run_id=run_id,
                public_command=public_command,
                mode_name=mode_name,
                lane_name=step.lane_name,
                status='planned',
                detail=step.detail,
                output_refs=[],
                started_at=utc_now(),
                ended_at=None,
            )
            self.ir_catalog.write_lane_execution(record)
            out.append(record)
        return out

    def mark_completed(self, lane_execution_id: str, output_refs: list[str] | None = None) -> None:
        """Mark completed.

        Args:
            lane_execution_id: Identifier used to select an existing run
                or record.
            output_refs: Primary output refs used by this step.
        """
        self.ir_catalog.update_lane_execution(lane_execution_id, status='completed', ended_at=utc_now(), output_refs=output_refs or [])

    def mark_failed(self, lane_execution_id: str, reason: str) -> None:
        """Mark failed.

        Args:
            lane_execution_id: Identifier used to select an existing run
                or record.
            reason: Primary reason used by this step.
        """
        self.ir_catalog.update_lane_execution(lane_execution_id, status='failed', ended_at=utc_now(), detail_append={'failure_reason': reason})
