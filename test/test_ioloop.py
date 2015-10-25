#!/usr/bin/env python

# Copyright (C) 2007-2016 Giampaolo Rodola' <g.rodola@gmail.com>.
# Use of this source code is governed by MIT license that can be
# found in the LICENSE file.

import os
import time

from pyftpdlib.ioloop import IOLoop
from testutils import unittest
from testutils import VERBOSITY


class TestCallLater(unittest.TestCase):
    """Tests for CallLater class."""

    def setUp(self):
        self.ioloop = IOLoop.instance()
        for task in self.ioloop.sched._tasks:
            if not task.cancelled:
                task.cancel()
        del self.ioloop.sched._tasks[:]

    def scheduler(self, timeout=0.01, count=100):
        while self.ioloop.sched._tasks and count > 0:
            self.ioloop.sched.poll()
            count -= 1
            time.sleep(timeout)

    def test_interface(self):
        def fun():
            return 0

        self.assertRaises(AssertionError, self.ioloop.call_later, -1, fun)
        x = self.ioloop.call_later(3, fun)
        self.assertEqual(x.cancelled, False)
        x.cancel()
        self.assertEqual(x.cancelled, True)
        self.assertRaises(AssertionError, x.call)
        self.assertRaises(AssertionError, x.reset)
        self.assertRaises(AssertionError, x.cancel)

    def test_order(self):
        def fun(x):
            l.append(x)

        l = []
        for x in [0.05, 0.04, 0.03, 0.02, 0.01]:
            self.ioloop.call_later(x, fun, x)
        self.scheduler()
        self.assertEqual(l, [0.01, 0.02, 0.03, 0.04, 0.05])

    # The test is reliable only on those systems where time.time()
    # provides time with a better precision than 1 second.
    if not str(time.time()).endswith('.0'):
        def test_reset(self):
            def fun(x):
                l.append(x)

            l = []
            self.ioloop.call_later(0.01, fun, 0.01)
            self.ioloop.call_later(0.02, fun, 0.02)
            self.ioloop.call_later(0.03, fun, 0.03)
            x = self.ioloop.call_later(0.04, fun, 0.04)
            self.ioloop.call_later(0.05, fun, 0.05)
            time.sleep(0.1)
            x.reset()
            self.scheduler()
            self.assertEqual(l, [0.01, 0.02, 0.03, 0.05, 0.04])

    def test_cancel(self):
        def fun(x):
            l.append(x)

        l = []
        self.ioloop.call_later(0.01, fun, 0.01).cancel()
        self.ioloop.call_later(0.02, fun, 0.02)
        self.ioloop.call_later(0.03, fun, 0.03)
        self.ioloop.call_later(0.04, fun, 0.04)
        self.ioloop.call_later(0.05, fun, 0.05).cancel()
        self.scheduler()
        self.assertEqual(l, [0.02, 0.03, 0.04])

    def test_errback(self):
        l = []
        self.ioloop.call_later(
            0.0, lambda: 1 // 0, _errback=lambda: l.append(True))
        self.scheduler()
        self.assertEqual(l, [True])


class TestCallEvery(unittest.TestCase):
    """Tests for CallEvery class."""

    def setUp(self):
        self.ioloop = IOLoop.instance()
        for task in self.ioloop.sched._tasks:
            if not task.cancelled:
                task.cancel()
        del self.ioloop.sched._tasks[:]

    def scheduler(self, timeout=0.003):
        stop_at = time.time() + timeout
        while time.time() < stop_at:
            self.ioloop.sched.poll()

    def test_interface(self):
        def fun():
            return 0

        self.assertRaises(AssertionError, self.ioloop.call_every, -1, fun)
        x = self.ioloop.call_every(3, fun)
        self.assertEqual(x.cancelled, False)
        x.cancel()
        self.assertEqual(x.cancelled, True)
        self.assertRaises(AssertionError, x.call)
        self.assertRaises(AssertionError, x.reset)
        self.assertRaises(AssertionError, x.cancel)

    def test_only_once(self):
        # make sure that callback is called only once per-loop
        def fun():
            l1.append(None)

        l1 = []
        self.ioloop.call_every(0, fun)
        self.ioloop.sched.poll()
        self.assertEqual(l1, [None])

    def test_multi_0_timeout(self):
        # make sure a 0 timeout callback is called as many times
        # as the number of loops
        def fun():
            l.append(None)

        l = []
        self.ioloop.call_every(0, fun)
        for x in range(100):
            self.ioloop.sched.poll()
        self.assertEqual(len(l), 100)

    # run it on systems where time.time() has a higher precision
    if os.name == 'posix':
        def test_low_and_high_timeouts(self):
            # make sure a callback with a lower timeout is called more
            # frequently than another with a greater timeout
            def fun():
                l1.append(None)

            l1 = []
            self.ioloop.call_every(0.001, fun)
            self.scheduler()

            def fun():
                l2.append(None)

            l2 = []
            self.ioloop.call_every(0.005, fun)
            self.scheduler(timeout=0.01)

            self.assertTrue(len(l1) > len(l2))

    def test_cancel(self):
        # make sure a cancelled callback doesn't get called anymore
        def fun():
            l.append(None)

        l = []
        call = self.ioloop.call_every(0.001, fun)
        self.scheduler()
        len_l = len(l)
        call.cancel()
        self.scheduler()
        self.assertEqual(len_l, len(l))

    def test_errback(self):
        l = []
        self.ioloop.call_every(
            0.0, lambda: 1 // 0, _errback=lambda: l.append(True))
        self.scheduler()
        self.assertTrue(l)


if __name__ == '__main__':
    unittest.main(verbosity=VERBOSITY)
