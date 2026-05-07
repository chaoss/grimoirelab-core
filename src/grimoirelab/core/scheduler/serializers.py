# -*- coding: utf-8 -*-
#
# Copyright (C) GrimoireLab Contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import django_rq

from rest_framework import (
    pagination,
    response,
    serializers,
)

from .models import SchedulerStatus
from .tasks.models import (
    EventizerTask,
    AffiliateTask,
    UnifyTask,
    GenderizeTask,
    ImportIdentitiesTask,
    RecommendAffiliationsTask,
    RecommendGenderTask,
    RecommendMatchesTask,
)


class SchedulerPaginator(pagination.PageNumberPagination):
    """Paginator for scheduler serializers.

    It extends the default PageNumberPagination to set a default
    page size and a maximum page size.
    """

    page_size = 25
    page_size_query_param = "size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return response.Response(
            {
                "links": {"next": self.get_next_link(), "previous": self.get_previous_link()},
                "count": self.page.paginator.count,
                "page": self.page.number,
                "total_pages": self.page.paginator.num_pages,
                "results": data,
            }
        )


class TaskSerializerMixin(serializers.ModelSerializer):
    """Mixin to serialize common fields of all Task models.

    This class defines the common fields and methods to be used by
    the task serializers.
    Subclasses must define the Meta class with the 'model'
    to be serialized, the 'fields' that will be included in the
    Response serialization, and the 'task_args' that will be
    validated to create a new task.
    """

    uuid = serializers.CharField(read_only=True)
    status = serializers.CharField(source="get_status_display", read_only=True)
    runs = serializers.IntegerField(read_only=True)
    failures = serializers.IntegerField(read_only=True)
    last_run = serializers.DateTimeField(read_only=True)
    scheduled_at = serializers.DateTimeField(read_only=True)
    last_jobs = serializers.SerializerMethodField(read_only=True)
    task_args = serializers.JSONField(required=True)
    job_max_retries = serializers.IntegerField(required=False)
    job_interval = serializers.IntegerField(required=False)
    burst = serializers.BooleanField(required=False)

    class Meta:
        model = None
        fields = [
            "uuid",
            "status",
            "runs",
            "failures",
            "last_run",
            "job_interval",
            "scheduled_at",
            "job_max_retries",
            "task_args",
            "burst",
            "last_jobs",
        ]
        task_args = ["task_args", "job_interval", "job_max_retries", "burst"]

    def get_last_jobs(self, obj):
        """Get the last jobs associated with the task."""

        jobs = obj.jobs.order_by("-job_num")[:10]
        return JobSummarySerializer(jobs, many=True).data

    def create_scheduler_task_args(self) -> dict:
        """Extract the arguments to schedule the task from the validated data.

        This method simplifies the creation of new tasks by extracting
        the relevant arguments from the validated data using the
        'task_args' defined in the Meta class.
        """
        task_args = {}
        for key in self.Meta.task_args:
            if key in self.validated_data:
                task_args[key] = self.validated_data[key]
        return task_args


class JobSummarySerializer(serializers.Serializer):
    """Serializer for job summary information.

    This serializer is used to provide a short summary of jobs
    associated with a task.
    """

    uuid = serializers.CharField()
    job_num = serializers.IntegerField()
    status = serializers.CharField(source="get_status_display")
    scheduled_at = serializers.DateTimeField(allow_null=True)
    started_at = serializers.DateTimeField(allow_null=True)
    finished_at = serializers.DateTimeField(allow_null=True)

    class Meta:
        fields = [
            "uuid",
            "job_num",
            "status",
            "scheduled_at",
            "started_at",
            "finished_at",
            "queue",
        ]


class JobSerializer(JobSummarySerializer):
    """Serializer for job details.

    This serializer extends the JobSummarySerializer to include
    the progress information.
    """

    progress = serializers.SerializerMethodField()

    class Meta:
        fields = JobSummarySerializer.Meta.fields + [
            "progress",
        ]

    def get_progress(self, obj):
        if obj.status == SchedulerStatus.RUNNING:
            rq_job = django_rq.get_queue(obj.queue).fetch_job(obj.uuid)
            if rq_job:
                return rq_job.progress.to_dict()
        return obj.progress


