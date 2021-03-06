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

from helpers import setup_path
setup_path()

import logging
from logr import Logr
Logr.configure(logging.DEBUG)

from caper import Caper
from caper.parsers.scene import SceneParser
from matchers import has_info
from hamcrest import *

caper = Caper()


def test_closures():
    r = caper.parse('Show Name.S01E05.[720p]-GROUP')
    assert_that(r, has_info('video', {'resolution': '720p'}))
    assert_that(r, has_info('group', 'GROUP'))


def test_print_tree():
    closures = caper._closure_split('Show.Name.S01E02-GROUP')
    closures = caper._fragment_split(closures)

    scene_parser = SceneParser(debug=True)
    scene_parser.run(closures)
