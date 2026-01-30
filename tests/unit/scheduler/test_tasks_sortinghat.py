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

import unittest

from typing import Any

import django_rq

from django.conf import settings
from django.contrib.auth import get_user_model

from grimoirelab.core.scheduler.models import register_task_model
from grimoirelab_toolkit.datetime import datetime_utcnow, str_to_datetime

from grimoirelab.core.scheduler.scheduler import schedule_task, reschedule_task
from grimoirelab.core.scheduler.tasks.models import (
    AffiliateTask,
    UnifyTask,
    RecommendAffiliationsTask,
    RecommendMatchesTask,
    ImportIdentitiesTask,
)

from sortinghat.core import api
from sortinghat.core.context import SortingHatContext
from sortinghat.core.importer.backend import IdentitiesImporter
from sortinghat.core.models import Individual, AffiliationRecommendation, MergeRecommendation


from ..base import GrimoireLabTestCase


def setup_sortinghat_database() -> dict[str, Any]:
    """Set up SortingHat database for tests.

    The individuals and organizations are obtained partially from tests
    in Sortinghat: https://github.com/chaoss/grimoirelab-sortinghat

    returns: A dictionary with created objects.
    """
    user = get_user_model().objects.create(username="test")
    ctx = SortingHatContext(user)

    # Organizations and domains
    org_1 = api.add_organization(ctx, "Example")
    api.add_domain(ctx, "Example", "example.com", is_top_domain=True)

    org_2 = api.add_organization(ctx, "Example Int.")
    api.add_domain(ctx, "Example Int.", "u.example.com", is_top_domain=True)
    api.add_domain(ctx, "Example Int.", "es.u.example.com")
    api.add_domain(ctx, "Example Int.", "en.u.example.com")

    org_3 = api.add_organization(ctx, "Bitergia")
    api.add_domain(ctx, "Bitergia", "bitergia.com")
    api.add_domain(ctx, "Bitergia", "bitergia.org")

    api.add_organization(ctx, "LibreSoft")

    # john_smith identity
    john_smith = api.add_identity(ctx, email="jsmith@example.com", name="John Smith", source="scm")
    js2 = api.add_identity(ctx, name="John Smith", source="scm", uuid=john_smith.uuid)
    js3 = api.add_identity(ctx, username="jsmith", source="scm", uuid=john_smith.uuid)

    # jsmith
    jsmith = api.add_identity(ctx, name="J. Smith", username="john_smith", source="alt")
    jsm2 = api.add_identity(
        ctx, name="John Smith", username="jsmith", source="alt", uuid=jsmith.uuid
    )
    jsm3 = api.add_identity(ctx, email="jsmith@example.com", source="alt", uuid=jsmith.uuid)

    # jane_rae
    jane_rae = api.add_identity(ctx, name="Janer Rae", source="mls")
    jr2 = api.add_identity(
        ctx, email="jane.rae@example.net", name="Jane Rae Doe", source="mls", uuid=jane_rae.uuid
    )

    # js_alt
    js_alt = api.add_identity(ctx, name="J. Smith", username="john_smith", source="scm")
    js_alt2 = api.add_identity(
        ctx, email="J_Smith@bitergia.com", username="john_smith", source="mls", uuid=js_alt.uuid
    )
    js_alt3 = api.add_identity(ctx, username="Smith. J", source="mls", uuid=js_alt.uuid)
    js_alt4 = api.add_identity(
        ctx, email="J_Smith@bitergia.com", name="Smith. J", source="mls", uuid=js_alt.uuid
    )

    # jrae
    jrae = api.add_identity(ctx, email="jrae@example.net", name="Jane Rae Doe", source="mls")
    jrae2 = api.add_identity(ctx, name="jrae", source="mls", uuid=jrae.uuid)
    jrae3 = api.add_identity(ctx, name="jrae", source="scm", uuid=jrae.uuid)

    return {
        "org_1": org_1,
        "org_2": org_2,
        "org_3": org_3,
        "john_smith": john_smith,
        "js2": js2,
        "js3": js3,
        "jsmith": jsmith,
        "jsm2": jsm2,
        "jsm3": jsm3,
        "jane_rae": jane_rae,
        "jr2": jr2,
        "js_alt": js_alt,
        "js_alt2": js_alt2,
        "js_alt3": js_alt3,
        "js_alt4": js_alt4,
        "jrae": jrae,
        "jrae2": jrae2,
        "jrae3": jrae3,
    }


