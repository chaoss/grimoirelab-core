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

from __future__ import annotations

import typing

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import CharField, JSONField, BooleanField, DateTimeField

from sortinghat.core.context import SortingHatContext
from sortinghat.core.importer.backend import find_import_identities_backends
from sortinghat.core.jobs import (
    recommend_affiliations,
    recommend_matches,
    recommend_gender,
    affiliate,
    unify,
    genderize,
    import_identities,
)
from sortinghat.core.models import MIN_PERIOD_DATE

from ...scheduler.models import (
    SchedulerStatus,
    Task,
    register_task_model,
)
from ...scheduler.scheduler import (
    _on_success_callback,
    _on_failure_callback,
)
from ...models import MAX_SIZE_CHAR_FIELD
from .chronicler import (
    chronicler_job,
    ChroniclerProgress,
    get_chronicler_argument_generator,
)

if typing.TYPE_CHECKING:
    from typing import Any, Self


class EventizerTask(Task):
    """Task to fetch and eventize data.

    This task will fetch data from a software development repository
    and convert it into events. Fetched data and events will be
    published to a Redis queue. The progress of the task can be accessed
    through the property `progress`. The result of the task can be obtained
    accessing to the property `result` of the object.

    Data will be fetched using `perceval` and eventized using
    `chronicler`.

    :param datasource_type: type of the datasource
        (e.g., 'git', 'github')
    :param datasource_category: category of the datasource
        (e.g., 'pull_request', 'issue')
    :param job_args: extra arguments to pass to the job
        (e.g., 'url', 'owner', 'repository')
    """

    datasource_type = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    datasource_category = CharField(max_length=MAX_SIZE_CHAR_FIELD)

    TASK_TYPE = "eventizer"

    @classmethod
    def create_task(
        cls,
        task_args: dict[str, Any],
        job_interval: int,
        job_max_retries: int,
        datasource_type: str,
        datasource_category: str,
        burst: bool = False,
        *args,
        **kwargs,
    ) -> Self:
        """Create a new task to eventize data.

        This method will create a new task to eventize data from a
        a repository. Besides the common arguments to create a task,
        this method requires the type of the datasource and the category
        of items to eventize.

        :param task_args: arguments to pass to the task.
        :param job_interval: interval in seconds between each task execution.
        :param job_max_retries: maximum number of retries before the task is
            considered failed.
        :param datasource_type: type of the datasource.
        :param datasource_category: category of the item to eventize.
        :param burst: flag to indicate if the task will only run once.
        :param args: additional arguments.
        :param kwargs: additional keyword arguments.

        :return: the new task created.
        """
        task = super().create_task(
            task_args, job_interval, job_max_retries, burst=burst, *args, **kwargs
        )
        task.datasource_type = datasource_type
        task.datasource_category = datasource_category
        task.save()

        return task

    def prepare_job_parameters(self):
        """Generate the parameters for a new job.

        This method will generate the parameters for a new job
        based on the original parameters set for the task plus
        the latest job parameters used. Depending on the status
        of the task, new parameters will be generated.
        """
        task_args = {
            "datasource_type": self.datasource_type,
            "datasource_category": self.datasource_category,
            "events_stream": settings.GRIMOIRELAB_EVENTS_STREAM_NAME,
            "stream_max_length": settings.GRIMOIRELAB_EVENTS_STREAM_MAX_LENGTH,
        }

        args_gen = get_chronicler_argument_generator(self.datasource_type)

        # Get the latest job arguments used and use them
        # to prepare the new job arguments.
        if self.status == SchedulerStatus.NEW:
            job_args = args_gen.initial_args(self.task_args)
        elif self.status == SchedulerStatus.COMPLETED:
            job = self.jobs.all().order_by("-job_num").first()
            if job and job.progress:
                progress = ChroniclerProgress.from_dict(job.progress)
                job_args = args_gen.resuming_args(job.job_args["job_args"], progress)
            else:
                job_args = args_gen.initial_args(self.task_args)
        elif self.status == SchedulerStatus.RECOVERY:
            job = self.jobs.all().order_by("-job_num").first()
            if job and job.progress:
                progress = ChroniclerProgress.from_dict(job.progress)
                job_args = args_gen.recovery_args(job.job_args["job_args"], progress)
            else:
                job_args = args_gen.initial_args(self.task_args)
        elif self.status == SchedulerStatus.CANCELED:
            job = self.jobs.order_by("-job_num").first()
            if job and job.status == SchedulerStatus.CANCELED:
                job_args = job.job_args["job_args"]
            else:
                job_args = args_gen.initial_args(self.task_args)
        else:
            job_args = args_gen.initial_args(self.task_args)

        task_args["job_args"] = job_args

        return task_args

    def can_be_retried(self):
        return True

    @property
    def default_job_queue(self):
        return settings.GRIMOIRELAB_Q_EVENTIZER_JOBS

    @staticmethod
    def job_function(*args, **kwargs):
        return chronicler_job(*args, **kwargs)

    @staticmethod
    def on_success_callback(*args, **kwargs):
        return _on_success_callback(*args, **kwargs)

    @staticmethod
    def on_failure_callback(*args, **kwargs):
        return _on_failure_callback(*args, **kwargs)


