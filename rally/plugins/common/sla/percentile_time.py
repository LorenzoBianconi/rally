# Copyright 2018: RedHat Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


"""
SLA (Service-level agreement) is set of details for determining compliance
with contracted values such as maximum error rate or minimum response time.
"""

from rally.common.i18n import _
from rally import consts
from rally.task import sla
from rally.common import streaming_algorithms


@sla.configure(name="percentile_time")
class PercentileTime(sla.SLA):
    """Percentile time for a given operation."""
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "min_iterations": {"type": "integer", "minimum": 3},
            "p0": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "th0": {"type": "number", "minimum": 0.0},
            "p1": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "th1": {"type": "number", "minimum": 0.0},
            "p2": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "th2": {"type": "number", "minimum": 0.0}
        }
    }

    def __init__(self, criterion_value):
        super(PercentileTime, self).__init__(criterion_value)
        self.min_iterations = self.criterion_value.get("min_iterations", 3)
        self.iterations = 0

        self.p0 = self.criterion_value.get("p0", 0.9)
        self.th0 = self.criterion_value.get("th0", 0.0)
        self.p0_comp = streaming_algorithms.PercentileComputation(self.p0, 1000)
        self.p1 = self.criterion_value.get("p1", 0.9)
        self.th1 = self.criterion_value.get("th1", 0.0)
        self.p1_comp = streaming_algorithms.PercentileComputation(self.p1, 1000)
        self.p2 = self.criterion_value.get("p2", 0.9)
        self.th2 = self.criterion_value.get("th2", 0.0)
        self.p2_comp = streaming_algorithms.PercentileComputation(self.p2, 1000)

    def add_iteration(self, iteration):
        if not iteration["error"]:
            self.iterations += 1

            if self.iterations >= self.min_iterations:
                self.p0_comp.add(iteration["duration"])
                self.p1_comp.add(iteration["duration"])
                self.p2_comp.add(iteration["duration"])

                if self.th0:
                    self.success = self.p0_comp.result() <= self.th0
                if self.success and self.th1:
                    self.success = self.p1_comp.result() <= self.th1
                if self.success and self.th2:
                    self.success = self.p2_comp.result() <= self.th2
        return self.success

    def merge(self, other):
        return self.success

    def details(self):
        return (_("P0 (%.2f) %.3f <= %.3f P1 (%.2f) %.3f <= %.3f P2 (%.2f) %.3f <= %.3f") %
                 (self.p0, self.p0_comp.result(), self.th0,
                 self.p1, self.p1_comp.result(), self.th1,
                 self.p2, self.p2_comp.result(), self.th2))
