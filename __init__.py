# Copyright 2022 Åke Forslund
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import aiml
import os
from os import listdir, remove as remove_file
from os.path import dirname, isfile

from mycroft.api import DeviceApi
from mycroft.skills.core import FallbackSkill, intent_handler
from adapt.intent import IntentBuilder


class AimlFallback(FallbackSkill):

    def __init__(self):
        super(AimlFallback, self).__init__(name='AimlFallback')
        self.kernel = aiml.Kernel()
        self.aiml_path = os.path.join(dirname(__file__), 'aiml')
        self.brain_path = os.path.join(self.file_system.path,
                                       'bot_brain.brn')
        # reloading skills will also reset this 'timer', so ideally it should
        # not be too high
        self.line_count = 1
        self.save_loop_threshold = int(self.settings.get('save_loop_threshold',
                                                         4))

        self.brain_loaded = False

    def initialize(self):
        self.register_fallback(self.handle_fallback, 90)
        return

    def load_brain(self):
        """Set up the aiml engine using available device information."""
        self.log.info('Loading Brain')
        if isfile(self.brain_path):
            self.kernel.bootstrap(brainFile=self.brain_path)
        else:
            aimls = listdir(self.aiml_path)
            for aiml_file in aimls:
                self.kernel.learn(os.path.join(self.aiml_path, aiml_file))
            self.kernel.saveBrain(self.brain_path)
        try:
            device = DeviceApi().get()
        except Exception:
            device = {
                "name": "Mycroft",
                "platform": "AI"
            }
        self.kernel.setBotPredicate("name", device["name"])
        self.kernel.setBotPredicate("species", device["platform"])
        self.kernel.setBotPredicate("genus", "Mycroft")
        self.kernel.setBotPredicate("family", "virtual personal assistant")
        self.kernel.setBotPredicate("order", "artificial intelligence")
        self.kernel.setBotPredicate("class", "computer program")
        self.kernel.setBotPredicate("kingdom", "machine")
        self.kernel.setBotPredicate("hometown", "127.0.0.1")
        self.kernel.setBotPredicate("botmaster", "master")
        self.kernel.setBotPredicate("master", "the community")
        # IDEA: extract age from
        # https://api.github.com/repos/MycroftAI/mycroft-core created_at date
        self.kernel.setBotPredicate("age", "2")

        self.brain_loaded = True
        return

    @intent_handler(IntentBuilder("ResetMemoryIntent").require("Reset")
                                                      .require("Memory"))
    def handle_reset_brain(self, message):
        """Delete the stored memory, effectively resetting the brain state."""
        self.log.debug('Deleting brain file')
        # delete the brain file and reset memory
        self.speak_dialog("reset.memory")
        remove_file(self.brain_path)
        self.soft_reset_brain()
        return

    def ask_brain(self, utterance):
        """Send a query to the AIML brain.

        Saves the state to disk once in a while.
        """
        response = self.kernel.respond(utterance)
        # make a security copy once in a while
        if (self.line_count % self.save_loop_threshold) == 0:
            self.kernel.saveBrain(self.brain_path)
        self.line_count += 1

        return response

    def soft_reset_brain(self):
        # Only reset the active kernel memory
        self.kernel.resetBrain()
        self.brain_loaded = False
        return

    def handle_fallback(self, message):
        """Mycroft fallback handler interfacing the AIML.

        If enabled in home, this will parse a sentence and return answer from
        the AIML engine.
        """
        if self.settings.get("enabled"):
            if not self.brain_loaded:
                self.load_brain()
            utterance = message.data.get("utterance")
            answer = self.ask_brain(utterance)
            if answer != "":
                asked_question = False
                if answer.endswith("?"):
                    asked_question = True
                self.speak(answer, expect_response=asked_question)
                return True
        return False

    def shutdown(self):
        """Shut down any loaded brain."""
        if self.brain_loaded:
            self.kernel.saveBrain(self.brain_path)
            self.kernel.resetBrain()  # Manual remove
        self.remove_fallback(self.handle_fallback)
        super(AimlFallback, self).shutdown()


def create_skill():
    return AimlFallback()