class BaseIdentitiesTask(Task):
    """Base class for Identities tasks and jobs."""

    # This attribute indicates the additional arguments used to run the task
    # to simplify methods like create_task, prepare_job_parameters and serializers.
    EXTRA_TASK_FIELDS = []

    @classmethod
    def create_task(
        cls,
        task_args: dict[str, Any],
        job_interval: int,
        job_max_retries: int,
        burst: bool = False,
        *args,
        **kwargs,
    ) -> Self:
        """Create a new Identities task.

        This method will create a new Identities task. Besides the
        common arguments to create a task, this method requires
        additional arguments specific to the Identities tasks that
        could be defined in the `EXTRA_TASK_FIELDS` attribute.
        """
        task = super().create_task(
            task_args, job_interval, job_max_retries, burst=burst, *args, **kwargs
        )
        for field in cls.EXTRA_TASK_FIELDS:
            if field in kwargs:
                setattr(task, field, kwargs[field])
        task.save()

        return task

    def prepare_job_parameters(self):
        """Generate the parameters for a new job.

        By default, this method will generate the parameters
        for a new job based on the original parameters set for the task.
        If the task has additional fields defined in the
        `EXTRA_TASK_FIELDS` attribute, those fields will be added
        to the job arguments.
        """
        system_user = get_user_model().objects.get(username=settings.SYSTEM_BOT_USER)
        ctx = SortingHatContext(user=system_user, job_id=None, tenant=None)

        job_args = {
            "ctx": ctx,
        }
        for field in self.EXTRA_TASK_FIELDS:
            job_args[field] = getattr(self, field)

        return job_args

    def can_be_retried(self):
        return True

    @property
    def default_job_queue(self):
        return settings.GRIMOIRELAB_Q_SORTINGHAT_JOBS

    @staticmethod
    def on_success_callback(*args, **kwargs):
        return _on_success_callback(*args, **kwargs)

    @staticmethod
    def on_failure_callback(*args, **kwargs):
        return _on_failure_callback(*args, **kwargs)

    class Meta:
        abstract = True


class RecommendAffiliationsTask(BaseIdentitiesTask):
    """Task to generate a list of affiliation recommendations from individuals.

    This task generates a list of recommendations which include the
    organizations where individuals can be affiliated.
    This job returns a dictionary with which individuals are recommended to be
    affiliated to which organization.
    """

    TASK_TYPE = "recommend_affiliations"
    EXTRA_TASK_FIELDS = ["uuids", "last_modified"]

    uuids = JSONField(null=True, default=None)
    last_modified = DateTimeField(default=MIN_PERIOD_DATE)

    @staticmethod
    def job_function(*args, **kwargs):
        ctx = kwargs.get("ctx")
        if ctx and not isinstance(ctx, SortingHatContext):
            ctx[0] = get_user_model().objects.get(username=ctx[0])
            kwargs["ctx"] = SortingHatContext(*ctx)

        return recommend_affiliations(*args, **kwargs)