class TestAffiliateTask(GrimoireLabTestCase):
    """Unit tests for AffiliateTask class"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # GRIMOIRELAB_TASK_MODELS is empty from other tests that removes the tasks
        try:
            register_task_model(AffiliateTask.TASK_TYPE, AffiliateTask)
        except ValueError:
            # Already registered
            pass

    def setUp(self):
        """Initialize database with a dataset"""

        get_user_model().objects.get_or_create(username=settings.SYSTEM_BOT_USER)

        data = setup_sortinghat_database()
        for key, value in data.items():
            setattr(self, key, value)

    def test_affiliate_task(self):
        """Test affiliate task execution"""

        task = schedule_task("affiliate", task_args={}, burst=True, uuids=[self.jsmith.uuid])
        self.assertIsInstance(task, AffiliateTask)
        self.assertEqual(task.uuids, [self.jsmith.uuid])

        # Execute the job
        worker = django_rq.workers.get_worker(task.default_job_queue)
        processed = worker.work(burst=True, with_scheduler=True)
        self.assertEqual(processed, 1)

        # Check database objects
        individual_db = Individual.objects.get(mk=self.john_smith.uuid)
        enrollments_db = individual_db.enrollments.all()
        self.assertEqual(len(enrollments_db), 0)

        individual_db = Individual.objects.get(mk=self.jsmith.uuid)
        enrollments_db = individual_db.enrollments.all()
        self.assertEqual(len(enrollments_db), 1)
        enrollment_db_1 = enrollments_db[0]
        self.assertEqual(enrollment_db_1.group.name, self.org_1.name)


class TestRecommendAffiliationsTask(GrimoireLabTestCase):
    """Unit tests for RecommendAffiliationsTask class"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # GRIMOIRELAB_TASK_MODELS might be empty from other tests that removes the tasks
        try:
            register_task_model(RecommendAffiliationsTask.TASK_TYPE, RecommendAffiliationsTask)
        except ValueError:
            # Already registered
            pass

    def setUp(self):
        """Initialize database with a dataset"""

        get_user_model().objects.get_or_create(username=settings.SYSTEM_BOT_USER)

        data = setup_sortinghat_database()
        for key, value in data.items():
            setattr(self, key, value)

    def test_recommend_affiliations_task(self):
        """Test recommend affiliations task execution"""

        task = schedule_task("recommend_affiliations", task_args={}, burst=True)
        self.assertIsInstance(task, RecommendAffiliationsTask)
        self.assertEqual(task.uuids, None)

        # Execute the job
        worker = django_rq.workers.get_worker(task.default_job_queue)
        processed = worker.work(burst=True, with_scheduler=True)
        self.assertEqual(processed, 1)

        # Check database objects
        recommendations = AffiliationRecommendation.objects.all()
        self.assertEqual(len(recommendations), 3)

        for recommendation in recommendations:
            if recommendation.individual.mk == self.john_smith.uuid:
                self.assertEqual(recommendation.organization.name, self.org_1.name)
            elif recommendation.individual.mk == self.jsmith.uuid:
                self.assertEqual(recommendation.organization.name, self.org_1.name)
            elif recommendation.individual.mk == self.js_alt.uuid:
                self.assertEqual(recommendation.organization.name, self.org_3.name)
            else:
                self.fail("Unexpected individual in affiliation recommendations")


