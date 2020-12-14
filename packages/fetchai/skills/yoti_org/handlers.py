# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This package contains the handlers of the yoti_org skill."""

from typing import List, Optional, cast
from urllib.parse import parse_qs, urlparse

from aea.protocols.base import Message
from aea.skills.base import Handler

from packages.fetchai.connections.yoti.connection import (
    CONNECTION_ID as YOTI_CONNECTION_ID,
)
from packages.fetchai.protocols.http.message import (  # pylint: disable=import-error,no-name-in-module
    HttpMessage,
)
from packages.fetchai.protocols.yoti.message import (  # pylint: disable=import-error,no-name-in-module
    YotiMessage,
)
from packages.fetchai.skills.yoti_org.dialogues import (
    HttpDialogue,
    HttpDialogues,
    YotiDialogue,
    YotiDialogues,
)
from packages.fetchai.skills.yoti_org.parameters import Parameters


class HttpHandler(Handler):
    """This class acts as a http handler."""

    SUPPORTED_PROTOCOL = HttpMessage.protocol_id

    def setup(self) -> None:
        """
        Implement the setup.

        :return: None
        """
        pass

    def handle(self, message: Message) -> None:
        """
        Implement the reaction to an envelope.

        :param message: the message
        :return: None
        """
        http_msg = cast(HttpMessage, message)

        # recover dialogue
        http_dialogues = cast(HttpDialogues, self.context.http_dialogues)
        http_dialogue = cast(HttpDialogue, http_dialogues.update(http_msg))
        if http_dialogue is None:
            self._handle_unidentified_dialogue(http_msg)
            return

        # handle message
        if http_msg.performative == HttpMessage.Performative.REQUEST:
            self._handle_request(http_msg, http_dialogue)
        else:
            self._handle_invalid(http_msg, http_dialogue)

    def _handle_unidentified_dialogue(self, http_msg: HttpMessage) -> None:
        """
        Handle an unidentified dialogue.

        :param http_msg: the message
        """
        self.context.logger.info(
            "received invalid http message={}, unidentified dialogue.".format(http_msg)
        )

    def _handle_request(
        self, http_msg: HttpMessage, http_dialogue: HttpDialogue
    ) -> None:
        """
        Handle a Http request.

        :param http_msg: the http message
        :param http_dialogue: the http dialogue
        :return: None
        """
        self.context.logger.info(
            "received http request with method={}, url={} and body={!r}".format(
                http_msg.method, http_msg.url, http_msg.body,
            )
        )
        if http_msg.method == "get":
            self._handle_get(http_msg, http_dialogue)
        else:
            self.context.logger.info(f"Unknown request type={http_msg.method}")

    def _handle_get(self, http_msg: HttpMessage, http_dialogue: HttpDialogue) -> None:
        """
        Handle a Http request of verb GET.

        :param http_msg: the http message
        :param http_dialogue: the http dialogue
        :return: None
        """
        parsed = urlparse(http_msg.url)
        query = parse_qs(parsed.query)
        address = cast(List[Optional[str]], query.get("address", [None]))[0]
        token = cast(List[Optional[str]], query.get("token", [None]))[0]
        yoti_redirect = 'yoti' in parsed.path
        parameters = cast(Parameters, self.context.parameters)
        info = parameters.db.get(address, None) if address is not None else None
        if not yoti_redirect and address is not None and info is None:
            http_response = http_dialogue.reply(
                performative=HttpMessage.Performative.RESPONSE,
                target_message=http_msg,
                version=http_msg.version,
                status_code=200,
                status_text="Success",
                headers='Content-Type: text/html',
                body=parameters.yoti_button,
            )
            self.context.logger.info("responding with: {}".format(http_response))
            self.context.outbox.put_message(message=http_response)
        elif not yoti_redirect and address is not None and info is not None:
            http_response = http_dialogue.reply(
                performative=HttpMessage.Performative.RESPONSE,
                target_message=http_msg,
                version=http_msg.version,
                status_code=200,
                status_text="Success",
                headers='Content-Type: text/html',
                body=parameters.info_html(info),
            )
            self.context.logger.info("responding with: {}".format(http_response))
            self.context.outbox.put_message(message=http_response)
        elif yoti_redirect and address is not None and token is not None:
            http_response = http_dialogue.reply(
                performative=HttpMessage.Performative.RESPONSE,
                target_message=http_msg,
                version=http_msg.version,
                status_code=200,
                status_text="Success",
                headers='Content-Type: text/html',
                body=parameters.success_html,
            )
            self.context.logger.info("responding with: {}".format(http_response))
            self.context.outbox.put_message(message=http_response)
            yoti_dialogues = cast(YotiDialogues, self.context.yoti_dialogues)
            yoti_request, yoti_dialogue = yoti_dialogues.create(
                performative=YotiMessage.Performative.GET_PROFILE,
                counterparty=str(YOTI_CONNECTION_ID),
                token=token,
                dotted_path="get_attribute",
                args=("age_over:18",),
            )
            yoti_dialogue = cast(YotiDialogue, yoti_dialogue)
            yoti_dialogue.agent_address = address
            self.context.logger.info(f"requesting profile from yoti with token={token}")
            self.context.outbox.put_message(message=yoti_request)
        else:
            http_response = http_dialogue.reply(
                performative=HttpMessage.Performative.RESPONSE,
                target_message=http_msg,
                version=http_msg.version,
                status_code=200,
                status_text="Success",
                headers='Content-Type: text/html',
                body=parameters.failure_html,
            )
            self.context.logger.info("responding with: {}".format(http_response))
            self.context.outbox.put_message(message=http_response)

    def _handle_invalid(
        self, http_msg: HttpMessage, http_dialogue: HttpDialogue
    ) -> None:
        """
        Handle an invalid http message.

        :param http_msg: the http message
        :param http_dialogue: the http dialogue
        :return: None
        """
        self.context.logger.warning(
            "cannot handle http message of performative={} in dialogue={}.".format(
                http_msg.performative, http_dialogue
            )
        )

    def teardown(self) -> None:
        """
        Implement the handler teardown.

        :return: None
        """
        pass