class RecommendMatchesTask(BaseIdentitiesTask):
    """Task to generate affiliation recommendations.

    This task generates a list of recommendations which include the
    matching identities from the individuals which can be merged with.
    This task returns a dictionary with which individuals are recommended to be
    merged to which individual (or which identities if `verbose` mode is activated).
    """

    TASK_TYPE = "recommend_matches"
    EXTRA_TASK_FIELDS = [
        "criteria",
        "source_uuids",
        "target_uuids",
        "exclude",
        "strict",
        "match_source",
        "guess_github_user",
        "last_modified",
    ]

    criteria = JSONField(null=True, default=None)
    source_uuids = JSONField(null=True, default=None)
    target_uuids = JSONField(null=True, default=None)
    exclude = BooleanField(default=True)
    strict = BooleanField(default=True)
    match_source = BooleanField(default=False)
    guess_github_user = BooleanField(default=False)
    last_modified = DateTimeField(default=MIN_PERIOD_DATE)

    @staticmethod
    def job_function(*args, **kwargs):
        ctx = kwargs.get("ctx")
        if ctx and not isinstance(ctx, SortingHatContext):
            ctx[0] = get_user_model().objects.get(username=ctx[0])
            kwargs["ctx"] = SortingHatContext(*ctx)

        return recommend_matches(*args, **kwargs)


class RecommendGenderTask(BaseIdentitiesTask):
    """Task to generate a list of gender recommendations.

    This task generates a list of recommendations with the
    probable gender of the given individuals.
    """

    TASK_TYPE = "recommend_gender"
    EXTRA_TASK_FIELDS = ["uuids", "exclude", "no_strict_matching"]

    uuids = JSONField(null=True, default=None)
    exclude = BooleanField(default=True)
    no_strict_matching = BooleanField(default=False)

    @staticmethod
    def job_function(*args, **kwargs):
        ctx = kwargs.get("ctx")
        if ctx and not isinstance(ctx, SortingHatContext):
            ctx[0] = get_user_model().objects.get(username=ctx[0])
            kwargs["ctx"] = SortingHatContext(*ctx)

        return recommend_gender(*args, **kwargs)


class AffiliateTask(BaseIdentitiesTask):
    """Task to Affiliates identities in SortingHat.

    This task automates the affiliation process obtaining
    a list of recommendations where individuals can be
    affiliated. After that, individuals are enrolled to them.
    The job returns a dictionary with which individuals were
    enrolled and the errors generated during this process.
    """

    TASK_TYPE = "affiliate"
    EXTRA_TASK_FIELDS = ["uuids", "last_modified"]

    uuids = JSONField(null=True, default=None)
    last_modified = DateTimeField(default=MIN_PERIOD_DATE)

    @staticmethod
    def job_function(*args, **kwargs):
        ctx = kwargs.get("ctx")
        if ctx and not isinstance(ctx, SortingHatContext):
            ctx[0] = get_user_model().objects.get(username=ctx[0])
            kwargs["ctx"] = SortingHatContext(*ctx)

        return affiliate(*args, **kwargs)


class UnifyTask(BaseIdentitiesTask):
    """Task to Unify identities in SortingHat.

    This task automates the identities unify process obtaining
    a list of recommendations where matching individuals can be merged.
    After that, matching individuals are merged.
    This job returns a list with the individuals which have been merged
    and the errors generated during this process.
    """

    TASK_TYPE = "unify"
    EXTRA_TASK_FIELDS = [
        "criteria",
        "source_uuids",
        "target_uuids",
        "exclude",
        "strict",
        "match_source",
        "guess_github_user",
        "last_modified",
    ]

    criteria = JSONField(null=True, default=None)
    source_uuids = JSONField(null=True, default=None)
    target_uuids = JSONField(null=True, default=None)
    exclude = BooleanField(default=True)
    strict = BooleanField(default=True)
    match_source = BooleanField(default=False)
    guess_github_user = BooleanField(default=False)
    last_modified = DateTimeField(default=MIN_PERIOD_DATE)

    @staticmethod
    def job_function(*args, **kwargs):
        ctx = kwargs.get("ctx")
        if ctx and not isinstance(ctx, SortingHatContext):
            ctx[0] = get_user_model().objects.get(username=ctx[0])
            kwargs["ctx"] = SortingHatContext(*ctx)

        return unify(*args, **kwargs)


