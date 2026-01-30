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

from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from grimoirelab.core.scheduler.models import (
    SchedulerStatus,
    get_all_registered_task_names,
)
from grimoirelab.core.scheduler.tasks.models import (
    EventizerTask,
    AffiliateTask,
    UnifyTask,
    GenderizeTask,
    ImportIdentitiesTask,
    RecommendAffiliationsTask,
    RecommendGenderTask,
    RecommendMatchesTask,
)


class ListTaskTypesApiTest(APITestCase):
    """Unit tests for the List Task Types API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_list_task_types(self):
        """Test that it returns a list of available task types"""

        url = reverse("task-types")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        names = get_all_registered_task_names()
        for name in names:
            self.assertIn(name, response.data)

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        url = reverse("task-types")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Authentication credentials were not provided.")


class CreateTasksApiTest(APITestCase):
    """Unit tests for the Create Tasks API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        get_user_model().objects.get_or_create(username=settings.SYSTEM_BOT_USER)
        self.client.force_authenticate(user=user)

    def test_create_eventizer_task(self):
        """Test creating an eventizer task"""

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        data = {
            "datasource_type": "git",
            "datasource_category": "commit",
            "task_args": {"uri": "https://github.com/example/repo.git"},
            "job_interval": 3600,
            "job_max_retries": 5,
            "burst": True,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], SchedulerStatus.ENQUEUED.label)
        self.assertEqual(response.data["datasource_type"], "git")
        self.assertEqual(response.data["datasource_category"], "commit")
        self.assertEqual(response.data["task_args"], {"uri": "https://github.com/example/repo.git"})
        self.assertEqual(response.data["job_interval"], 3600)
        self.assertEqual(response.data["job_max_retries"], 5)
        self.assertEqual(response.data["burst"], True)

    def test_create_affiliate_task(self):
        """Test creating an affiliate task"""

        url = reverse("tasks", kwargs={"task_type": "affiliate"})
        data = {
            "task_args": {},
            "job_interval": 3600,
            "job_max_retries": 5,
            "burst": True,
            "uuids": ["uuid1", "uuid2"],
            # last_modified is optional, defaulted in model
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], SchedulerStatus.ENQUEUED.label)
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["job_interval"], 3600)
        self.assertEqual(response.data["job_max_retries"], 5)
        self.assertEqual(response.data["burst"], True)
        self.assertEqual(response.data["uuids"], ["uuid1", "uuid2"])
        self.assertEqual(response.data["last_modified"], "1900-01-01T00:00:00Z")

    def test_create_unify_task(self):
        """Test creating a unify task"""

        url = reverse("tasks", kwargs={"task_type": "unify"})
        data = {
            "task_args": {},
            "job_interval": 3600,
            "job_max_retries": 5,
            "burst": True,
            "criteria": {"email": True},
            "source_uuids": ["uuid1"],
            "target_uuids": ["uuid2"],
            "exclude": False,
            "strict": True,
            "match_source": False,
            "guess_github_user": False,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], SchedulerStatus.ENQUEUED.label)
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["criteria"], {"email": True})
        self.assertEqual(response.data["source_uuids"], ["uuid1"])
        self.assertEqual(response.data["target_uuids"], ["uuid2"])
        self.assertEqual(response.data["exclude"], False)
        self.assertEqual(response.data["strict"], True)
        self.assertEqual(response.data["match_source"], False)
        self.assertEqual(response.data["guess_github_user"], False)

    def test_create_genderize_task(self):
        """Test creating a genderize task"""

        url = reverse("tasks", kwargs={"task_type": "genderize"})
        data = {
            "task_args": {},
            "job_interval": 3600,
            "job_max_retries": 5,
            "burst": True,
            "uuids": ["uuid1", "uuid2"],
            "exclude": False,
            "no_strict_matching": True,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], SchedulerStatus.ENQUEUED.label)
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["uuids"], ["uuid1", "uuid2"])
        self.assertEqual(response.data["exclude"], False)
        self.assertEqual(response.data["no_strict_matching"], True)

    def test_create_import_identities_task(self):
        """Test creating an import identities task"""

        url = reverse("tasks", kwargs={"task_type": "import_identities"})
        data = {
            "task_args": {},
            "job_interval": 3600,
            "job_max_retries": 5,
            "burst": True,
            "backend_name": "test_backend",
            "url": "https://example.com/identities.json",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], SchedulerStatus.ENQUEUED.label)
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["backend_name"], "test_backend")
        self.assertEqual(response.data["url"], "https://example.com/identities.json")

    def test_create_recommend_affiliations_task(self):
        """Test creating a recommend affiliations task"""

        url = reverse("tasks", kwargs={"task_type": "recommend_affiliations"})
        data = {
            "task_args": {},
            "job_interval": 3600,
            "job_max_retries": 5,
            "burst": True,
            "uuids": ["uuid1", "uuid2"],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], SchedulerStatus.ENQUEUED.label)
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["uuids"], ["uuid1", "uuid2"])

    def test_create_recommend_gender_task(self):
        """Test creating a recommend gender task"""

        url = reverse("tasks", kwargs={"task_type": "recommend_gender"})
        data = {
            "task_args": {},
            "job_interval": 3600,
            "job_max_retries": 5,
            "burst": True,
            "uuids": ["uuid1", "uuid2"],
            "exclude": False,
            "no_strict_matching": True,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], SchedulerStatus.ENQUEUED.label)
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["uuids"], ["uuid1", "uuid2"])
        self.assertEqual(response.data["exclude"], False)
        self.assertEqual(response.data["no_strict_matching"], True)

    def test_create_recommend_matches_task(self):
        """Test creating a recommend matches task"""

        url = reverse("tasks", kwargs={"task_type": "recommend_matches"})
        data = {
            "task_args": {},
            "job_interval": 3600,
            "job_max_retries": 5,
            "burst": True,
            "criteria": {"email": True},
            "source_uuids": ["uuid1"],
            "exclude": False,
            "strict": True,
            "match_source": False,
            "guess_github_user": False,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], SchedulerStatus.ENQUEUED.label)
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["criteria"], {"email": True})
        self.assertEqual(response.data["source_uuids"], ["uuid1"])
        self.assertEqual(response.data["target_uuids"], None)
        self.assertEqual(response.data["exclude"], False)
        self.assertEqual(response.data["strict"], True)
        self.assertEqual(response.data["match_source"], False)
        self.assertEqual(response.data["guess_github_user"], False)

    def test_create_task_invalid_type(self):
        """Test creating a task with an invalid task type"""

        url = reverse("tasks", kwargs={"task_type": "invalid-type"})
        data = {
            "task_args": {},
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown task type", str(response.data))

    def test_create_task_missing_required_fields(self):
        """Test creating a task with missing required fields"""

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        data = {
            "datasource_type": "git",
            # Missing datasource_category and task_args
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ListTasksAPITestCase(APITestCase):
    """Test case for listing tasks via the API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        get_user_model().objects.get_or_create(username=settings.SYSTEM_BOT_USER)
        self.client.force_authenticate(user=user)

    def test_list_eventizer_tasks(self):
        """Test that it returns a list of eventizer tasks"""

        # Create some test tasks
        task1 = EventizerTask.create_task(
            task_args={"uri": "https://github.com/example/repo1.git"},
            job_interval=3600,
            job_max_retries=3,
            datasource_type="git",
            datasource_category="commit",
        )
        task2 = EventizerTask.create_task(
            task_args={"uri": "https://github.com/example/repo2"},
            job_interval=3600,
            job_max_retries=3,
            datasource_type="github",
            datasource_category="issue",
        )

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        task_data = response.data["results"][0]
        self.assertEqual(task1.uuid, task_data["uuid"])
        self.assertEqual(task1.datasource_type, task_data["datasource_type"])
        self.assertEqual(task1.datasource_category, task_data["datasource_category"])
        self.assertEqual(task1.task_args, task_data["task_args"])
        self.assertEqual(task1.job_interval, task_data["job_interval"])
        self.assertEqual(task1.job_max_retries, task_data["job_max_retries"])

        task_data = response.data["results"][1]
        self.assertEqual(task2.uuid, task_data["uuid"])
        self.assertEqual(task2.datasource_type, task_data["datasource_type"])
        self.assertEqual(task2.datasource_category, task_data["datasource_category"])
        self.assertEqual(task2.task_args, task_data["task_args"])
        self.assertEqual(task2.job_interval, task_data["job_interval"])
        self.assertEqual(task2.job_max_retries, task_data["job_max_retries"])

    def test_list_affiliate_tasks(self):
        """Test that it returns a list of affiliate tasks"""

        task1 = AffiliateTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            uuids=["uuid1", "uuid2"],
        )
        task2 = AffiliateTask.create_task(
            task_args={},
            job_interval=7200,
            job_max_retries=2,
            uuids=["uuid3"],
        )

        url = reverse("tasks", kwargs={"task_type": "affiliate"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        task_data = response.data["results"][0]
        self.assertEqual(task1.uuid, task_data["uuid"])
        self.assertEqual(task1.uuids, task_data["uuids"])
        self.assertEqual(task1.task_args, task_data["task_args"])
        self.assertEqual(task1.job_interval, task_data["job_interval"])
        self.assertEqual(task1.job_max_retries, task_data["job_max_retries"])

        task_data = response.data["results"][1]
        self.assertEqual(task2.uuid, task_data["uuid"])
        self.assertEqual(task2.uuids, task_data["uuids"])
        self.assertEqual(task2.task_args, task_data["task_args"])
        self.assertEqual(task2.job_interval, task_data["job_interval"])
        self.assertEqual(task2.job_max_retries, task_data["job_max_retries"])

    def test_list_unify_tasks(self):
        """Test that it returns a list of unify tasks"""

        task1 = UnifyTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            criteria={"email": True},
            source_uuids=["uuid1"],
            target_uuids=["uuid2"],
            exclude=False,
            strict=True,
            match_source=False,
            guess_github_user=False,
        )
        task2 = UnifyTask.create_task(
            task_args={},
            job_interval=7200,
            job_max_retries=2,
            criteria={"email": False},
            source_uuids=["uuid3"],
            target_uuids=["uuid4"],
            exclude=True,
            strict=False,
            match_source=True,
            guess_github_user=True,
        )

        url = reverse("tasks", kwargs={"task_type": "unify"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        task_data = response.data["results"][0]
        self.assertEqual(task1.uuid, task_data["uuid"])
        self.assertEqual(task1.criteria, task_data["criteria"])
        self.assertEqual(task1.source_uuids, task_data["source_uuids"])
        self.assertEqual(task1.target_uuids, task_data["target_uuids"])
        self.assertEqual(task1.exclude, task_data["exclude"])
        self.assertEqual(task1.strict, task_data["strict"])
        self.assertEqual(task1.match_source, task_data["match_source"])
        self.assertEqual(task1.guess_github_user, task_data["guess_github_user"])
        self.assertEqual(task1.task_args, task_data["task_args"])
        self.assertEqual(task1.job_interval, task_data["job_interval"])
        self.assertEqual(task1.job_max_retries, task_data["job_max_retries"])

        task_data = response.data["results"][1]
        self.assertEqual(task2.uuid, task_data["uuid"])
        self.assertEqual(task2.criteria, task_data["criteria"])
        self.assertEqual(task2.source_uuids, task_data["source_uuids"])
        self.assertEqual(task2.target_uuids, task_data["target_uuids"])
        self.assertEqual(task2.exclude, task_data["exclude"])
        self.assertEqual(task2.strict, task_data["strict"])
        self.assertEqual(task2.match_source, task_data["match_source"])
        self.assertEqual(task2.guess_github_user, task_data["guess_github_user"])
        self.assertEqual(task2.task_args, task_data["task_args"])
        self.assertEqual(task2.job_interval, task_data["job_interval"])
        self.assertEqual(task2.job_max_retries, task_data["job_max_retries"])

    def test_list_genderize_tasks(self):
        """Test that it returns a list of genderize tasks"""

        task1 = GenderizeTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            uuids=["uuid1", "uuid2"],
            exclude=False,
            no_strict_matching=True,
        )
        task2 = GenderizeTask.create_task(
            task_args={},
            job_interval=7200,
            job_max_retries=2,
            uuids=["uuid3"],
            exclude=True,
            no_strict_matching=False,
        )

        url = reverse("tasks", kwargs={"task_type": "genderize"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        task_data = response.data["results"][0]
        self.assertEqual(task1.uuid, task_data["uuid"])
        self.assertEqual(task1.uuids, task_data["uuids"])
        self.assertEqual(task1.exclude, task_data["exclude"])
        self.assertEqual(task1.no_strict_matching, task_data["no_strict_matching"])
        self.assertEqual(task1.task_args, task_data["task_args"])
        self.assertEqual(task1.job_interval, task_data["job_interval"])
        self.assertEqual(task1.job_max_retries, task_data["job_max_retries"])

        task_data = response.data["results"][1]
        self.assertEqual(task2.uuid, task_data["uuid"])
        self.assertEqual(task2.uuids, task_data["uuids"])
        self.assertEqual(task2.exclude, task_data["exclude"])
        self.assertEqual(task2.no_strict_matching, task_data["no_strict_matching"])
        self.assertEqual(task2.task_args, task_data["task_args"])
        self.assertEqual(task2.job_interval, task_data["job_interval"])
        self.assertEqual(task2.job_max_retries, task_data["job_max_retries"])

    def test_list_import_identities_tasks(self):
        """Test that it returns a list of import identities tasks"""

        task1 = ImportIdentitiesTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            backend_name="test_backend1",
            url="https://example.com/identities1.json",
        )
        task2 = ImportIdentitiesTask.create_task(
            task_args={},
            job_interval=7200,
            job_max_retries=2,
            backend_name="test_backend2",
            url="https://example.com/identities2.json",
        )

        url = reverse("tasks", kwargs={"task_type": "import_identities"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        task_data = response.data["results"][0]
        self.assertEqual(task1.uuid, task_data["uuid"])
        self.assertEqual(task1.backend_name, task_data["backend_name"])
        self.assertEqual(task1.url, task_data["url"])
        self.assertEqual(task1.task_args, task_data["task_args"])
        self.assertEqual(task1.job_interval, task_data["job_interval"])
        self.assertEqual(task1.job_max_retries, task_data["job_max_retries"])

        task_data = response.data["results"][1]
        self.assertEqual(task2.uuid, task_data["uuid"])
        self.assertEqual(task2.backend_name, task_data["backend_name"])
        self.assertEqual(task2.url, task_data["url"])
        self.assertEqual(task2.task_args, task_data["task_args"])
        self.assertEqual(task2.job_interval, task_data["job_interval"])
        self.assertEqual(task2.job_max_retries, task_data["job_max_retries"])

    def test_list_recommend_affiliations_tasks(self):
        """Test that it returns a list of recommend affiliations tasks"""

        task1 = RecommendAffiliationsTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            uuids=["uuid1", "uuid2"],
        )
        task2 = RecommendAffiliationsTask.create_task(
            task_args={},
            job_interval=7200,
            job_max_retries=2,
            uuids=["uuid3"],
        )

        url = reverse("tasks", kwargs={"task_type": "recommend_affiliations"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        task_data = response.data["results"][0]
        self.assertEqual(task1.uuid, task_data["uuid"])
        self.assertEqual(task1.uuids, task_data["uuids"])
        self.assertEqual(task1.task_args, task_data["task_args"])
        self.assertEqual(task1.job_interval, task_data["job_interval"])
        self.assertEqual(task1.job_max_retries, task_data["job_max_retries"])

        task_data = response.data["results"][1]
        self.assertEqual(task2.uuid, task_data["uuid"])
        self.assertEqual(task2.uuids, task_data["uuids"])
        self.assertEqual(task2.task_args, task_data["task_args"])
        self.assertEqual(task2.job_interval, task_data["job_interval"])
        self.assertEqual(task2.job_max_retries, task_data["job_max_retries"])

    def test_list_recommend_gender_tasks(self):
        """Test that it returns a list of recommend gender tasks"""

        task1 = RecommendGenderTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            uuids=["uuid1", "uuid2"],
            exclude=False,
            no_strict_matching=True,
        )
        task2 = RecommendGenderTask.create_task(
            task_args={},
            job_interval=7200,
            job_max_retries=2,
            uuids=["uuid3"],
            exclude=True,
            no_strict_matching=False,
        )

        url = reverse("tasks", kwargs={"task_type": "recommend_gender"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        task_data = response.data["results"][0]
        self.assertEqual(task1.uuid, task_data["uuid"])
        self.assertEqual(task1.uuids, task_data["uuids"])
        self.assertEqual(task1.exclude, task_data["exclude"])
        self.assertEqual(task1.no_strict_matching, task_data["no_strict_matching"])
        self.assertEqual(task1.task_args, task_data["task_args"])
        self.assertEqual(task1.job_interval, task_data["job_interval"])
        self.assertEqual(task1.job_max_retries, task_data["job_max_retries"])

        task_data = response.data["results"][1]
        self.assertEqual(task2.uuid, task_data["uuid"])
        self.assertEqual(task2.uuids, task_data["uuids"])
        self.assertEqual(task2.exclude, task_data["exclude"])
        self.assertEqual(task2.no_strict_matching, task_data["no_strict_matching"])
        self.assertEqual(task2.task_args, task_data["task_args"])
        self.assertEqual(task2.job_interval, task_data["job_interval"])
        self.assertEqual(task2.job_max_retries, task_data["job_max_retries"])

    def test_list_recommend_matches_tasks(self):
        """Test that it returns a list of recommend matches tasks"""

        task1 = RecommendMatchesTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            criteria={"email": True},
            source_uuids=["uuid1"],
            exclude=False,
            strict=True,
            match_source=False,
            guess_github_user=False,
        )
        task2 = RecommendMatchesTask.create_task(
            task_args={},
            job_interval=7200,
            job_max_retries=2,
            criteria={"email": False},
            source_uuids=["uuid3"],
            exclude=True,
            strict=False,
            match_source=True,
            guess_github_user=True,
        )

        url = reverse("tasks", kwargs={"task_type": "recommend_matches"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        task_data = response.data["results"][0]
        self.assertEqual(task1.uuid, task_data["uuid"])
        self.assertEqual(task1.criteria, task_data["criteria"])
        self.assertEqual(task1.source_uuids, task_data["source_uuids"])
        self.assertEqual(task1.exclude, task_data["exclude"])
        self.assertEqual(task1.strict, task_data["strict"])
        self.assertEqual(task1.match_source, task_data["match_source"])
        self.assertEqual(task1.guess_github_user, task_data["guess_github_user"])
        self.assertEqual(task1.task_args, task_data["task_args"])
        self.assertEqual(task1.job_interval, task_data["job_interval"])
        self.assertEqual(task1.job_max_retries, task_data["job_max_retries"])

        task_data = response.data["results"][1]
        self.assertEqual(task2.uuid, task_data["uuid"])
        self.assertEqual(task2.criteria, task_data["criteria"])
        self.assertEqual(task2.source_uuids, task_data["source_uuids"])
        self.assertEqual(task2.exclude, task_data["exclude"])
        self.assertEqual(task2.strict, task_data["strict"])
        self.assertEqual(task2.match_source, task_data["match_source"])
        self.assertEqual(task2.guess_github_user, task_data["guess_github_user"])
        self.assertEqual(task2.task_args, task_data["task_args"])
        self.assertEqual(task2.job_interval, task_data["job_interval"])
        self.assertEqual(task2.job_max_retries, task_data["job_max_retries"])

    def test_list_tasks_with_status_filter(self):
        """Test filtering tasks by status"""

        task1 = EventizerTask.create_task(
            task_args={"uri": "https://github.com/example/repo1.git"},
            job_interval=3600,
            job_max_retries=3,
            datasource_type="git",
            datasource_category="commit",
        )
        task1.status = SchedulerStatus.NEW
        task1.save()

        task2 = EventizerTask.create_task(
            task_args={"uri": "https://github.com/example/repo2.git"},
            job_interval=3600,
            job_max_retries=3,
            datasource_type="git",
            datasource_category="commit",
        )
        task2.status = SchedulerStatus.COMPLETED
        task2.save()

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        response = self.client.get(url, {"status": SchedulerStatus.NEW})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["status"], "new")

    def test_list_tasks_pagination(self):
        """Test that tasks are properly paginated"""

        # Create multiple tasks
        for i in range(30):
            EventizerTask.create_task(
                task_args={"uri": f"https://github.com/example/repo{i}.git"},
                job_interval=3600,
                job_max_retries=3,
                datasource_type="git",
                datasource_category="commit",
            )

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        response = self.client.get(url, {"page": 2, "size": 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 30)
        self.assertEqual(response.data["page"], 2)
        self.assertEqual(response.data["total_pages"], 3)
        self.assertEqual(len(response.data["results"]), 10)

    def test_list_tasks_invalid_type(self):
        """Test listing tasks with invalid task type"""

        url = reverse("tasks", kwargs={"task_type": "invalid-type"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown task type", str(response.data))

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveDestroyTaskApiTest(APITestCase):
    """Unit tests for the Retrieve Destroy Task API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_get_eventizer_task(self):
        """Test retrieving an eventizer task"""

        task = EventizerTask.create_task(
            task_args={"uri": "https://github.com/example/repo.git"},
            job_interval=3600,
            job_max_retries=3,
            datasource_type="git",
            datasource_category="commit",
        )

        url = reverse("task-detail", kwargs={"task_type": "eventizer", "uuid": task.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], task.uuid)
        self.assertEqual(response.data["datasource_type"], "git")
        self.assertEqual(response.data["datasource_category"], "commit")

    def test_get_affiliate_task(self):
        """Test retrieving an affiliate task"""

        task = AffiliateTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            uuids=["uuid1", "uuid2"],
        )

        url = reverse("task-detail", kwargs={"task_type": "affiliate", "uuid": task.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], task.uuid)
        self.assertEqual(response.data["uuids"], ["uuid1", "uuid2"])
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["job_interval"], 3600)
        self.assertEqual(response.data["job_max_retries"], 3)

    def test_get_unify_task(self):
        """Test retrieving a unify task"""

        task = UnifyTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            criteria={"email": True},
            source_uuids=["uuid1"],
            target_uuids=["uuid2"],
            exclude=False,
            strict=True,
            match_source=False,
            guess_github_user=False,
        )

        url = reverse("task-detail", kwargs={"task_type": "unify", "uuid": task.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], task.uuid)
        self.assertEqual(response.data["criteria"], {"email": True})
        self.assertEqual(response.data["source_uuids"], ["uuid1"])
        self.assertEqual(response.data["target_uuids"], ["uuid2"])
        self.assertEqual(response.data["exclude"], False)
        self.assertEqual(response.data["strict"], True)
        self.assertEqual(response.data["match_source"], False)
        self.assertEqual(response.data["guess_github_user"], False)
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["job_interval"], 3600)
        self.assertEqual(response.data["job_max_retries"], 3)

    def test_get_genderize_task(self):
        """Test retrieving a genderize task"""

        task = GenderizeTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            uuids=["uuid1", "uuid2"],
            exclude=False,
            no_strict_matching=True,
        )

        url = reverse("task-detail", kwargs={"task_type": "genderize", "uuid": task.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], task.uuid)
        self.assertEqual(response.data["uuids"], ["uuid1", "uuid2"])
        self.assertEqual(response.data["exclude"], False)
        self.assertEqual(response.data["no_strict_matching"], True)
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["job_interval"], 3600)
        self.assertEqual(response.data["job_max_retries"], 3)

    def test_get_import_identities_task(self):
        """Test retrieving an import identities task"""

        task = ImportIdentitiesTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            backend_name="test_backend",
            url="https://example.com/identities.json",
        )

        url = reverse("task-detail", kwargs={"task_type": "import_identities", "uuid": task.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], task.uuid)
        self.assertEqual(response.data["backend_name"], "test_backend")
        self.assertEqual(response.data["url"], "https://example.com/identities.json")
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["job_interval"], 3600)
        self.assertEqual(response.data["job_max_retries"], 3)

    def test_get_recommend_affiliations_task(self):
        """Test retrieving a recommend affiliations task"""

        task = RecommendAffiliationsTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            uuids=["uuid1", "uuid2"],
        )

        url = reverse(
            "task-detail", kwargs={"task_type": "recommend_affiliations", "uuid": task.uuid}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], task.uuid)
        self.assertEqual(response.data["uuids"], ["uuid1", "uuid2"])
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["job_interval"], 3600)
        self.assertEqual(response.data["job_max_retries"], 3)

    def test_get_recommend_gender_task(self):
        """Test retrieving a recommend gender task"""

        task = RecommendGenderTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            uuids=["uuid1", "uuid2"],
            exclude=False,
            no_strict_matching=True,
        )

        url = reverse("task-detail", kwargs={"task_type": "recommend_gender", "uuid": task.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], task.uuid)
        self.assertEqual(response.data["uuids"], ["uuid1", "uuid2"])
        self.assertEqual(response.data["exclude"], False)
        self.assertEqual(response.data["no_strict_matching"], True)
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["job_interval"], 3600)
        self.assertEqual(response.data["job_max_retries"], 3)

    def test_get_recommend_matches_task(self):
        """Test retrieving a recommend matches task"""

        task = RecommendMatchesTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            criteria={"email": True},
            source_uuids=["uuid1"],
            exclude=False,
            strict=True,
            match_source=False,
            guess_github_user=False,
        )

        url = reverse("task-detail", kwargs={"task_type": "recommend_matches", "uuid": task.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], task.uuid)
        self.assertEqual(response.data["criteria"], {"email": True})
        self.assertEqual(response.data["source_uuids"], ["uuid1"])
        self.assertEqual(response.data["exclude"], False)
        self.assertEqual(response.data["strict"], True)
        self.assertEqual(response.data["match_source"], False)
        self.assertEqual(response.data["guess_github_user"], False)
        self.assertEqual(response.data["task_args"], {})
        self.assertEqual(response.data["job_interval"], 3600)
        self.assertEqual(response.data["job_max_retries"], 3)

    def test_get_task_not_found(self):
        """Test retrieving a task that doesn't exist"""

        fake_uuid = "fake_task_uuid"
        url = reverse("task-detail", kwargs={"task_type": "eventizer", "uuid": fake_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_task_invalid_type(self):
        """Test retrieving a task with invalid task type"""

        fake_uuid = "fake_task_uuid"
        url = reverse("task-detail", kwargs={"task_type": "invalid-type", "uuid": fake_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown task type", str(response.data))

    def test_delete_task(self):
        """Test deleting a task"""

        task = EventizerTask.create_task(
            task_args={"uri": "https://github.com/example/repo.git"},
            job_interval=3600,
            job_max_retries=3,
            datasource_type="git",
            datasource_category="commit",
        )

        url = reverse("task-detail", kwargs={"task_type": "eventizer", "uuid": task.uuid})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify task is deleted
        self.assertFalse(EventizerTask.objects.filter(uuid=task.uuid).exists())

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        fake_uuid = "fake_task_uuid"
        url = reverse("task-detail", kwargs={"task_type": "eventizer", "uuid": fake_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RescheduleTaskApiTest(APITestCase):
    """Unit tests for the Reschedule Task API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    @patch("grimoirelab.core.scheduler.api.reschedule_task")
    def test_reschedule_task(self, mock_reschedule_task):
        """Test rescheduling a task"""

        task_uuid = "test_task_uuid"
        url = reverse("task-reschedule", kwargs={"task_type": "eventizer", "uuid": task_uuid})

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("rescheduled", response.data[0])
        mock_reschedule_task.assert_called_once_with(task_uuid)

    @patch("grimoirelab.core.scheduler.api.reschedule_task")
    def test_reschedule_task_not_found(self, mock_reschedule_task):
        """Test rescheduling a task that doesn't exist"""

        from grimoirelab.core.scheduler.errors import NotFoundError

        mock_reschedule_task.side_effect = NotFoundError(element="Task")

        task_uuid = "test_task_uuid"
        url = reverse("task-reschedule", kwargs={"task_type": "eventizer", "uuid": task_uuid})

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("not found", response.data["detail"])

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        task_uuid = "test_task_uuid"
        url = reverse("task-reschedule", kwargs={"task_type": "eventizer", "uuid": task_uuid})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CancelTaskApiTest(APITestCase):
    """Unit tests for the Cancel Task API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    @patch("grimoirelab.core.scheduler.api.cancel_task")
    def test_cancel_task(self, mock_cancel_task):
        """Test cancelling a task"""

        task_uuid = "test_task_uuid"
        url = reverse("task-cancel", kwargs={"task_type": "eventizer", "uuid": task_uuid})

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("cancelled", response.data[0])
        mock_cancel_task.assert_called_once_with(task_uuid)

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        task_uuid = "test_task_uuid"
        url = reverse("task-cancel", kwargs={"task_type": "eventizer", "uuid": task_uuid})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ListJobsApiTest(APITestCase):
    """Unit tests for the List Jobs API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_list_jobs_invalid_task_type(self):
        """Test listing jobs with invalid task type"""

        task_uuid = "test_task_uuid"
        url = reverse("jobs", kwargs={"task_type": "invalid-type", "task_id": task_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown task type", str(response.data))

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        task_uuid = "test_task_uuid"
        url = reverse("jobs", kwargs={"task_type": "eventizer", "task_id": task_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class JobDetailApiTest(APITestCase):
    """Unit tests for the Job Detail API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_get_job_invalid_task_type(self):
        """Test retrieving job details with invalid task type"""

        task_uuid = "test_task_uuid"
        job_uuid = "test_job_uuid"
        url = reverse(
            "job-detail",
            kwargs={"task_type": "invalid-type", "task_id": task_uuid, "uuid": job_uuid},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown task type", str(response.data))

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        task_uuid = "test_task_uuid"
        job_uuid = "test_job_uuid"
        url = reverse(
            "job-detail", kwargs={"task_type": "eventizer", "task_id": task_uuid, "uuid": job_uuid}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class JobLogsApiTest(APITestCase):
    """Unit tests for the Job Logs API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_get_job_logs_invalid_task_type(self):
        """Test retrieving job logs with invalid task type"""

        task_uuid = "test_task_uuid"
        job_uuid = "test_job_uuid"
        url = reverse(
            "job-logs", kwargs={"task_type": "invalid-type", "task_id": task_uuid, "uuid": job_uuid}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown task type", str(response.data))

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        task_uuid = "test_task_uuid"
        job_uuid = "test_job_uuid"
        url = reverse(
            "job-logs", kwargs={"task_type": "eventizer", "task_id": task_uuid, "uuid": job_uuid}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