class YotiHandler(Handler):
    """This class acts as a yoti handler."""

    SUPPORTED_PROTOCOL = YotiMessage.protocol_id

    def setup(self) -> None:
        """
        Implement the setup.

        :return: None
        """
        pass

    def handle(self, message: Message) -> None:
        """
        Implement the reaction to an envelope.

        :param message: the message
        :return: None
        """
        yoti_msg = cast(YotiMessage, message)

        # recover dialogue
        yoti_dialogues = cast(YotiDialogues, self.context.yoti_dialogues)
        yoti_dialogue = cast(YotiDialogue, yoti_dialogues.update(yoti_msg))
        if yoti_dialogue is None:
            self._handle_unidentified_dialogue(yoti_msg)
            return

        # handle message
        if yoti_msg.performative == YotiMessage.Performative.PROFILE:
            self._handle_profile(yoti_msg, yoti_dialogue)
        elif yoti_msg.performative == YotiMessage.Performative.ERROR:
            self._handle_error(yoti_msg, yoti_dialogue)
        else:
            self._handle_invalid(yoti_msg, yoti_dialogue)

    def _handle_unidentified_dialogue(self, yoti_msg: YotiMessage) -> None:
        """
        Handle an unidentified dialogue.

        :param yoti_msg: the message
        """
        self.context.logger.info(
            "received invalid yoti message={}, unidentified dialogue.".format(yoti_msg)
        )

    def _handle_profile(
        self, yoti_msg: YotiMessage, yoti_dialogue: YotiDialogue
    ) -> None:
        """
        Handle a yoti message of performative PROFILE.

        :param yoti_msg: the yoti message
        :param yoti_dialogue: the yoti dialogue
        :return: None
        """
        self.context.logger.info(
            "received yoti message={} in dialogue={}.".format(yoti_msg, yoti_dialogue)
        )
        parameters = cast(Parameters, self.context.parameters)
        parameters.db[yoti_dialogue.agent_address] = yoti_msg.info
        self.context.logger.info(f"DB updated: {parameters.db}")

    def _handle_error(
        self, yoti_msg: YotiMessage, yoti_dialogue: YotiDialogue
    ) -> None:
        """
        Handle an invalid yoti message.

        :param yoti_msg: the yoti message
        :param yoti_dialogue: the yoti dialogue
        :return: None
        """
        self.context.logger.warning(
            "received yoti error message={} in dialogue={}.".format(
                yoti_msg.error_msg, yoti_dialogue
            )
        )

    def _handle_invalid(
        self, yoti_msg: YotiMessage, yoti_dialogue: YotiDialogue
    ) -> None:
        """
        Handle an invalid yoti message.

        :param yoti_msg: the yoti message
        :param yoti_dialogue: the yoti dialogue
        :return: None
        """
        self.context.logger.warning(
            "cannot handle yoti message of performative={} in dialogue={}.".format(
                yoti_msg.performative, yoti_dialogue
            )
        )

    def teardown(self) -> None:
        """
        Implement the handler teardown.

        :return: None
        """
        pass