class GenderizeTask(BaseIdentitiesTask):
    """Task to assign a gender to a set of individuals.

    This task autocompletes the gender information (stored in
    the profile) of unique identities after obtaining a list
    of recommendations for their gender based on their name.
    """

    TASK_TYPE = "genderize"
    EXTRA_TASK_FIELDS = ["uuids", "exclude", "no_strict_matching"]

    uuids = JSONField(null=True, default=None)
    exclude = BooleanField(default=True)
    no_strict_matching = BooleanField(default=False)

    @staticmethod
    def job_function(*args, **kwargs):
        ctx = kwargs.get("ctx")
        if ctx and not isinstance(ctx, SortingHatContext):
            ctx[0] = get_user_model().objects.get(username=ctx[0])
            kwargs["ctx"] = SortingHatContext(*ctx)

        return genderize(*args, **kwargs)


class ImportIdentitiesTask(BaseIdentitiesTask):
    """Task to Import identities in SortingHat."""

    TASK_TYPE = "import_identities"
    EXTRA_TASK_FIELDS = ["backend_name", "url"]

    backend_name = CharField(max_length=255)
    url = CharField(max_length=2048)

    @classmethod
    def create_task(
        cls,
        task_args: dict[str, Any],
        job_interval: int,
        job_max_retries: int,
        backend_name: str,
        url: str,
        burst: bool = False,
        *args,
        **kwargs,
    ) -> Self:
        """Create a new task to import identities to SortingHat.

        This task imports identities to SortingHat using the
        data obtained from the URL using the specified backend.
        """
        task = super().create_task(
            task_args, job_interval, job_max_retries, burst=burst, *args, **kwargs
        )
        task.backend_name = backend_name
        task.url = url
        task.save()

        return task

    @staticmethod
    def job_function(*args, **kwargs):
        ctx = kwargs.get("ctx")
        if ctx and not isinstance(ctx, SortingHatContext):
            ctx[0] = get_user_model().objects.get(username=ctx[0])
            kwargs["ctx"] = SortingHatContext(*ctx)

        return import_identities(*args, **kwargs)

    def prepare_job_parameters(self):
        """Generate the parameters for a new job.

        This method generates the parameters required to
        execute the job associated with this task. If the task
        has been executed before, it includes the timestamp of
        the last modification to only import new or updated
        identities.
        """

        system_user = get_user_model().objects.get(username=settings.SYSTEM_BOT_USER)
        ctx = SortingHatContext(user=system_user, job_id=None, tenant=None)

        job_args = {
            "ctx": ctx,
            "backend_name": self.backend_name,
            "url": self.url,
            **self.task_args,
        }
        backends = find_import_identities_backends()
        try:
            backend_args = backends[self.backend_name]["args"]
        except KeyError:
            backend_args = {}
        if "from_date" in backend_args:
            last_job = self.jobs.order_by("job_num").filter(status=SchedulerStatus.COMPLETED).last()
            if last_job and last_job.started_at:
                job_args["from_date"] = last_job.started_at.isoformat()

        return job_args


register_task_model(EventizerTask.TASK_TYPE, EventizerTask)
register_task_model(AffiliateTask.TASK_TYPE, AffiliateTask)
register_task_model(UnifyTask.TASK_TYPE, UnifyTask)
register_task_model(GenderizeTask.TASK_TYPE, GenderizeTask)
register_task_model(RecommendAffiliationsTask.TASK_TYPE, RecommendAffiliationsTask)
register_task_model(RecommendMatchesTask.TASK_TYPE, RecommendMatchesTask)
register_task_model(RecommendGenderTask.TASK_TYPE, RecommendGenderTask)
register_task_model(ImportIdentitiesTask.TASK_TYPE, ImportIdentitiesTask)