class JobLogsSerializer(JobSummarySerializer):
    """Serializer for Job logs.

    This serializer provides a summary of the job along with its logs.
    """

    uuid = serializers.CharField()
    status = serializers.CharField(source="get_status_display")
    logs = serializers.SerializerMethodField()

    class Meta:
        fields = [
            "uuid",
            "status",
            "logs",
        ]

    def get_logs(self, obj):
        if obj.status == SchedulerStatus.RUNNING:
            rq_job = django_rq.get_queue(obj.queue).fetch_job(obj.uuid)
            if rq_job:
                return rq_job.job_log
        return obj.logs


class EventizerTaskSerializer(TaskSerializerMixin):
    """Serializer for EventizerTask model."""

    class Meta:
        model = EventizerTask
        fields = TaskSerializerMixin.Meta.fields + ["datasource_type", "datasource_category"]
        task_args = TaskSerializerMixin.Meta.task_args + ["datasource_type", "datasource_category"]


class RecommendAffiliationsTaskSerializer(TaskSerializerMixin):
    """Serializer for RecommendAffiliationsTask model."""

    class Meta:
        model = RecommendAffiliationsTask
        fields = TaskSerializerMixin.Meta.fields + RecommendAffiliationsTask.EXTRA_TASK_FIELDS
        task_args = TaskSerializerMixin.Meta.task_args + RecommendAffiliationsTask.EXTRA_TASK_FIELDS


class RecommendMatchesTaskSerializer(TaskSerializerMixin):
    """Serializer for RecommendMatchesTask model."""

    class Meta:
        model = RecommendMatchesTask
        fields = TaskSerializerMixin.Meta.fields + RecommendMatchesTask.EXTRA_TASK_FIELDS
        task_args = TaskSerializerMixin.Meta.task_args + RecommendMatchesTask.EXTRA_TASK_FIELDS


class RecommendGenderTaskSerializer(TaskSerializerMixin):
    """Serializer for RecommendGenderTask model."""

    class Meta:
        model = RecommendGenderTask
        fields = TaskSerializerMixin.Meta.fields + RecommendGenderTask.EXTRA_TASK_FIELDS
        task_args = TaskSerializerMixin.Meta.task_args + RecommendGenderTask.EXTRA_TASK_FIELDS


class AffiliateTaskSerializer(TaskSerializerMixin):
    """Serializer for AffiliateTask model."""

    class Meta:
        model = AffiliateTask
        fields = TaskSerializerMixin.Meta.fields + AffiliateTask.EXTRA_TASK_FIELDS
        task_args = TaskSerializerMixin.Meta.task_args + AffiliateTask.EXTRA_TASK_FIELDS


class UnifyTaskSerializer(TaskSerializerMixin):
    """Serializer for UnifyTask model."""

    class Meta:
        model = UnifyTask
        fields = TaskSerializerMixin.Meta.fields + UnifyTask.EXTRA_TASK_FIELDS
        task_args = TaskSerializerMixin.Meta.task_args + UnifyTask.EXTRA_TASK_FIELDS


class GenderizeTaskSerializer(TaskSerializerMixin):
    """Serializer for GenderizeTask model."""

    class Meta:
        model = GenderizeTask
        fields = TaskSerializerMixin.Meta.fields + GenderizeTask.EXTRA_TASK_FIELDS
        task_args = TaskSerializerMixin.Meta.task_args + GenderizeTask.EXTRA_TASK_FIELDS


class ImportIdentitiesTaskSerializer(TaskSerializerMixin):
    """Serializer for ImportIdentitiesTask model."""

    class Meta:
        model = ImportIdentitiesTask
        fields = TaskSerializerMixin.Meta.fields + ImportIdentitiesTask.EXTRA_TASK_FIELDS
        task_args = TaskSerializerMixin.Meta.task_args + ImportIdentitiesTask.EXTRA_TASK_FIELDS
