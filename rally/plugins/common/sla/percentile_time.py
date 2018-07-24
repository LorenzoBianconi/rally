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
            "duration_distribution": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "percentile": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "threshold": {"type": "number", "minimum": 0.0}
                    }
                }
            }
        }
    }

    def __init__(self, criterion_value):
        super(PercentileTime, self).__init__(criterion_value)

        self.min_iterations = self.criterion_value.get("min_iterations", 3)
        self.iterations = 0

        self.p_comp_list = []
        self.dur_distribution = self.criterion_value.get("duration_distribution")
        for item in self.dur_distribution:
            percentile = item.get("percentile", 0.9)
            p_comp = streaming_algorithms.PercentileComputation(percentile, 10000)
            self.p_comp_list.append(p_comp)

    def add_iteration(self, iteration):
        if not iteration["error"]:
            self.iterations += 1
            if self.iterations < self.min_iterations:
                return self.success

            for index in range(0, len(self.p_comp_list)):
                threshold = self.dur_distribution[index].get("threshold", 1)
                self.p_comp_list[index].add(iteration["duration"])
                self.success = self.p_comp_list[index].result() <= threshold
                if not self.success:
                    break
        return self.success

    def merge(self, other):
        return self.success

    def details(self):
        output = ""

        for index in range(0, len(self.p_comp_list)):
            percentile = self.dur_distribution[index].get("percentile", 0.9)
            threshold = self.dur_distribution[index].get("threshold", 1)
            result = self.p_comp_list[index].result()

            output += "P(%.2f) %.3f <= %.3f " % (percentile, result, threshold)
        return output
