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

import json
import time

from grimoirelab.core.consumers.consumer import (
    Consumer,
    Entry
)

from ..base import GrimoireLabTestCase


class RedisStream:
    """Helper class to interact with Redis streams"""

    def __init__(self, redis_connection):
        self.redis_connection = redis_connection

    def create_stream_group(self, stream_name, group_name):
        self.redis_connection.xgroup_create(stream_name, group_name, id="0", mkstream=True)

    def add_entry_to_stream(self, stream_name, message_id, event):
        self.redis_connection.xadd(stream_name, {b"data": json.dumps(event).encode()}, id=message_id)

    def read_stream_group(self, stream_name, group_name, consumer_name, total):
        return self.redis_connection.xreadgroup(group_name, consumer_name, {stream_name: ">"}, count=total)


class TestConsumer(GrimoireLabTestCase):

    def test_consumer_initialization(self):
        """Test whether the consumer is initialized correctly"""

        consumer = Consumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level="DEBUG",
        )

        self.assertEqual(consumer.stream_name, "test_stream")
        self.assertEqual(consumer.consumer_group, "test_group")
        self.assertEqual(consumer.consumer_name, "test_consumer")
        self.assertEqual(consumer.stream_block_timeout, 1000)
        self.assertEqual(consumer.logging_level, "DEBUG")

    def test_fetch_new_entries(self):
        """Test whether the consumer fetches entries from the stream"""

        expected_entries = [
            Entry(message_id="1-0", event={"key": "value_1"}),
            Entry(message_id="2-0", event={"key": "value_2"}),
            Entry(message_id="3-0", event={"key": "value_3"}),
        ]

        stream = RedisStream(self.conn)
        stream.create_stream_group("test_stream", "test_group")
        for entry in expected_entries:
            stream.add_entry_to_stream("test_stream", entry.message_id, entry.event)

        consumer = Consumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level="DEBUG",
        )
        entries = list(consumer.fetch_new_entries())

        self.assertEqual(len(entries), len(expected_entries))

        for entry, expected_entry in zip(entries, expected_entries):
            self.assertEqual(entry.message_id.decode(), expected_entry.message_id)
            self.assertDictEqual(entry.event, expected_entry.event)

    def test_recover_entries(self):
        """Test whether the consumer recovers entries from the stream"""

        expected_entries = [
            Entry(message_id="1-0", event={"key": "value_1"}),
            Entry(message_id="2-0", event={"key": "value_2"}),
            Entry(message_id="3-0", event={"key": "value_3"}),
        ]

        stream = RedisStream(self.conn)
        stream.create_stream_group("test_stream", "test_group")
        for entry in expected_entries:
            stream.add_entry_to_stream("test_stream", entry.message_id, entry.event)

        # Read the entries to claim them
        stream.read_stream_group("test_stream", "test_group", "test_consumer", 3)

        consumer = Consumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level="DEBUG",
        )
        # No entries should be available
        entries = list(consumer.fetch_new_entries())
        self.assertEqual(len(entries), 0)

        entries = list(consumer.recover_stream_entries())
        self.assertEqual(len(entries), 0)

        # Change min_idle_time to 2s to recover the entries
        time.sleep(2)
        entries = list(consumer.recover_stream_entries(recover_idle_time=2000))

        self.assertEqual(len(entries), len(expected_entries))
        for entry, expected_entry in zip(entries, expected_entries):
            self.assertEqual(entry.message_id.decode(), expected_entry.message_id)
            self.assertDictEqual(entry.event, expected_entry.event)

    def test_ack_entries(self):
        """Test whether the consumer acknowledges entries"""

        stream = RedisStream(self.conn)
        stream.create_stream_group("test_stream", "test_group")
        stream.add_entry_to_stream("test_stream", "1-0", {"key": "value_1"})
        stream.add_entry_to_stream("test_stream", "2-0", {"key": "value_2"})

        consumer = Consumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level="DEBUG",
        )
        entries = list(consumer.fetch_new_entries())
        self.assertEqual(len(entries), 2)

        pending = self.conn.xpending("test_stream", "test_group")
        self.assertEqual(pending["pending"], 2)

        ids = [entry.message_id for entry in entries]
        consumer.ack_entries(ids)

        # Entries are acknowledged
        pending = self.conn.xpending("test_stream", "test_group")
        self.assertEqual(pending["pending"], 0)
