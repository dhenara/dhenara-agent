# Copyright 2024-2025 Dhenara Inc. All rights reserved.

import logging

from dhenara.agent.types import FlowContext
from django.core.exceptions import ValidationError

# from django.db import transaction
from apps.model_apps.app_dhenrun_models.models import TsgDhenRunEndPoint, TsgDhenRunEndPointExecutionRecord
from apps.model_apps.app_dhenrun_models.services.endpoint import DhenRunEndPointModelService

logger = logging.getLogger(__name__)


class ExecutionRecorder:
    def __init__(self):
        pass
        self.execution_record: TsgDhenRunEndPointExecutionRecord | None = None

    async def get_obj(
        self,
        obj_id: str | None,
        obj_ref_num: str | None = None,
    ) -> TsgDhenRunEndPoint:
        try:
            # Use select_related to fetch flow data in the same query
            qs = TsgDhenRunEndPointExecutionRecord.objects.select_related("endpoint")

            if obj_id:
                return await qs.aget(id=obj_id)
            if obj_ref_num:
                return await qs.aget(reference_number=obj_ref_num)
            return None
        except TsgDhenRunEndPoint.DoesNotExist:
            raise ValidationError(
                f"Endpoint not found for id {obj_id}/ reference_number {obj_ref_num}",
            )

    async def update_execution_in_db(self, context: FlowContext, create: bool = False):
        return  # TODO
        # TODO: Run in backround as non blocking
        try:
            if create:
                endpoint = await DhenRunEndPointModelService.get_obj(obj_id=context.endpoint_id)
                data = {
                    "endpoint": endpoint,
                    "execution_status": context.execution_status,
                    "flow_context": context.model_dump_json(),
                }
                self.execution_record = await TsgDhenRunEndPointExecutionRecord.objects.acreate(**data)
            else:
                if not self.execution_record:
                    raise ValidationError("execution_record is None")

                self.execution_record.flow_context = context
                self.execution_record.execution_status = context.execution_status
                await self.execution_record.asave()

        except Exception as e:
            logger.exception(f"update_execution_in_db : Error: {e}")
