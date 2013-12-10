# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from logr import Logr
from caper import CaperClosure, CaperFragment
from caper.helpers import clean_dict
from caper.result import CaperFragmentNode, CaperClosureNode
from caper.step import CaptureStep
from caper.constraint import CaptureConstraint


class CaptureGroup(object):
    def __init__(self, parser, result):
        """Capture group object

        :type parser: caper.parsers.base.Parser
        :type result: caper.result.CaperResult
        """

        self.parser = parser
        self.result = result

        #: @type: list of CaptureStep
        self.steps = []
        #: type: str
        self.step_source = None
        #: @type: list of CaptureConstraint
        self.constraints = []

    def capture_fragment(self, tag, regex=None, func=None, single=True):
        Logr.debug('capture_fragment("%s", "%s", %s, %s)', tag, regex, func, single)

        if self.step_source != 'fragment':
            if self.step_source is None:
                self.step_source = 'fragment'
            else:
                raise ValueError("Unable to mix fragment and closure capturing in a group")

        self.steps.append(CaptureStep(
            self, tag,
            'fragment',
            regex=regex,
            func=func,
            single=single
        ))

        return self

    def capture_closure(self, tag, regex=None, func=None, single=True):
        Logr.debug('capture_closure("%s", "%s", %s, %s)', tag, regex, func, single)

        if self.step_source != 'closure':
            if self.step_source is None:
                self.step_source = 'closure'
            else:
                raise ValueError("Unable to mix fragment and closure capturing in a group")

        self.steps.append(CaptureStep(
            self, tag,
            'closure',
            regex=regex,
            func=func,
            single=single
        ))

        return self

    def until(self, **kwargs):
        self.constraints.append(CaptureConstraint(self, **kwargs))

        return self

    def parse_subject(self, parent_head, subject):
        Logr.debug("parse_subject (%s) subject: %s", self.step_source, repr(subject))

        if type(subject) is CaperClosure:
            return self.parse_closure(parent_head, subject)

        if type(subject) is CaperFragment:
            return self.parse_fragment(parent_head, subject)

        raise ValueError('Unknown subject (%s)', subject)

    def parse_fragment(self, parent_head, subject):
        parent_node = parent_head[0] if type(parent_head) is list else parent_head

        nodes, match = self.match(parent_head, parent_node, subject)

        # Capturing broke on constraint, return now
        if not match:
            return nodes

        Logr.debug('created fragment node with subject.value: "%s"' % subject.value)

        result = [CaperFragmentNode(
            parent_node.closure,
            subject.take_right(match.num_fragments),
            parent_head,
            match
        )]

        # Branch if the match was indefinite (weight below 1.0)
        if match.result and match.weight < 1.0:
            if match.num_fragments == 1:
                result.append(CaperFragmentNode(parent_node.closure, [subject], parent_head, None))
            else:
                nodes.append(CaperFragmentNode(parent_node.closure, [subject], parent_head, None))

        nodes.append(result[0] if len(result) == 1 else result)

        return nodes

    def parse_closure(self, parent_head, subject):
        if self.step_source != 'closure':
            Logr.debug('Closure encountered, jumping into fragments')
            return [CaperClosureNode(subject, parent_head)]

        raise NotImplementedError()

    def match(self, parent_head, parent_node, subject):
        nodes = []

        # Check constraints
        for constraint in self.constraints:
            weight, success = constraint.execute(subject)
            if success:
                Logr.debug('capturing broke on "%s" at %s', subject.value, constraint)
                parent_node.finished_groups.append(self)
                nodes.append(parent_head)

                if weight == 1.0:
                    return nodes, None
                else:
                    Logr.debug('Branching result')

        # Try match subject against the steps available
        match = None

        for step in self.steps:
            match = step.execute(subject)

            if match.success:
                if type(match.result) is dict:
                    match.result = clean_dict(match.result)

                Logr.debug('Found match with weight %s, match: %s, num_fragments: %s' % (
                    match.weight, match.result, match.num_fragments
                ))
                break

        return nodes, match

    def execute(self):
        heads_finished = None

        while heads_finished is None or not (len(heads_finished) == len(self.result.heads) and all(heads_finished)):
            heads_finished = []

            heads = self.result.heads
            self.result.heads = []

            for head in heads:
                node = head[0] if type(head) is list else head

                if self in node.finished_groups:
                    Logr.debug("head finished for group")
                    self.result.heads.append(head)
                    heads_finished.append(True)
                    continue

                next_subject = node.next()

                Logr.debug('')
                Logr.debug('----------[%s] (%s)----------' % (next_subject, repr(next_subject.value) if next_subject else None))

                if next_subject:
                    for node_result in self.parse_subject(head, next_subject):
                        self.result.heads.append(node_result)

                heads_finished.append(self in node.finished_groups or next_subject is None)

            if len(self.result.heads) == 0:
                self.result.heads = heads

            Logr.debug("heads_finished: %s, self.result.heads: %s", heads_finished, self.result.heads)

        Logr.debug("group finished")