class TestUnifyTask(GrimoireLabTestCase):
    """Unit tests for UnifyTask class"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # GRIMOIRELAB_TASK_MODELS might be empty from other tests that removes the tasks
        try:
            register_task_model(UnifyTask.TASK_TYPE, UnifyTask)
        except ValueError:
            # Already registered
            pass

    def setUp(self):
        """Initialize database with a dataset"""

        get_user_model().objects.get_or_create(username=settings.SYSTEM_BOT_USER)

        data = setup_sortinghat_database()
        for key, value in data.items():
            setattr(self, key, value)

    def test_task(self):
        """Test unify task execution"""

        source_uuids = [self.john_smith.uuid, self.jrae3.uuid, self.jr2.uuid]
        target_uuids = [
            self.john_smith.uuid,
            self.js2.uuid,
            self.js3.uuid,
            self.jsmith.uuid,
            self.jsm2.uuid,
            self.jsm3.uuid,
            self.jane_rae.uuid,
            self.jr2.uuid,
            self.js_alt.uuid,
            self.js_alt2.uuid,
            self.js_alt3.uuid,
            self.js_alt4.uuid,
            self.jrae.uuid,
            self.jrae2.uuid,
            self.jrae3.uuid,
        ]
        criteria = ["email", "name", "username"]

        task = schedule_task(
            "unify",
            task_args={},
            burst=True,
            criteria=criteria,
            source_uuids=source_uuids,
            target_uuids=target_uuids,
        )
        self.assertIsInstance(task, UnifyTask)
        self.assertEqual(task.source_uuids, source_uuids)
        self.assertEqual(task.target_uuids, target_uuids)
        self.assertEqual(task.criteria, criteria)

        # Execute the job
        worker = django_rq.workers.get_worker(task.default_job_queue)
        processed = worker.work(burst=True, with_scheduler=True)
        self.assertEqual(processed, 1)

        # Checking if the identities have been merged
        # Individual 1
        individual_1 = Individual.objects.get(mk=self.jsmith.uuid)
        identities = individual_1.identities.all()
        self.assertEqual(len(identities), 6)

        id1 = identities[0]
        self.assertEqual(id1, self.jsm2)

        id2 = identities[1]
        self.assertEqual(id2, self.jsmith)

        id3 = identities[2]
        self.assertEqual(id3, self.jsm3)

        id4 = identities[3]
        self.assertEqual(id4, self.john_smith)

        id5 = identities[4]
        self.assertEqual(id5, self.js2)

        id6 = identities[5]
        self.assertEqual(id6, self.js3)

        # Individual 2
        individual_2 = Individual.objects.get(mk=self.jrae.uuid)
        identities = individual_2.identities.all()
        self.assertEqual(len(identities), 5)

        id1 = identities[0]
        self.assertEqual(id1, self.jrae2)

        id2 = identities[1]
        self.assertEqual(id2, self.jrae3)

        id3 = identities[2]
        self.assertEqual(id3, self.jrae)

        id4 = identities[3]
        self.assertEqual(id4, self.jane_rae)

        id5 = identities[4]
        self.assertEqual(id5, self.jr2)


class TestRecommendMatchesTask(GrimoireLabTestCase):
    """Unit tests for RecommendMatchesTask class"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # GRIMOIRELAB_TASK_MODELS might be empty from other tests that removes the tasks
        try:
            register_task_model(RecommendMatchesTask.TASK_TYPE, RecommendMatchesTask)
        except ValueError:
            # Already registered
            pass

    def setUp(self):
        """Initialize database with a dataset"""

        get_user_model().objects.get_or_create(username=settings.SYSTEM_BOT_USER)

        data = setup_sortinghat_database()
        for key, value in data.items():
            setattr(self, key, value)

    def test_recommend_matches_task(self):
        """Test recommend matches task execution"""

        criteria = ["email", "name", "username"]

        task = schedule_task(
            "recommend_matches",
            task_args={},
            burst=True,
            criteria=criteria,
        )
        self.assertIsInstance(task, RecommendMatchesTask)
        self.assertEqual(task.source_uuids, None)
        self.assertEqual(task.target_uuids, None)
        self.assertEqual(task.criteria, criteria)

        # Execute the job
        worker = django_rq.workers.get_worker(task.default_job_queue)
        processed = worker.work(burst=True, with_scheduler=True)
        self.assertEqual(processed, 1)

        # Check database objects
        recommendations_expected = [
            sorted([self.js_alt.individual.mk, self.jsmith.individual.mk]),
            sorted([self.jsmith.individual.mk, self.john_smith.individual.mk]),
            sorted([self.jrae.individual.mk, self.jane_rae.individual.mk]),
        ]

        recommendations = MergeRecommendation.objects.all()
        self.assertEqual(len(recommendations), 3)
        for recommendation in recommendations:
            uuids = [recommendation.individual1.mk, recommendation.individual2.mk]
            self.assertIn(uuids, recommendations_expected)


class MockTestImporter(IdentitiesImporter):
    NAME = "test_backend"

    def __init__(self, ctx, url, from_date=None, token=None):
        super().__init__(ctx, url)
        self.token = token
        self.from_date = from_date

    def get_individuals(self):
        from sortinghat.core.importer.models import Individual, Identity

        indiv = Individual()
        indiv.identities.append(Identity(source="test_backend", username="test_user"))
        return [indiv]


class TestImportIdentities(GrimoireLabTestCase):
    """Unit tests for import_identities"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # GRIMOIRELAB_TASK_MODELS might be empty from other tests that removes the tasks
        try:
            register_task_model(ImportIdentitiesTask.TASK_TYPE, ImportIdentitiesTask)
        except ValueError:
            # Already registered
            pass

    def setUp(self):
        """Initialize database"""

        self.user = get_user_model().objects.get_or_create(username=settings.SYSTEM_BOT_USER)

    @unittest.mock.patch("sortinghat.core.importer.backend.find_backends")
    def test_import_identities(self, mock_find_backends):
        """Check if the importer is executed correctly"""

        mock_find_backends.return_value = {"test_backend": MockTestImporter}

        task = schedule_task(
            "import_identities",
            task_args={},
            burst=True,
            backend_name="test_backend",
            url="my_url",
        )
        self.assertIsInstance(task, ImportIdentitiesTask)
        self.assertEqual(task.backend_name, "test_backend")
        self.assertEqual(task.url, "my_url")

        dt_before = datetime_utcnow()

        # Execute the job
        worker = django_rq.workers.get_worker(task.default_job_queue)
        processed = worker.work(burst=True, with_scheduler=True)
        self.assertEqual(processed, 1)

        dt_after = datetime_utcnow()

        # Check individual and identity are inserted
        indiv = Individual.objects.first()
        identity = indiv.identities.first()
        self.assertEqual(identity.source, "test_backend")
        self.assertEqual(identity.username, "test_user")

        # The next execution the from_date should be set
        reschedule_task(task.uuid)

        job = task.jobs.order_by("-created_at").first()

        self.assertIsNotNone(job)
        self.assertIn("from_date", job.job_args)
        self.assertGreater(str_to_datetime(job.job_args["from_date"]), dt_before)
        self.assertLess(str_to_datetime(job.job_args["from_date"]), dt_after)
